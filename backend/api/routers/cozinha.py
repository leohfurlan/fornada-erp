"""Authenticated, tenant-scoped reading station for the kitchen UI."""

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from api.dependencies import get_authenticated_actor
from domain.cozinha.schemas import (
    AcknowledgeRequest,
    HeartbeatRequest,
    KitchenCommand,
    LeaseRequest,
    StationCreate,
)
from domain.cozinha.service import (
    recipe_projection,
    resume_completion,
    station_view,
    update_completion,
    update_ingredient_checks,
)
from domain.cozinha.speech import projection_speech_parts
from domain.receitas.central_snapshot import normalized, search
from infrastructure.database.cozinha_models import CozinhaComando, CozinhaEstacao
from infrastructure.database.models import Usuario
from infrastructure.database.session import get_db

router = APIRouter(prefix="/cozinha", tags=["Modo cozinha"])
LEASE_SECONDS = 30


def deny_support(admin_session: str | None = Header(default=None, alias="X-Admin-Session")) -> None:
    if admin_session is not None:
        raise HTTPException(403, detail="Encerre o suporte para acessar o modo cozinha.")


def station_query(actor: Usuario, station_id: UUID) -> Select[tuple[CozinhaEstacao]]:
    return select(CozinhaEstacao).where(
        CozinhaEstacao.id == station_id,
        CozinhaEstacao.tenant_id == actor.tenant_id,
        CozinhaEstacao.usuario_id == actor.id,
        CozinhaEstacao.deleted_at.is_(None),
    )


async def require_station(
    db: AsyncSession, actor: Usuario, station_id: UUID, *, lock: bool = False
) -> CozinhaEstacao:
    query = station_query(actor, station_id)
    if lock:
        query = query.with_for_update()
    station = await db.scalar(query)
    if station is None:
        raise HTTPException(
            404, detail="Estação não encontrada.", headers={"Cache-Control": "no-store"}
        )
    return station


async def refresh_recipe_state(db: AsyncSession, actor: Usuario, station: CozinhaEstacao) -> bool:
    """Drop an obsolete projection before returning it to the authenticated browser."""
    if station.receita_id is None:
        return False
    try:
        current = await recipe_projection(db, actor.tenant_id, station.receita_id)
    except ValueError:
        current = None
    if current is not None and current["recipe_version"] == station.receita_versao:
        return False
    station.aviso = (
        "A receita foi removida ou precisa de revisão. Escolha uma receita cadastrada válida."
        if current is None
        else "Esta receita foi alterada. Confira a versão atual antes de continuar."
    )
    station.receita_id = None
    station.receita_versao = None
    station.projection = None
    station.bloco_indice = 0
    station.parte_fala_indice = 0
    station.revisao += 1
    return True


def require_lease(station: CozinhaEstacao, lease_id: UUID) -> None:
    now = datetime.now(UTC)
    digest = hashlib.sha256(lease_id.bytes).hexdigest()
    if (
        station.status != "active"
        or station.lease_hash != digest
        or not station.lease_expira_em
        or station.lease_expira_em <= now
    ):
        raise HTTPException(409, detail="A estação não está ativa nesta tela.")


