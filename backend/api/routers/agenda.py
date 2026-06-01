from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_id
from domain.agenda.repository import AgendaRepository
from domain.agenda.schemas import (
    AgendaItemResponse,
    AtualizarAgendaItemRequest,
    ConcluirAgendaItemRequest,
    CriarAgendaItemRequest,
    MoverAgendaItemRequest,
)
from domain.agenda.service import AgendaService
from domain.exceptions import ValidationError
from infrastructure.database.session import get_db

router = APIRouter(prefix="/agenda", tags=["Agenda"])


def get_agenda_service(db: AsyncSession = Depends(get_db)) -> AgendaService:
    return AgendaService(AgendaRepository(db))


@router.get("", response_model=list[AgendaItemResponse])
async def listar_agenda(
    view: Literal["mes", "semana", "dia"] = Query("semana"),
    data: date | None = Query(None, description="Data de referência (semana/dia)"),
    ano: int | None = Query(None),
    mes: int | None = Query(None),
    tenant_id: UUID = Depends(get_tenant_id),
    service: AgendaService = Depends(get_agenda_service),
) -> list[AgendaItemResponse]:
    """Lista itens da agenda por período.

    - `view=semana&data=YYYY-MM-DD` → segunda a domingo da semana de `data`
    - `view=dia&data=YYYY-MM-DD`    → apenas o dia
    - `view=mes&ano=YYYY&mes=M`     → mês inteiro
    """
    if view == "mes":
        if ano is None or mes is None:
            raise ValidationError("Informe ano e mês para a visualização de mês")
        return await service.listar_mes(tenant_id, ano, mes)
    if data is None:
        raise ValidationError("Informe a data de referência")
    if view == "dia":
        return await service.listar_dia(tenant_id, data)
    return await service.listar_semana(tenant_id, data)


@router.post("", response_model=AgendaItemResponse, status_code=status.HTTP_201_CREATED)
async def criar_item(
    dados: CriarAgendaItemRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: AgendaService = Depends(get_agenda_service),
    db: AsyncSession = Depends(get_db),
) -> AgendaItemResponse:
    result = await service.criar_item(tenant_id, dados)
    await db.commit()
    return result


@router.patch("/{item_id}", response_model=AgendaItemResponse)
async def atualizar_item(
    item_id: UUID,
    dados: AtualizarAgendaItemRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: AgendaService = Depends(get_agenda_service),
    db: AsyncSession = Depends(get_db),
) -> AgendaItemResponse:
    result = await service.atualizar_item(tenant_id, item_id, dados)
    await db.commit()
    return result


@router.patch("/{item_id}/concluir", response_model=AgendaItemResponse)
async def concluir_item(
    item_id: UUID,
    dados: ConcluirAgendaItemRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: AgendaService = Depends(get_agenda_service),
    db: AsyncSession = Depends(get_db),
) -> AgendaItemResponse:
    """Marca o item como concluído ou pendente (toggle controlado pelo body)."""
    result = await service.marcar_concluido(tenant_id, item_id, dados.concluido)
    await db.commit()
    return result


@router.patch("/{item_id}/mover", response_model=AgendaItemResponse)
async def mover_item(
    item_id: UUID,
    dados: MoverAgendaItemRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: AgendaService = Depends(get_agenda_service),
    db: AsyncSession = Depends(get_db),
) -> AgendaItemResponse:
    """Reposiciona o item (drag-and-drop) — altera só data e horário."""
    result = await service.mover_item(tenant_id, item_id, dados)
    await db.commit()
    return result


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_item(
    item_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: AgendaService = Depends(get_agenda_service),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.deletar_item(tenant_id, item_id)
    await db.commit()
