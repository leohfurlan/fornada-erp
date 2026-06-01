from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_id
from domain.estoque_pa.repository import EstoquePARepository
from domain.estoque_pa.schemas import (
    AtualizarEstoquePARequest,
    EstoquePAResponse,
    MovimentacaoEstoquePAResponse,
)
from domain.estoque_pa.service import EstoquePAService
from infrastructure.database.session import get_db

router = APIRouter(prefix="/estoque-pa", tags=["Estoque produto acabado"])


def get_estoque_pa_service(db: AsyncSession = Depends(get_db)) -> EstoquePAService:
    return EstoquePAService(EstoquePARepository(db))


@router.get("", response_model=list[EstoquePAResponse])
async def listar_saldos(
    tenant_id: UUID = Depends(get_tenant_id),
    service: EstoquePAService = Depends(get_estoque_pa_service),
) -> list[EstoquePAResponse]:
    """Lista todos os saldos de produto acabado com status (ok/baixo/zerado)."""
    return await service.listar_saldos(tenant_id)


@router.get("/{receita_id}", response_model=EstoquePAResponse)
async def buscar_saldo(
    receita_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: EstoquePAService = Depends(get_estoque_pa_service),
) -> EstoquePAResponse:
    return await service.buscar_saldo(receita_id, tenant_id)


@router.patch("/{receita_id}", response_model=EstoquePAResponse)
async def atualizar_qtd_minima(
    receita_id: UUID,
    data: AtualizarEstoquePARequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: EstoquePAService = Depends(get_estoque_pa_service),
    db: AsyncSession = Depends(get_db),
) -> EstoquePAResponse:
    """Ajusta o gatilho de alerta de estoque baixo."""
    result = await service.atualizar_qtd_minima(receita_id, tenant_id, data.qtd_minima)
    await db.commit()
    return result


@router.get(
    "/{receita_id}/movimentacoes",
    response_model=list[MovimentacaoEstoquePAResponse],
)
async def listar_movimentacoes(
    receita_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant_id: UUID = Depends(get_tenant_id),
    service: EstoquePAService = Depends(get_estoque_pa_service),
) -> list[MovimentacaoEstoquePAResponse]:
    """Histórico de entradas/saídas do produto acabado, mais recente primeiro."""
    return await service.listar_movimentacoes(receita_id, tenant_id, limit, offset)
