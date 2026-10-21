"""F08.3: boundary de serviço para compra revisada, sem transporte WhatsApp próprio."""

import base64
import hashlib
import hmac
import io
import json
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic import ValidationError as SchemaError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from domain.compras import conversation as dialogue
from domain.compras.automatic import propose_purchase
from domain.compras.comercial import ComprasComerciais
from domain.compras.comercial_schemas import CompraRevisada, LeituraCompra
from domain.compras.reconhecimento import ReconhecimentoCompras
from domain.compras.repository import ComprasRepository
from domain.compras.review_errors import (
    PurchaseReviewConflict,
    PurchaseReviewError,
    PurchaseReviewUnavailable,
    detail,
    issue,
)
from domain.estoque.repository import EstoqueRepository
from domain.estoque.service import EstoqueService
from domain.exceptions import ValidationError
from infrastructure.database.central_models import CentralCompra
from infrastructure.database.models import Tenant, Usuario
from infrastructure.database.session import get_db
from infrastructure.ocr.central_vision import CentralVisionExtractor
from infrastructure.ocr.hybrid import HybridReceiptExtractor


async def authenticated(authorization: str = Header(default="")) -> None:
    """A chave é exclusiva deste serviço; usuário/tenant são resolvidos novamente."""
    token = settings.central_service_token.get_secret_value()
    if not settings.central_enabled:
        raise HTTPException(404, "Integração desativada")
    if len(token) < 32 or not hmac.compare_digest(
        authorization.encode("utf-8"), ("Bearer " + token).encode("utf-8")
    ):
        raise HTTPException(401, "Serviço não autorizado")


router = APIRouter(prefix="/central", tags=["Central"], dependencies=[Depends(authenticated)])


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class Identity(Input):
    business_id: UUID
    sender_phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    operation: Literal["purchases.review", "stock.receive", "recipes.search", "recipes.read"]
    scope: dict | None = None
    resource_id: str | None = None


class Extract(Identity):
    conversation_id: UUID
    incoming_message_id: UUID
    content_base64: str = Field(min_length=1, max_length=27962028)
    mime: Literal["image/jpeg", "image/png", "image/webp"]


class Proposal(Identity):
    proposal_id: UUID


class Review(Proposal):
    renew_expired: bool = Field(default=False, strict=True)
    expected_version: int = Field(ge=1)
    reviewed: CompraRevisada


class ConversationDraft(Proposal):
    operation: Literal["purchases.review"]
    action: Literal["read", "patch", "lookup"]
    expected_version: int | None = Field(default=None, ge=1, strict=True)
    incoming_message_id: UUID | None = None
    edits: list[dialogue.Edit] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def action_fields(self):
        if self.action == "patch":
            if self.expected_version is None or not self.incoming_message_id or not self.edits:
                raise ValueError("Mensagem, versão e alterações obrigatórias")
        elif self.edits or self.expected_version is not None:
            raise ValueError("Leitura e consulta não recebem alterações")
        if self.action == "lookup" and not self.incoming_message_id:
            raise ValueError("Mensagem obrigatória")
        if self.action == "read" and self.incoming_message_id is not None:
            raise ValueError("Leitura não recebe mensagem")
        return self


class Decision(Proposal):
    expected_version: int = Field(ge=1)
    summary_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    approved: bool = Field(strict=True)
    incoming_message_id: UUID


class Operation(Input):
    operation_id: UUID
    command_id: UUID
    business_id: UUID
    capability_code: Literal["stock.receive", "purchases.review"]
    payload: dict
    authorization_receipt_ref: UUID | None = None
    approval_receipt_ref: UUID | None = None
    expected_resource_version: str | None = None
    idempotency_key: UUID
    conversation_id: UUID | None = None
    principal_ref: UUID
    scope: dict

    @model_validator(mode="after")
    def registered_payload(self):
        key = "proposal_ref" if self.capability_code == "stock.receive" else "resource_ref"
        if set(self.payload) != {key}:
            raise ValueError("Payload incompatível com a capacidade")
        try:
            UUID(self.payload[key])
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Referência inválida") from None
        return self


