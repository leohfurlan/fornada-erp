from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_authenticated_actor, require_superuser
from infrastructure.database.models import Tenant, Usuario
from infrastructure.database.pwa_models import PwaEvento
from infrastructure.database.session import get_db

router = APIRouter(tags=["Instalação PWA"])
logger = structlog.get_logger(__name__)
Tipo = Literal[
    "convite_exibido",
    "adiado",
    "instalar_clicado",
    "confirmacao_aceita",
    "confirmacao_recusada",
    "instalacao_sinalizada",
    "acesso_app",
]
TIPOS = (
    "convite_exibido",
    "adiado",
    "instalar_clicado",
    "confirmacao_aceita",
    "confirmacao_recusada",
    "instalacao_sinalizada",
    "acesso_app",
)


class EventoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: UUID
    browser_id: UUID
    session_id: UUID
    tipo: Tipo
    origem: Literal["automatico", "menu", "navegador", "abertura_app"]

    @model_validator(mode="after")
    def validar_origem(self) -> "EventoRequest":
        permitidas = {
            "convite_exibido": {"automatico"},
            "adiado": {"automatico"},
            "instalar_clicado": {"automatico", "menu"},
            "confirmacao_aceita": {"automatico", "menu"},
            "confirmacao_recusada": {"automatico", "menu"},
            "instalacao_sinalizada": {"navegador"},
            "acesso_app": {"abertura_app"},
        }
        if self.origem not in permitidas[self.tipo]:
            raise ValueError("Origem incompatível com o evento.")
        return self


class EventoResponse(BaseModel):
    event_id: UUID
    recebido_em: datetime


def sem_suporte(
    admin_session: str | None = Header(default=None, alias="X-Admin-Session"),
) -> None:
    if admin_session is not None:
        raise HTTPException(403, "Encerre o suporte para acessar os sinais do aplicativo.")


@router.post(
    "/pwa/eventos",
    response_model=EventoResponse,
    status_code=201,
    dependencies=[Depends(sem_suporte)],
)
async def registrar_evento(
    data: EventoRequest,
    response: Response,
    actor: Usuario = Depends(get_authenticated_actor),
    db: AsyncSession = Depends(get_db),
) -> EventoResponse:
    """Registra sinal idempotente usando exclusivamente a identidade autenticada."""
    values = data.model_dump()
    inserted = (
        await db.execute(
            insert(PwaEvento)
            .values(id=uuid4(), tenant_id=actor.tenant_id, usuario_id=actor.id, **values)
            .on_conflict_do_nothing(constraint="uq_pwa_evento")
            .returning(PwaEvento.id)
        )
    ).scalar_one_or_none()
    row = (
        await db.execute(
            select(PwaEvento).where(
                PwaEvento.tenant_id == actor.tenant_id,
                PwaEvento.usuario_id == actor.id,
                PwaEvento.event_id == data.event_id,
            )
        )
    ).scalar_one()
    if any(getattr(row, key) != value for key, value in values.items()):
        raise HTTPException(409, "Evento já registrado com conteúdo diferente.")
    await db.commit()
    if inserted is not None:
        logger.info(
            "pwa_evento_registrado",
            tenant_id=str(actor.tenant_id),
            user_id=str(actor.id),
            action=data.tipo,
            entity="pwa_evento",
            entity_id=str(row.event_id),
        )
    if inserted is None:
        response.status_code = 200
    return EventoResponse(event_id=row.event_id, recebido_em=row.created_at)


class SinalResponse(BaseModel):
    quantidade: int
    ultimo_em: datetime | None


class UsuarioPwaResponse(BaseModel):
    usuario_id: UUID
    tenant_id: UUID
    nome: str
    email: str
    negocio: str
    sinais: dict[str, SinalResponse]


class PaginaPwaResponse(BaseModel):
    items: list[UsuarioPwaResponse]
    total: int
    limit: int
    offset: int


@router.get(
    "/admin/pwa/usuarios", response_model=PaginaPwaResponse, dependencies=[Depends(sem_suporte)]
)
async def listar_adesao(
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    actor: Usuario = Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
) -> PaginaPwaResponse:
    """Diretório global explícito, autorizado apenas ao administrador da plataforma."""
    query = (
        select(Usuario, Tenant)
        .join(Tenant)
        .where(Usuario.deleted_at.is_(None), Tenant.deleted_at.is_(None))
    )
    if q.strip():
        term = q.strip().lower()
        query = query.where(
            func.lower(Usuario.email).contains(term, autoescape=True)
            | func.lower(Usuario.nome).contains(term, autoescape=True)
            | func.lower(Tenant.nome).contains(term, autoescape=True)
        )
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (
        await db.execute(query.order_by(Usuario.email, Usuario.id).limit(limit).offset(offset))
    ).all()
    items = []
    for user, tenant in rows:
        signals = {tipo: SinalResponse(quantidade=0, ultimo_em=None) for tipo in TIPOS}
        aggregates = (
            await db.execute(
                select(PwaEvento.tipo, func.count(), func.max(PwaEvento.created_at))
                .where(
                    PwaEvento.tenant_id == tenant.id,
                    PwaEvento.usuario_id == user.id,
                    PwaEvento.deleted_at.is_(None),
                )
                .group_by(PwaEvento.tipo)
            )
        ).all()
        for tipo, count, latest in aggregates:
            signals[tipo] = SinalResponse(quantidade=count, ultimo_em=latest)
        items.append(
            UsuarioPwaResponse(
                usuario_id=user.id,
                tenant_id=tenant.id,
                nome=user.nome,
                email=user.email,
                negocio=tenant.nome,
                sinais=signals,
            )
        )
    return PaginaPwaResponse(items=items, total=total, limit=limit, offset=offset)
