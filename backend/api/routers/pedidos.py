from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_id
from domain.estoque_pa.repository import EstoquePARepository
from domain.estoque_pa.service import EstoquePAService
from domain.pedidos.repository import PedidosRepository
from domain.pedidos.schemas import (
    AtualizarClienteRequest,
    AtualizarPedidoRequest,
    ClienteResponse,
    CriarClienteRequest,
    CriarPedidoRequest,
    MudarStatusRequest,
    PedidoResponse,
)
from domain.pedidos.service import PedidosService
from infrastructure.database.session import get_db

router = APIRouter(tags=["Pedidos"])


def get_pedidos_service(db: AsyncSession = Depends(get_db)) -> PedidosService:
    estoque_pa = EstoquePAService(EstoquePARepository(db))
    return PedidosService(PedidosRepository(db), estoque_pa)


# --------- Clientes ---------


@router.post("/clientes", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
async def criar_cliente(
    data: CriarClienteRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: PedidosService = Depends(get_pedidos_service),
    db: AsyncSession = Depends(get_db),
) -> ClienteResponse:
    result = await service.criar_cliente(tenant_id, data)
    await db.commit()
    return result


@router.get("/clientes", response_model=list[ClienteResponse])
async def listar_clientes(
    tenant_id: UUID = Depends(get_tenant_id),
    service: PedidosService = Depends(get_pedidos_service),
) -> list[ClienteResponse]:
    return await service.listar_clientes(tenant_id)


@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
async def buscar_cliente(
    cliente_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: PedidosService = Depends(get_pedidos_service),
) -> ClienteResponse:
    return await service.buscar_cliente(cliente_id, tenant_id)


@router.patch("/clientes/{cliente_id}", response_model=ClienteResponse)
async def atualizar_cliente(
    cliente_id: UUID,
    data: AtualizarClienteRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: PedidosService = Depends(get_pedidos_service),
    db: AsyncSession = Depends(get_db),
) -> ClienteResponse:
    result = await service.atualizar_cliente(cliente_id, tenant_id, data)
    await db.commit()
    return result


@router.delete("/clientes/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_cliente(
    cliente_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: PedidosService = Depends(get_pedidos_service),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.deletar_cliente(cliente_id, tenant_id)
    await db.commit()


# --------- Pedidos ---------


@router.post("/pedidos", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
async def criar_pedido(
    data: CriarPedidoRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: PedidosService = Depends(get_pedidos_service),
    db: AsyncSession = Depends(get_db),
) -> PedidoResponse:
    result = await service.criar_pedido(tenant_id, data)
    await db.commit()
    return result


@router.get("/pedidos", response_model=list[PedidoResponse])
async def listar_pedidos(
    status_filtro: str | None = Query(None, alias="status"),
    cliente_id: UUID | None = None,
    data_de: date | None = None,
    data_ate: date | None = None,
    tenant_id: UUID = Depends(get_tenant_id),
    service: PedidosService = Depends(get_pedidos_service),
) -> list[PedidoResponse]:
    return await service.listar_pedidos(
        tenant_id,
        status=status_filtro,
        cliente_id=cliente_id,
        data_de=data_de,
        data_ate=data_ate,
    )


@router.get("/pedidos/{pedido_id}", response_model=PedidoResponse)
async def buscar_pedido(
    pedido_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: PedidosService = Depends(get_pedidos_service),
) -> PedidoResponse:
    return await service.buscar_pedido(pedido_id, tenant_id)


@router.patch("/pedidos/{pedido_id}", response_model=PedidoResponse)
async def atualizar_pedido(
    pedido_id: UUID,
    data: AtualizarPedidoRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: PedidosService = Depends(get_pedidos_service),
    db: AsyncSession = Depends(get_db),
) -> PedidoResponse:
    result = await service.atualizar_pedido(pedido_id, tenant_id, data)
    await db.commit()
    return result


@router.patch("/pedidos/{pedido_id}/status", response_model=PedidoResponse)
async def mudar_status_pedido(
    pedido_id: UUID,
    data: MudarStatusRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: PedidosService = Depends(get_pedidos_service),
    db: AsyncSession = Depends(get_db),
) -> PedidoResponse:
    """Avança o pedido na máquina de estados. Pode disparar reserva/baixa de estoque."""
    result = await service.mudar_status(pedido_id, tenant_id, data.status)
    await db.commit()
    return result


@router.delete("/pedidos/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_pedido(
    pedido_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: PedidosService = Depends(get_pedidos_service),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.deletar_pedido(pedido_id, tenant_id)
    await db.commit()