class Reference(Input):
    operation_id: UUID
    business_id: UUID
    capability_code: Literal["stock.receive", "purchases.review"]
    principal_ref: UUID
    scope: dict
    idempotency_key: UUID
    external_reference: str | None = None


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def operation_digest(operation: Operation) -> str:
    return digest(
        operation.model_dump(
            mode="json",
            exclude={"authorization_receipt_ref", "approval_receipt_ref", "principal_ref", "scope"},
        )
    )


def commercial(db: AsyncSession) -> ComprasComerciais:
    return ComprasComerciais(ComprasRepository(db), EstoqueService(EstoqueRepository(db)))


async def actor(
    db: AsyncSession,
    business_id: UUID,
    *,
    phone: str | None = None,
    principal: UUID | None = None,
    scope: dict | None = None,
) -> Usuario:
    """Grant administrativo fixa o tenant; telefone nunca escolhe outro negócio."""
    tenant = settings.central_business_tenants.get(business_id)
    if tenant is None or (
        scope is not None and scope != {"tenant_id": str(tenant), "company_id": None}
    ):
        raise HTTPException(403, "Negócio não autorizado")
    query = (
        select(Usuario)
        .join(Tenant)
        .where(
            Usuario.tenant_id == tenant,
            Usuario.ativo.is_(True),
            Usuario.deleted_at.is_(None),
            Usuario.is_superuser.is_(False),
            Tenant.ativo.is_(True),
            Tenant.deleted_at.is_(None),
        )
    )
    query = (
        query.where(Usuario.telefone == phone) if phone else query.where(Usuario.id == principal)
    )
    user = await db.scalar(query.with_for_update(of=Usuario))
    if not user or not user.telefone:
        raise HTTPException(403, "Solicitante sem vínculo ativo")
    return user