def response_json(value: dict[str, Any], response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    return value


@router.get("/recipes/search")
async def search_recipes(
    response: Response,
    q: str = Query(min_length=1, max_length=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: Usuario = Depends(get_authenticated_actor),
    _: None = Depends(deny_support),
) -> dict[str, Any]:
    query = q.strip()
    if not normalized(query):
        raise HTTPException(422, detail="Digite o nome de uma receita com letras ou números.")
    result = await search(db, actor.tenant_id, query, offset, 5, include_suggestions=True)
    return response_json(result, response)


@router.post("/stations", status_code=status.HTTP_201_CREATED)
async def create_station(
    data: StationCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    actor: Usuario = Depends(get_authenticated_actor),
    _: None = Depends(deny_support),
) -> dict[str, Any]:
    existing = await db.scalar(
        select(CozinhaEstacao).where(
            CozinhaEstacao.tenant_id == actor.tenant_id,
            CozinhaEstacao.usuario_id == actor.id,
            CozinhaEstacao.deleted_at.is_(None),
        )
    )
    if existing:
        return response_json({"station": station_view(existing)}, response)
    await db.execute(
        insert(CozinhaEstacao)
        .values(
            tenant_id=actor.tenant_id,
            usuario_id=actor.id,
            nome=data.name.strip() or "Minha cozinha",
        )
        .on_conflict_do_nothing(constraint="uq_cozinha_estacao_usuario")
    )
    await db.commit()
    station = await db.scalar(
        select(CozinhaEstacao).where(
            CozinhaEstacao.tenant_id == actor.tenant_id,
            CozinhaEstacao.usuario_id == actor.id,
            CozinhaEstacao.deleted_at.is_(None),
        )
    )
    assert station is not None, "A estação deveria existir depois da criação idempotente."
    return response_json({"station": station_view(station)}, response)


@router.get("/stations")
async def list_stations(
    response: Response,
    db: AsyncSession = Depends(get_db),
    actor: Usuario = Depends(get_authenticated_actor),
    _: None = Depends(deny_support),
) -> dict[str, Any]:
    station = await db.scalar(
        select(CozinhaEstacao).where(
            CozinhaEstacao.tenant_id == actor.tenant_id,
            CozinhaEstacao.usuario_id == actor.id,
            CozinhaEstacao.deleted_at.is_(None),
        )
    )
    items = (
        [
            {
                "id": str(station.id),
                "name": station.nome,
                "status": station.status,
                "revision": station.revisao,
            }
        ]
        if station
        else []
    )
    return response_json({"items": items}, response)


@router.get("/stations/{station_id}")
async def get_station(
    station_id: UUID,
    response: Response,
    after_revision: int | None = Query(default=None, ge=0),
    lease_id: UUID = Query(),
    db: AsyncSession = Depends(get_db),
    actor: Usuario = Depends(get_authenticated_actor),
    _: None = Depends(deny_support),
) -> dict[str, Any]:
    station = await require_station(db, actor, station_id, lock=True)
    require_lease(station, lease_id)
    changed_recipe = await refresh_recipe_state(db, actor, station)
    if changed_recipe:
        await db.commit()
        await db.refresh(station)
    unchanged = after_revision == station.revisao
    if not unchanged:
        station.delivered_revision = station.revisao
        await db.commit()
    data = None if unchanged else station_view(station)
    return response_json({"changed": not unchanged, "station": data}, response)


@router.post("/stations/{station_id}/lease")
async def acquire_lease(
    station_id: UUID,
    data: LeaseRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    actor: Usuario = Depends(get_authenticated_actor),
    _: None = Depends(deny_support),
) -> dict[str, Any]:
    station = await require_station(db, actor, station_id, lock=True)
    now = datetime.now(UTC)
    valid_lease = station.lease_expira_em is not None and station.lease_expira_em > now
    if valid_lease and not data.takeover:
        raise HTTPException(409, detail="Esta estação já está aberta em outra tela.")
    if data.expected_revision != station.revisao:
        raise HTTPException(
            409, detail="A estação foi atualizada. Atualize a página e tente novamente."
        )
    await refresh_recipe_state(db, actor, station)
    lease_id = UUID(bytes=secrets.token_bytes(16), version=4)
    station.status = "active"
    station.lease_hash = hashlib.sha256(lease_id.bytes).hexdigest()
    station.lease_expira_em = now + timedelta(seconds=LEASE_SECONDS)
    station.revisao += 1
    station.delivered_revision = station.revisao
    await db.commit()
    await db.refresh(station)
    return response_json(
        {
            "lease_id": str(lease_id),
            "expires_at": station.lease_expira_em.isoformat(),
            "station": station_view(station),
        },
        response,
    )


@router.post("/stations/{station_id}/heartbeat")
async def heartbeat(
    station_id: UUID,
    data: HeartbeatRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    actor: Usuario = Depends(get_authenticated_actor),
    _: None = Depends(deny_support),
) -> dict[str, Any]:
    station = await require_station(db, actor, station_id, lock=True)
    require_lease(station, data.lease_id)
    station.lease_expira_em = datetime.now(UTC) + timedelta(seconds=LEASE_SECONDS)
    await db.commit()
    return response_json({"expires_at": station.lease_expira_em.isoformat()}, response)


@router.post("/stations/{station_id}/commands")
async def command(
    station_id: UUID,
    data: KitchenCommand,
    response: Response,
    db: AsyncSession = Depends(get_db),
    actor: Usuario = Depends(get_authenticated_actor),
    _: None = Depends(deny_support),
) -> dict[str, Any]:
    station = await require_station(db, actor, station_id, lock=True)
    require_lease(station, data.lease_id)
    if await refresh_recipe_state(db, actor, station):
        await db.commit()
        raise HTTPException(
            409, detail="A receita mudou. Confira a versão atual antes de continuar."
        )
    request_payload = data.model_dump(mode="json", exclude={"lease_id", "command_id"})
    request_hash = hashlib.sha256(json.dumps(request_payload, sort_keys=True).encode()).hexdigest()
    prior = await db.scalar(
        select(CozinhaComando).where(
            CozinhaComando.tenant_id == actor.tenant_id,
            CozinhaComando.usuario_id == actor.id,
            CozinhaComando.estacao_id == station.id,
            CozinhaComando.command_id == data.command_id,
        )
    )
    if prior:
        if prior.request_hash != request_hash:
            raise HTTPException(409, detail="Este comando já foi recebido com outro conteúdo.")
        return response_json(prior.receipt, response)
    await db.execute(
        delete(CozinhaComando).where(
            CozinhaComando.tenant_id == actor.tenant_id,
            CozinhaComando.usuario_id == actor.id,
            CozinhaComando.estacao_id == station.id,
            CozinhaComando.created_at < datetime.now(UTC) - timedelta(hours=24),
        )
    )
    if data.expected_revision != station.revisao:
        raise HTTPException(
            409, detail="A receita mudou nesta tela. Atualize a página antes de continuar."
        )
    selection = None
    if data.type == "search_recipe":
        if data.payload.query is None or not data.payload.query.strip():
            raise HTTPException(422, detail="Digite o nome de uma receita.")
        selection = await search(
            db, actor.tenant_id, data.payload.query.strip(), data.payload.offset, 5
        )
        station.selecao_id = uuid4()
        station.resultados_busca = {
            "selection_id": str(station.selecao_id),
            "query": data.payload.query.strip(),
            "offset": data.payload.offset,
            "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            **{
                **selection,
                "items": [
                    {"ordinal": index, **item}
                    for index, item in enumerate(selection["items"], start=1)
                ],
            },
        }
        selection = station.resultados_busca
        if data.payload.offset == 0 and len(selection["items"]) == 1:
            data.type = "open_recipe"
            data.payload.recipe_id = UUID(selection["items"][0]["recipe_id"])
        elif not selection["items"] or data.payload.offset > 0 or len(selection["items"]) > 1:
            station.revisao += 1
            receipt = {
                "command_id": str(data.command_id),
                "revision": station.revisao,
                "status": "selection_required" if selection["items"] else "no_results",
                "station_id": str(station.id),
                "selection": selection,
                "error": None,
            }
            receipt["speech_parts"] = []
            db.add(
                CozinhaComando(
                    tenant_id=actor.tenant_id,
                    usuario_id=actor.id,
                    estacao_id=station.id,
                    command_id=data.command_id,
                    request_hash=request_hash,
                    receipt=receipt,
                )
            )
            await db.commit()
            return response_json(receipt, response)
    elif data.type == "select_recipe":
        saved = station.resultados_busca
        if (
            not saved
            or data.payload.selection_id is None
            or str(station.selecao_id) != str(data.payload.selection_id)
            or datetime.fromisoformat(saved["expires_at"]) <= datetime.now(UTC)
        ):
            raise HTTPException(410, detail="A lista venceu. Faça a busca novamente.")
        item = next(
            (item for item in saved["items"] if item["ordinal"] == data.payload.ordinal), None
        )
        if data.payload.offset != saved["offset"] or item is None:
            raise HTTPException(422, detail="Escolha uma receita da lista exibida.")
        data.type = "open_recipe"
        data.payload.recipe_id = UUID(item["recipe_id"])
    if data.type in ("open_recipe", "search_recipe"):
        if data.payload.recipe_id is None:
            raise HTTPException(422, detail="Selecione uma receita da lista.")
        try:
            projection = await recipe_projection(db, actor.tenant_id, data.payload.recipe_id)
        except ValueError:
            raise HTTPException(
                422, detail="A receita precisa ser revisada antes de abrir."
            ) from None
        if projection is None:
            raise HTTPException(404, detail="Receita não encontrada.")
        projection = resume_completion(station.projection, projection)
        station.receita_id = data.payload.recipe_id
        station.aviso = None
        station.selecao_id = None
        station.resultados_busca = None
        station.receita_versao = projection["recipe_version"]
        station.projection = projection
        station.secao = "ingredients"
        station.bloco_indice = 0
        station.parte_fala_indice = 0
    elif data.type == "set_ingredient_checked":
        if not station.projection:
            raise HTTPException(422, detail="Abra uma receita antes de conferir ingredientes.")
        try:
            station.projection = update_ingredient_checks(
                station.projection, data.payload.block_id, data.payload.completed
            )
        except ValueError as error:
            raise HTTPException(422, detail=str(error)) from error
    elif data.type in ("set_step_completed", "reset_steps"):
        if not station.projection:
            raise HTTPException(422, detail="Abra uma receita antes de concluir etapas.")
        if data.type == "set_step_completed" and (
            data.payload.block_id is None or data.payload.completed is None
        ):
            raise HTTPException(422, detail="Informe a etapa e seu estado de conclusão.")
        try:
            station.projection = update_completion(
                station.projection,
                data.payload.block_id if data.type == "set_step_completed" else None,
                data.payload.completed,
            )
        except ValueError as error:
            raise HTTPException(422, detail=str(error)) from error
    elif data.type == "show_section":
        if not station.projection or data.payload.section is None:
            raise HTTPException(422, detail="Abra uma receita antes de escolher uma seção.")
        blocks = [
            block
            for block in station.projection["blocks"]
            if block["section"] == data.payload.section
        ]
        if not blocks:
            raise HTTPException(422, detail="Esta receita não tem essa seção cadastrada.")
        station.secao, station.bloco_indice = data.payload.section, 0
        station.parte_fala_indice = 0
    elif data.type in ("next", "previous", "repeat", "continue_speech", "resume"):
        if not station.projection:
            raise HTTPException(422, detail="Abra uma receita antes de navegar.")
        blocks = [
            block for block in station.projection["blocks"] if block["section"] == station.secao
        ]
        if data.type == "next" and station.bloco_indice < len(blocks) - 1:
            station.bloco_indice += 1
            station.parte_fala_indice = 0
        elif data.type == "previous" and station.bloco_indice > 0:
            station.bloco_indice -= 1
            station.parte_fala_indice = 0
        elif data.type == "continue_speech":
            parts = projection_speech_parts(station.projection, station.secao, station.bloco_indice)
            if station.parte_fala_indice + 1 < len(parts):
                station.parte_fala_indice += 1
        elif data.type in ("next", "previous"):
            pass
    station.revisao += 1
    receipt = {
        "command_id": str(data.command_id),
        "revision": station.revisao,
        "status": "accepted",
        "station_id": str(station.id),
        "selection": selection,
        "speech_parts": [],
        "error": None,
    }
    db.add(
        CozinhaComando(
            tenant_id=actor.tenant_id,
            usuario_id=actor.id,
            estacao_id=station.id,
            command_id=data.command_id,
            request_hash=request_hash,
            receipt=receipt,
        )
    )
    await db.commit()
    return response_json(receipt, response)


@router.post("/stations/{station_id}/ack")
async def acknowledge(
    station_id: UUID,
    data: AcknowledgeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    actor: Usuario = Depends(get_authenticated_actor),
    _: None = Depends(deny_support),
) -> dict[str, int]:
    station = await require_station(db, actor, station_id, lock=True)
    require_lease(station, data.lease_id)
    if data.revision > (station.delivered_revision or 0) or data.revision < (
        station.rendered_revision or 0
    ):
        raise HTTPException(409, detail="Não foi possível confirmar a atualização desta tela.")
    station.rendered_revision = data.revision
    await db.commit()
    return response_json({"rendered_revision": station.rendered_revision}, response)


@router.post("/stations/{station_id}/close", status_code=status.HTTP_204_NO_CONTENT)
async def close_station(
    station_id: UUID,
    data: HeartbeatRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    actor: Usuario = Depends(get_authenticated_actor),
    _: None = Depends(deny_support),
) -> None:
    station = await require_station(db, actor, station_id, lock=True)
    require_lease(station, data.lease_id)
    station.status = "paused"
    station.lease_hash = None
    station.lease_expira_em = None
    station.revisao += 1
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
