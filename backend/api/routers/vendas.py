from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_id
from domain.estoque_pa.repository import EstoquePARepository
from domain.estoque_pa.service import EstoquePAService
from domain.vendas.repository import VendasRepository
from domain.vendas.schemas import CriarVendaRequest, VendaResponse
from domain.vendas.service import VendasService
from infrastructure.database.session import get_db

router = APIRouter(prefix="/vendas", tags=["Vendas"])


def get_vendas_service(db: AsyncSession = Depends(get_db)) -> VendasService:
    estoque_pa = EstoquePAService(EstoquePARepository(db))
    return VendasService(VendasRepository(db), estoque_pa)


@router.post("", response_model=VendaResponse, status_code=status.HTTP_201_CREATED)
async def criar_venda(
    data: CriarVendaRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: VendasService = Depends(get_vendas_service),
    db: AsyncSession = Depends(get_db),
) -> VendaResponse:
    """Registra venda multicanal e debita estoque de produto acabado."""
    result = await service.criar(tenant_id, data)
    await db.commit()
    return result


@router.get("", response_model=list[VendaResponse])
async def listar_vendas(
    canal: str | None = Query(None),
    cliente_id: UUID | None = None,
    data_de: date | None = None,
    data_ate: date | None = None,
    tenant_id: UUID = Depends(get_tenant_id),
    service: VendasService = Depends(get_vendas_service),
) -> list[VendaResponse]:
    return await service.listar(
        tenant_id,
        canal=canal,
        cliente_id=cliente_id,
        data_de=data_de,
        data_ate=data_ate,
    )


@router.get("/{venda_id}", response_model=VendaResponse)
async def buscar_venda(
    venda_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: VendasService = Depends(get_vendas_service),
) -> VendaResponse:
    return await service.buscar(venda_id, tenant_id)


@router.delete("/{venda_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancelar_venda(
    venda_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: VendasService = Depends(get_vendas_service),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Cancela venda: estorna estoque PA e marca como deletada."""
    await service.cancelar(venda_id, tenant_id)
    await db.commit()