async def owned(
    db: AsyncSession, identity: Proposal, *, allow_expired: bool = False
) -> tuple[Usuario, CentralCompra]:
    user = await actor(db, identity.business_id, phone=identity.sender_phone, scope=identity.scope)
    row = await db.scalar(
        select(CentralCompra)
        .where(
            CentralCompra.id == identity.proposal_id,
            CentralCompra.tenant_id == user.tenant_id,
            CentralCompra.usuario_id == user.id,
            CentralCompra.business_id == identity.business_id,
            CentralCompra.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if not row:
        raise HTTPException(404, "Compra não encontrada")
    if row.telefone != user.telefone:
        raise HTTPException(403, "Vínculo do solicitante alterado; revise no Fornada")
    if not allow_expired and row.expira_em <= datetime.now(UTC) and row.estado != "confirmed":
        raise HTTPException(409, "Proposta expirada; revise diretamente no Fornada")
    return user, row


def view(row: CentralCompra) -> dict:
    return {
        "id": str(row.id),
        "business_id": str(row.business_id),
        "principal_ref": str(row.usuario_id),
        "scope": {"tenant_id": str(row.tenant_id), "company_id": None},
        "conversation_id": str(row.conversation_id),
        "version": row.revisao,
        "state": row.estado,
        "reading": row.leitura,
        "reviewed": dialogue.reviewed(row.dialogo) if row.dialogo else row.revisada,
        "preview": row.previa,
        "summary_hash": row.resumo_hash,
        "result": row.resultado,
    }


class NoPublicVision:
    async def processar_imagem(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> object:
        """Leitura local incompleta exige revisão; jamais chama visão pública."""
        raise ValidationError(
            "Não foi possível ler o cupom localmente. Revise a imagem no atendimento."
        )


def recognition(db: AsyncSession) -> ReconhecimentoCompras:
    extractor = (
        CentralVisionExtractor(settings)
        if settings.central_public_ocr_enabled
        else HybridReceiptExtractor(NoPublicVision())
    )
    return ReconhecimentoCompras(commercial(db), extractor)


@router.post("/resolve")
async def resolve(data: Identity, db: AsyncSession = Depends(get_db)) -> dict:
    user = await actor(db, data.business_id, phone=data.sender_phone, scope=data.scope)
    if data.operation.startswith("recipes."):
        from domain.receitas.repository import ReceitaRepository

        if data.operation == "recipes.read":
            try:
                resource = UUID(data.resource_id or "")
            except ValueError:
                raise HTTPException(403, "Recurso não autorizado") from None
            if not await ReceitaRepository(db).buscar_por_id(resource, user.tenant_id):
                raise HTTPException(403, "Recurso não autorizado")
        elif data.resource_id:
            raise HTTPException(403, "Recurso não autorizado")
        return {
            "decision": "ALLOWED",
            "principal_ref": str(user.id),
            "scope": {"tenant_id": str(user.tenant_id), "company_id": None},
            "synthetic": False,
        }
    if data.resource_id:
        try:
            resource = UUID(data.resource_id)
        except ValueError:
            raise HTTPException(403, "Recurso não autorizado") from None
        row = await db.scalar(
            select(CentralCompra).where(
                CentralCompra.tenant_id == user.tenant_id,
                CentralCompra.business_id == data.business_id,
                CentralCompra.usuario_id == user.id,
                CentralCompra.deleted_at.is_(None),
                or_(
                    CentralCompra.id == resource,
                    CentralCompra.resultado["compra_id"].astext == str(resource),
                ),
            )
        )
        if not row or (data.operation == "stock.receive" and row.id != resource):
            raise HTTPException(403, "Recurso não autorizado")
    return {
        "decision": "ALLOWED",
        "principal_ref": str(user.id),
        "scope": {"tenant_id": str(user.tenant_id), "company_id": None},
        "synthetic": False,
    }


async def prepare_known(db: AsyncSession, row: CentralCompra) -> None:
    """Prepare catalog changes and stock receipt for explicit recipient approval."""
    if row.leitura.get("fonte") not in {"tesseract", "google_vision"}:
        return
    try:
        reading = LeituraCompra.model_validate(row.leitura)
        service = commercial(db)
        reviewed = propose_purchase(
            reading,
            await service.repo.produtos(row.tenant_id),
            await service.estoque.listar(row.tenant_id),
            await service.repo.fornecedores(row.tenant_id),
        )
        preview = await service.prever(row.tenant_id, reviewed)
        if (
            not preview.pode_confirmar
            or preview.duplicidade
            or preview.total_selecionado != reading.total_nota
        ):
            return
        row.revisada, row.previa = reviewed.model_dump(mode="json"), preview.model_dump(mode="json")
        row.resumo_hash = digest({"reviewed": row.revisada, "preview": row.previa})
        row.revisao, row.estado = (row.revisao or 1) + 1, "awaiting_approval"
    except (ValueError, ValidationError):
        return


@router.post("/extract")
async def extract(data: Extract, db: AsyncSession = Depends(get_db)) -> dict:
    user = await actor(db, data.business_id, phone=data.sender_phone, scope=data.scope)
    try:
        content = base64.b64decode(data.content_base64, validate=True)
        if not content or len(content) > 20 * 1024 * 1024:
            raise ValueError()
        with Image.open(io.BytesIO(content)) as image:
            expected = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(
                image.format
            )
            if expected != data.mime or image.width * image.height > 25000000:
                raise ValueError()
            image.verify()
    except (ValueError, UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(422, "Envie uma imagem válida de até 20 MiB") from None
    media_hash = hashlib.sha256(content).hexdigest()
    await db.scalar(select(Tenant).where(Tenant.id == user.tenant_id).with_for_update())
    # Actor lock serializes the recipient; cross-recipient duplicates are not disclosed.
    prior = await db.scalar(
        select(CentralCompra).where(
            CentralCompra.tenant_id == user.tenant_id,
            CentralCompra.business_id == data.business_id,
            CentralCompra.media_hash == media_hash,
        )
    )
    if prior:
        if prior.usuario_id != user.id or prior.conversation_id != data.conversation_id:
            raise HTTPException(409, "Cupom precisa de revisão no atendimento")
        if not (
            settings.central_public_ocr_enabled
            and prior.estado == "review"
            and (
                prior.leitura.get("fonte") == "unavailable"
                or (prior.leitura.get("fonte") == "google_vision" and prior.leitura.get("avisos"))
            )
            and not prior.revisada
            and not prior.resumo_hash
            and not prior.aprovacao_ref
            and not prior.operation_id
            and not prior.resultado
        ):
            return view(prior)
    reading: dict
    if settings.central_local_ocr_enabled or settings.central_public_ocr_enabled:
        try:
            extracted = await recognition(db).ler(user.tenant_id, content, data.mime)
            if extracted.aviso_mock or extracted.fonte == "mock":
                raise ValidationError("Leitura indisponível")
            reading = extracted.model_dump(mode="json")
        except ValidationError:
            reading = {
                "itens": [],
                "avisos": ["Revise o cupom no atendimento; leitura incompleta ou indisponível."],
                "fonte": "unavailable",
            }
    else:
        reading = {
            "itens": [],
            "avisos": ["Leitura local ainda não habilitada; revisão humana necessária."],
            "fonte": "unavailable",
        }
    if prior and reading.get("fonte") == "unavailable":
        # A failed provider retry must not erase an earlier readable draft.
        return view(prior)
    row = prior or CentralCompra(
        tenant_id=user.tenant_id,
        business_id=data.business_id,
        usuario_id=user.id,
        conversation_id=data.conversation_id,
        incoming_message_id=data.incoming_message_id,
        telefone=user.telefone,
        media_hash=media_hash,
        leitura=reading,
        expira_em=datetime.now(UTC) + timedelta(hours=24),
    )
    if prior:
        row.leitura = reading
        row.revisao += 1
        row.expira_em = datetime.now(UTC) + timedelta(hours=24)
    db.add(row)
    await prepare_known(db, row)
    await db.commit()
    return view(row)


@router.post("/draft")
async def draft(data: Proposal, db: AsyncSession = Depends(get_db)) -> dict:
    _, row = await owned(db, data)
    return view(row)


@router.post("/catalog")
async def catalog(data: Identity, db: AsyncSession = Depends(get_db)) -> dict:
    user = await actor(db, data.business_id, phone=data.sender_phone, scope=data.scope)
    service = commercial(db)
    products = await service.catalogo.listar_produtos(user.tenant_id, None, None, 200, 0)
    suppliers = await service.catalogo.listar_fornecedores(user.tenant_id, None, 200, 0)
    return {
        "materials": [
            {"id": str(i.id), "name": i.nome, "unit": i.unidade, "type": i.tipo}
            for i in await service.estoque.listar(user.tenant_id)
        ],
        "products": [p.model_dump(mode="json") for p in products.itens],
        "suppliers": [f.model_dump(mode="json") for f in suppliers.itens],
        "truncated": products.total > 200 or suppliers.total > 200,
    }


async def conversation_snapshot(db, user, row):
    dialog = dialogue.seed(row)
    issues = []
    try:
        value = CompraRevisada.model_validate(dialogue.reviewed(dialog))
        preview = await commercial(db).prever(user.tenant_id, value)
        for result in preview.itens:
            issues.extend(issue(code, result.indice) for code in result.pendencias_codigos)
        if preview.duplicidade:
            issues.append(issue("duplicate_review_required"))
        ready = preview.pode_confirmar and not issues
        if not ready and not issues:
            issues.append(issue("review_invalid"))
    except SchemaError as exc:
        ready = False
        for error in exc.errors(include_input=False):
            loc = error["loc"]
            index = (
                loc[1] if len(loc) > 1 and loc[0] == "itens" and isinstance(loc[1], int) else None
            )
            issues.append(
                {
                    "code": "draft_field_required",
                    "item_index": index,
                    "field": ".".join(str(k) for k in loc[2:] if k is not None)
                    if index is not None
                    else ".".join(str(k) for k in loc),
                    "message": "Confira este campo antes de preparar o resumo.",
                }
            )
    except (PurchaseReviewError, PurchaseReviewConflict, PurchaseReviewUnavailable) as exc:
        ready = False
        issues.append(exc.issue)
    if (
        row.estado not in {"review", "awaiting_approval", "approved"}
        or row.operation_id
        or row.resultado
    ):
        ready = False
        issues.append(
            {
                "code": "draft_edit_not_allowed",
                "item_index": None,
                "field": None,
                "message": "Consulte o resultado desta compra.",
            }
        )
    return view(row) | {
        "summary_hash": (
            row.resumo_hash if ready and dialogue.reviewed(dialog) == row.revisada else None
        ),
        "conversation_draft": dialog["draft"],
        "issues": issues,
        "ready_for_review": ready,
        "expired": row.expira_em <= datetime.now(UTC),
    }


@router.post("/conversation-draft")
async def conversation_draft(data: ConversationDraft, db: AsyncSession = Depends(get_db)):
    user, row = await owned(db, data, allow_expired=True)
    if data.action == "patch" and (
        row.estado not in {"review", "awaiting_approval", "approved"}
        or row.operation_id
        or row.resultado
    ):
        raise HTTPException(409, "Rascunho não pode mais ser alterado")
    dialog = dialogue.seed(row)
    if data.action == "lookup":
        if not data.incoming_message_id:
            raise HTTPException(422, "Mensagem obrigatória")
        if str(data.incoming_message_id) not in dialog["applied"]:
            raise HTTPException(404, "Alteração não encontrada")
    elif data.action == "patch":
        if not data.incoming_message_id or not data.edits or data.expected_version is None:
            raise HTTPException(422, "Mensagem, versão e alterações obrigatórias")
        key = str(data.incoming_message_id)
        payload_digest = dialogue.digest(
            {"version": data.expected_version, "edits": [edit.model_dump() for edit in data.edits]}
        )
        if key in dialog["applied"]:
            if dialog["applied"][key] != payload_digest:
                raise HTTPException(409, "Mensagem reutilizada com alterações diferentes")
        else:
            if row.revisao != data.expected_version or len(dialog["applied"]) >= 200:
                raise HTTPException(409, "Atualize a revisão antes de alterar")
            try:
                dialog = dialogue.patch(dialog, data.edits, await catalog(data, db))
            except (ValueError, TypeError) as exc:
                raise HTTPException(
                    422, "Alteração inválida; confira item, campo e catálogo"
                ) from exc
            dialog["applied"][key] = payload_digest
            row.revisao += 1
            row.estado = "review"
            row.resumo_hash = row.aprovacao_ref = row.aprovacao_message_id = None
            row.previa = row.revisada = None
    row.dialogo = dialog
    await db.commit()
    return await conversation_snapshot(db, user, row)


@router.post("/review")
async def review(data: Review, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        user, row = await owned(db, data, allow_expired=data.renew_expired)
    except HTTPException as exc:
        if exc.status_code == 409:
            raise HTTPException(409, detail([issue("proposal_expired")])) from None
        raise
    if (
        row.operation_id
        or row.resultado
        or row.revisao != data.expected_version
        or row.estado
        not in {
            "review",
            "awaiting_approval",
            "approved",
        }
    ):
        raise HTTPException(409, detail([issue("proposal_version_changed")]))
    # A duplicate fiscal note never receives a silent override through the bot.
    if data.reviewed.confirmar_duplicidade:
        raise HTTPException(422, detail([issue("duplicate_review_required")]))
    try:
        preview = await commercial(db).prever(user.tenant_id, data.reviewed)
    except (PurchaseReviewError, PurchaseReviewConflict, PurchaseReviewUnavailable) as exc:
        raise HTTPException(exc.status_code, detail([exc.issue])) from None
    if not preview.pode_confirmar:
        errors = []
        for result in preview.itens:
            errors.extend(issue(code, result.indice) for code in result.pendencias_codigos)
        if preview.duplicidade:
            errors.append(issue("duplicate_review_required"))
        raise HTTPException(422, detail(errors or [issue("review_invalid")]))
    if data.renew_expired and row.expira_em <= datetime.now(UTC):
        row.expira_em = datetime.now(UTC) + timedelta(hours=24)
    row.revisada, row.previa = (
        data.reviewed.model_dump(mode="json"),
        preview.model_dump(mode="json"),
    )
    if row.dialogo:
        updated = dialogue.seed(row)
        draft = json.loads(json.dumps(row.revisada))
        previous = updated["draft"]["itens"]
        used_refs = set()
        for item in draft["itens"]:
            candidates = [p for p in previous if p["item_ref"] not in used_refs]
            matching = next(
                (
                    p
                    for p in candidates
                    if dialogue.reviewed({"draft": {"itens": [p]}})["itens"][0] == item
                ),
                None,
            )
            if matching is None:
                same_description = [
                    p
                    for p in candidates
                    if p.get("descricao_original") == item.get("descricao_original")
                ]
                # Ambiguous manual replacements get new refs, never another group's identity.
                if (
                    len(same_description) == 1
                    and sum(
                        i.get("descricao_original") == item.get("descricao_original")
                        for i in draft["itens"]
                    )
                    == 1
                ):
                    matching = same_description[0]
            item["item_ref"] = matching["item_ref"] if matching else str(uuid4())
            item["occurrences"] = matching.get("occurrences", 1) if matching else 1
            used_refs.add(item["item_ref"])
        updated["draft"] = draft
        row.dialogo = updated
    row.resumo_hash = digest({"reviewed": row.revisada, "preview": row.previa})
    row.revisao += 1
    row.estado, row.aprovacao_ref, row.aprovacao_message_id = "awaiting_approval", None, None
    await db.commit()
    return view(row)


async def current_preview(db: AsyncSession, user: Usuario, row: CentralCompra) -> CompraRevisada:
    """A revisão aprovada deixa de valer se catálogo/conversão/prévia mudarem."""
    if not row.revisada:
        raise HTTPException(409, "Revise o cupom antes de aprovar")
    reviewed = CompraRevisada.model_validate(row.revisada)
    preview = await commercial(db).prever(user.tenant_id, reviewed)
    if (
        not preview.pode_confirmar
        or digest({"reviewed": row.revisada, "preview": preview.model_dump(mode="json")})
        != row.resumo_hash
    ):
        raise HTTPException(409, "A compra mudou; gere outro resumo")
    return reviewed


@router.post("/decision")
async def decision(data: Decision, db: AsyncSession = Depends(get_db)) -> dict:
    user, row = await owned(db, data)
    if (
        row.aprovacao_message_id == data.incoming_message_id
        and row.resumo_hash == data.summary_hash
    ):
        expected_state = "approved" if data.approved else "rejected"
        if row.estado != expected_state and not (data.approved and row.estado == "confirmed"):
            raise HTTPException(409, "Decisao ja registrada")
        return view(row)
    if (
        row.revisao != data.expected_version
        or row.resumo_hash != data.summary_hash
        or row.estado != "awaiting_approval"
    ):
        raise HTTPException(409, "Resumo obsoleto ou já respondido")
    if data.approved:
        await current_preview(db, user, row)
    row.estado = "approved" if data.approved else "rejected"
    row.aprovacao_ref, row.aprovacao_message_id = uuid4(), data.incoming_message_id
    await db.commit()
    return view(row)


async def operation_proposal(db: AsyncSession, data: Operation) -> tuple[Usuario, CentralCompra]:
    user = await actor(db, data.business_id, principal=data.principal_ref, scope=data.scope)
    try:
        proposal_id = UUID(data.payload["proposal_ref"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(422, "Proposta inválida") from None
    identity = Proposal(
        business_id=data.business_id,
        sender_phone=user.telefone,
        operation="stock.receive",
        scope=data.scope,
        proposal_id=proposal_id,
    )
    _, row = await owned(db, identity)
    if (
        row.estado not in {"approved", "confirmed"}
        or not row.aprovacao_ref
        or data.expected_resource_version != str(row.revisao)
        or str(data.conversation_id) != str(row.conversation_id)
    ):
        raise HTTPException(409, "Aprovação específica necessária")
    return user, row


@router.post("/approval")
async def approval(data: Operation, db: AsyncSession = Depends(get_db)) -> dict:
    if data.capability_code != "stock.receive":
        raise HTTPException(422, "Aprovação disponível apenas para entrada de estoque")
    user, row = await operation_proposal(db, data)
    if row.estado != "confirmed":
        await current_preview(db, user, row)
    return {
        "request_digest": operation_digest(data),
        "principal_ref": str(user.id),
        "scope": data.scope,
        "approval_ref": str(row.aprovacao_ref),
        "resource_version": str(row.revisao),
    }


def result(row: CentralCompra) -> dict:
    return {
        "status": "confirmed",
        "business_id": str(row.business_id),
        "principal_ref": str(row.usuario_id),
        "scope": {"tenant_id": str(row.tenant_id), "company_id": None},
        "external_reference": str(row.resultado["compra_id"]),
        "resource_version": str(row.revisao),
        "evidence_ref": "fornada:compra:" + str(row.resultado["compra_id"]),
        "data": {"resource_ref": str(row.resultado["compra_id"]), "state": "confirmed"},
        "intervention_required": False,
    }


@router.post("/execute")
async def execute(data: Operation, db: AsyncSession = Depends(get_db)) -> dict:
    if data.capability_code == "purchases.review":
        user = await actor(db, data.business_id, principal=data.principal_ref, scope=data.scope)
        try:
            resource = UUID(data.payload["resource_ref"])
        except (KeyError, ValueError, TypeError):
            raise HTTPException(422, "Compra inválida") from None
        row = await db.scalar(
            select(CentralCompra).where(
                CentralCompra.tenant_id == user.tenant_id,
                CentralCompra.business_id == data.business_id,
                CentralCompra.usuario_id == user.id,
                CentralCompra.deleted_at.is_(None),
                or_(
                    CentralCompra.id == resource,
                    CentralCompra.resultado["compra_id"].astext == str(resource),
                ),
            )
        )
        if not row:
            raise HTTPException(404, "Compra não encontrada")
        return {
            "status": "confirmed",
            "business_id": str(data.business_id),
            "principal_ref": str(user.id),
            "scope": data.scope,
            "external_reference": str(row.id),
            "evidence_ref": "fornada:proposal:" + str(row.id),
            "resource_version": str(row.revisao),
            "data": {"resource_ref": str(resource), "state": row.estado},
        }
    if data.capability_code != "stock.receive":
        raise HTTPException(422, "Operação não disponível neste fluxo")
    user, row = await operation_proposal(db, data)
    fingerprint = operation_digest(data)
    if row.resultado:
        if row.operation_id != data.operation_id or row.operation_digest != fingerprint:
            raise HTTPException(409, "A compra já foi registrada por outra operação")
        return result(row)
    reviewed = await current_preview(db, user, row)
    row.operation_id, row.idempotency_key, row.operation_digest = (
        data.operation_id,
        data.idempotency_key,
        fingerprint,
    )
    confirmed = await commercial(db).confirmar(
        user.tenant_id, reviewed, data.idempotency_key, usuario=user.id, origem="whatsapp_central"
    )
    row.resultado, row.estado = confirmed.model_dump(mode="json"), "confirmed"
    await db.commit()
    return result(row)


@router.post("/reconcile")
async def reconcile(data: Reference, db: AsyncSession = Depends(get_db)) -> dict:
    user = await actor(db, data.business_id, principal=data.principal_ref, scope=data.scope)
    row = await db.scalar(
        select(CentralCompra).where(
            CentralCompra.tenant_id == user.tenant_id,
            CentralCompra.business_id == data.business_id,
            CentralCompra.usuario_id == user.id,
            CentralCompra.operation_id == data.operation_id,
            CentralCompra.idempotency_key == data.idempotency_key,
            CentralCompra.deleted_at.is_(None),
        )
    )
    return (
        result(row)
        if row and row.resultado
        else {
            "status": "unknown",
            "business_id": str(data.business_id),
            "principal_ref": str(user.id),
            "scope": data.scope,
            "intervention_required": True,
        }
    )
