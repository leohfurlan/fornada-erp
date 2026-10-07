from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import require_superuser
from infrastructure.database.models import SessaoAdministrativa, Tenant, Usuario
from infrastructure.database.session import get_db

router = APIRouter(prefix="/admin", tags=["Administração"])
logger = structlog.get_logger(__name__)


class ContaResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    nome: str
    email: str
    negocio: str
    ativo: bool
    is_superuser: bool


class IniciarSuporteRequest(BaseModel):
    usuario_id: UUID
    motivo: str = Field(min_length=5, max_length=500)

    @field_validator("motivo", mode="before")
    @classmethod
    def limpar_motivo(cls, value: str) -> str:
        return value.strip()


class SuporteResponse(BaseModel):
    id: UUID
    expires_at: datetime
    conta: ContaResponse


def conta_response(usuario: Usuario, tenant: Tenant) -> ContaResponse:
    return ContaResponse(
        id=usuario.id,
        tenant_id=tenant.id,
        nome=usuario.nome,
        email=usuario.email,
        negocio=tenant.nome,
        ativo=usuario.ativo and tenant.ativo,
        is_superuser=usuario.is_superuser,
    )


@router.get("/usuarios", response_model=list[ContaResponse])
async def listar_contas(
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    actor: Usuario = Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
) -> list[ContaResponse]:
    """Diretório global autorizado somente ao operador da plataforma."""
    query = (
        select(Usuario, Tenant)
        .join(Tenant)
        .where(
            Usuario.deleted_at.is_(None),
            Tenant.deleted_at.is_(None),
        )
    )
    if q.strip():
        term = q.strip().lower()
        query = query.where(
            func.lower(Usuario.email).contains(term, autoescape=True)
            | func.lower(Usuario.nome).contains(term, autoescape=True)
            | func.lower(Tenant.nome).contains(term, autoescape=True)
        )
    rows = (
        await db.execute(query.order_by(Usuario.email, Usuario.id).limit(limit).offset(offset))
    ).all()
    return [conta_response(user, tenant) for user, tenant in rows]


@router.post("/suporte", response_model=SuporteResponse, status_code=201)
async def iniciar_suporte(
    data: IniciarSuporteRequest,
    actor: Usuario = Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
) -> SuporteResponse:
    row = (
        await db.execute(
            select(Usuario, Tenant)
            .join(Tenant)
            .where(
                Usuario.id == data.usuario_id,
                Usuario.deleted_at.is_(None),
                Tenant.deleted_at.is_(None),
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    target, tenant = row
    if target.is_superuser or not target.ativo or not tenant.ativo:
        raise HTTPException(status_code=403, detail="Conta indisponível para suporte.")
    session = SessaoAdministrativa(
        tenant_id=tenant.id,
        operador_id=actor.id,
        usuario_id=target.id,
        motivo=data.motivo,
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    db.add(session)
    await db.flush()
    result = SuporteResponse(
        id=session.id, expires_at=session.expires_at, conta=conta_response(target, tenant)
    )
    await db.commit()
    logger.info(
        "suporte_iniciado",
        tenant_id=str(tenant.id),
        user_id=str(actor.id),
        target_user_id=str(target.id),
        action="start",
        entity="sessao_administrativa",
        entity_id=str(session.id),
    )
    return result


@router.delete("/suporte/{session_id}", status_code=204)
async def encerrar_suporte(
    session_id: UUID,
    actor: Usuario = Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
) -> Response:
    session = (
        await db.execute(
            select(SessaoAdministrativa).where(
                SessaoAdministrativa.id == session_id,
                SessaoAdministrativa.operador_id == actor.id,
            )
        )
    ).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Acesso de suporte não encontrado.")
    if not session.ended_at:
        session.ended_at = datetime.now(UTC)
        await db.commit()
        logger.info(
            "suporte_encerrado",
            tenant_id=str(session.tenant_id),
            user_id=str(actor.id),
            action="end",
            entity="sessao_administrativa",
            entity_id=str(session.id),
        )
    return Response(status_code=204)
