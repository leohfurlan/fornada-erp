"""Testes de integração do fluxo Pedido (Sprint 3 — simplificado).

Após o refator: Pedido não mexe mais em ingredientes. Quem produz é a OP.
Pedido apenas debita estoque de produto acabado (PA) ao entregar.

Cenários:
  - Aprovar pedido → entregar com saldo PA suficiente → debita PA
  - Tentar entregar sem saldo PA → bloqueia com EstoquePAInsuficienteError
  - Cancelar pedido aprovado → não mexe em estoque
"""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from domain.estoque_pa.repository import EstoquePARepository
from domain.estoque_pa.service import EstoquePAService
from domain.exceptions import EstoquePAInsuficienteError, ValidationError
from domain.pedidos.repository import PedidosRepository
from domain.pedidos.schemas import (
    CriarClienteRequest,
    CriarPedidoRequest,
    PedidoItemRequest,
)
from domain.pedidos.service import PedidosService
from infrastructure.database.models import (
    EstoqueProdutoAcabado,
    Receita,
    Tenant,
)


@pytest_asyncio.fixture
async def tenant_id(db: AsyncSession):
    tenant = Tenant(nome="Padaria Teste")
    db.add(tenant)
    await db.flush()
    return tenant.id


@pytest_asyncio.fixture
async def receita(db: AsyncSession, tenant_id):
    r = Receita(
        tenant_id=tenant_id,
        nome="Brownie",
        categoria="Doce",
        rendimento=Decimal("1"),
        rendimento_unidade="unidade",
        margem_desejada=Decimal("0.30"),
    )
    db.add(r)
    await db.flush()
    return r


@pytest_asyncio.fixture
async def saldo_pa(db: AsyncSession, tenant_id, receita):
    """Pré-popula o saldo PA com 10 unidades disponíveis."""
    saldo = EstoqueProdutoAcabado(
        tenant_id=tenant_id,
        receita_id=receita.id,
        qtd_disponivel=Decimal("10"),
        qtd_minima=Decimal("0"),
    )
    db.add(saldo)
    await db.flush()
    return saldo


@pytest_asyncio.fixture
async def service(db: AsyncSession) -> PedidosService:
    return PedidosService(
        PedidosRepository(db),
        EstoquePAService(EstoquePARepository(db)),
    )


@pytest.mark.asyncio
async def test_entregar_pedido_debita_estoque_pa(
    db: AsyncSession, service: PedidosService, tenant_id, receita, saldo_pa
):
    cliente = await service.criar_cliente(
        tenant_id, CriarClienteRequest(nome="Maria")
    )
    pedido = await service.criar_pedido(
        tenant_id,
        CriarPedidoRequest(
            cliente_id=cliente.id,
            itens=[
                PedidoItemRequest(
                    receita_id=receita.id,
                    quantidade=Decimal("3"),
                    preco_unitario=Decimal("15"),
                )
            ],
        ),
    )

    await service.mudar_status(pedido.id, tenant_id, "aprovado")
    await service.mudar_status(pedido.id, tenant_id, "entregue")

    await db.refresh(saldo_pa)
    # 10 - 3 = 7
    assert saldo_pa.qtd_disponivel == Decimal("7")


@pytest.mark.asyncio
async def test_entregar_sem_saldo_pa_bloqueia(
    db: AsyncSession, service: PedidosService, tenant_id, receita, saldo_pa
):
    cliente = await service.criar_cliente(
        tenant_id, CriarClienteRequest(nome="João")
    )
    # Pedido de 15 un, mas só tem 10 em estoque PA.
    pedido = await service.criar_pedido(
        tenant_id,
        CriarPedidoRequest(
            cliente_id=cliente.id,
            itens=[
                PedidoItemRequest(
                    receita_id=receita.id,
                    quantidade=Decimal("15"),
                    preco_unitario=Decimal("15"),
                )
            ],
        ),
    )
    await service.mudar_status(pedido.id, tenant_id, "aprovado")

    with pytest.raises(EstoquePAInsuficienteError):
        await service.mudar_status(pedido.id, tenant_id, "entregue")

    # Saldo PA permanece intocado (validação atomica antes de debitar).
    await db.refresh(saldo_pa)
    assert saldo_pa.qtd_disponivel == Decimal("10")


@pytest.mark.asyncio
async def test_cancelar_pedido_aprovado_nao_mexe_em_estoque(
    db: AsyncSession, service: PedidosService, tenant_id, receita, saldo_pa
):
    cliente = await service.criar_cliente(
        tenant_id, CriarClienteRequest(nome="Ana")
    )
    pedido = await service.criar_pedido(
        tenant_id,
        CriarPedidoRequest(
            cliente_id=cliente.id,
            itens=[
                PedidoItemRequest(
                    receita_id=receita.id,
                    quantidade=Decimal("4"),
                    preco_unitario=Decimal("15"),
                )
            ],
        ),
    )
    await service.mudar_status(pedido.id, tenant_id, "aprovado")
    await service.mudar_status(pedido.id, tenant_id, "cancelado")

    await db.refresh(saldo_pa)
    # Pedido cancelado nem chegou a debitar (só debita no entregue).
    assert saldo_pa.qtd_disponivel == Decimal("10")


@pytest.mark.asyncio
async def test_pedido_com_receita_inexistente_falha(
    db: AsyncSession, service: PedidosService, tenant_id
):
    with pytest.raises(ValidationError):
        await service.criar_pedido(
            tenant_id,
            CriarPedidoRequest(
                itens=[
                    PedidoItemRequest(
                        receita_id=uuid4(),
                        quantidade=Decimal("1"),
                        preco_unitario=Decimal("10"),
                    )
                ],
            ),
        )


@pytest.mark.asyncio
async def test_isolamento_de_tenant(
    db: AsyncSession, service: PedidosService, tenant_id
):
    outro_tenant = uuid4()
    cliente = await service.criar_cliente(
        tenant_id, CriarClienteRequest(nome="Carla")
    )
    encontrados = await service.listar_clientes(tenant_id)
    assert any(c.id == cliente.id for c in encontrados)
    do_outro = await service.listar_clientes(outro_tenant)
    assert not any(c.id == cliente.id for c in do_outro)
