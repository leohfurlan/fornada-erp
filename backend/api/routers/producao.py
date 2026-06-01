from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_id
from domain.estoque.repository import EstoqueRepository
from domain.estoque_pa.repository import EstoquePARepository
from domain.estoque_pa.service import EstoquePAService
from domain.producao.repository import ProducaoRepository
from domain.producao.schemas import (
    AtualizarOrdemProducaoRequest,
    CriarOrdemProducaoRequest,
    MudarStatusOPRequest,
    OrdemProducaoResponse,
)
from domain.producao.service import ProducaoService
from infrastructure.database.session import get_db

router = APIRouter(prefix="/producao", tags=["Produção"])


def get_producao_service(db: AsyncSession = Depends(get_db)) -> ProducaoService:
    return ProducaoService(
        ProducaoRepository(db),
        EstoqueRepository(db),
        EstoquePAService(EstoquePARepository(db)),
    )


@router.post(
    "/ordens",
    response_model=OrdemProducaoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_ordem(
    data: CriarOrdemProducaoRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: ProducaoService = Depends(get_producao_service),
    db: AsyncSession = Depends(get_db),
) -> OrdemProducaoResponse:
    result = await service.criar(tenant_id, data)
    await db.commit()
    return result


@router.get("/ordens", response_model=list[OrdemProducaoResponse])
async def listar_ordens(
    status_filtro: str | None = Query(None, alias="status"),
    receita_id: UUID | None = None,
    pedido_id: UUID | None = None,
    data_de: date | None = None,
    data_ate: date | None = None,
    tenant_id: UUID = Depends(get_tenant_id),
    service: ProducaoService = Depends(get_producao_service),
) -> list[OrdemProducaoResponse]:
    return await service.listar(
        tenant_id,
        status=status_filtro,
        receita_id=receita_id,
        pedido_id=pedido_id,
        data_de=data_de,
        data_ate=data_ate,
    )


@router.get("/ordens/{op_id}", response_model=OrdemProducaoResponse)
async def buscar_ordem(
    op_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: ProducaoService = Depends(get_producao_service),
) -> OrdemProducaoResponse:
    return await service.buscar(op_id, tenant_id)


@router.patch("/ordens/{op_id}", response_model=OrdemProducaoResponse)
async def atualizar_ordem(
    op_id: UUID,
    data: AtualizarOrdemProducaoRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: ProducaoService = Depends(get_producao_service),
    db: AsyncSession = Depends(get_db),
) -> OrdemProducaoResponse:
    """Atualiza campos da OP. Permitido apenas enquanto status='planejada'."""
    result = await service.atualizar(op_id, tenant_id, data)
    await db.commit()
    return result


@router.patch("/ordens/{op_id}/status", response_model=OrdemProducaoResponse)
async def mudar_status_ordem(
    op_id: UUID,
    data: MudarStatusOPRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: ProducaoService = Depends(get_producao_service),
    db: AsyncSession = Depends(get_db),
) -> OrdemProducaoResponse:
    """Avança a OP na máquina de estados. Para finalizar, passe `qtd_produzida`."""
    result = await service.mudar_status(op_id, tenant_id, data.status, data.qtd_produzida)
    await db.commit()
    return result


@router.delete("/ordens/{op_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_ordem(
    op_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: ProducaoService = Depends(get_producao_service),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.deletar(op_id, tenant_id)
    await db.commit()
