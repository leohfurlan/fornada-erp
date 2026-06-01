"""Testes de integração do fluxo de Vendas (Sprint 3).

Cobre:
  - Criar venda multicanal → debita estoque PA, agrega valor_total
  - Venda sem saldo PA → EstoquePAInsuficienteError (atomic)
  - Múltiplos itens da mesma receita agregam corretamente na validação
  - Cancelar venda → estorna estoque PA
  - Isolamento de tenant
"""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from domain.estoque_pa.repository import EstoquePARepository
from domain.estoque_pa.service import EstoquePAService
from domain.exceptions import EstoquePAInsuficienteError, ValidationError
from domain.vendas.repository import VendasRepository
from domain.vendas.schemas import CriarVendaRequest, VendaItemRequest
from domain.vendas.service import VendasService
from infrastructure.database.models import (
    EstoqueProdutoAcabado,
    Receita,
    Tenant,
)


@pytest_asyncio.fixture
async def tenant_id(db: AsyncSession):
    tenant = Tenant(nome="Padaria Vendas")
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
    saldo = EstoqueProdutoAcabado(
        tenant_id=tenant_id,
        receita_id=receita.id,
        qtd_disponivel=Decimal("20"),
        qtd_minima=Decimal("5"),
    )
    db.add(saldo)
    await db.flush()
    return saldo


@pytest_asyncio.fixture
async def service(db: AsyncSession) -> VendasService:
    return VendasService(
        VendasRepository(db),
        EstoquePAService(EstoquePARepository(db)),
    )


@pytest.mark.asyncio
async def test_criar_venda_whatsapp_debita_estoque_pa(
    db: AsyncSession, service: VendasService, tenant_id, receita, saldo_pa
):
    venda = await service.criar(
        tenant_id,
        CriarVendaRequest(
            canal="whatsapp",
            itens=[
                VendaItemRequest(
                    receita_id=receita.id,
                    quantidade=Decimal("5"),
                    preco_unitario=Decimal("15"),
                )
            ],
        ),
    )
    assert venda.canal == "whatsapp"
    assert venda.cliente_id is None  # cliente opcional
    assert venda.valor_total == Decimal("75.00")  # 5 × 15

    await db.refresh(saldo_pa)
    assert saldo_pa.qtd_disponivel == Decimal("15")


@pytest.mark.asyncio
async def test_venda_sem_saldo_pa_bloqueia_atomicamente(
    db: AsyncSession, service: VendasService, tenant_id, receita, saldo_pa
):
    # Tentar vender 25 brownies, só tem 20.
    with pytest.raises(EstoquePAInsuficienteError):
        await service.criar(
            tenant_id,
            CriarVendaRequest(
                canal="ifood",
                itens=[
                    VendaItemRequest(
                        receita_id=receita.id,
                        quantidade=Decimal("25"),
                        preco_unitario=Decimal("15"),
                    )
                ],
            ),
        )
    # Saldo PA permaneceu intocado (validação pré-criação).
    await db.refresh(saldo_pa)
    assert saldo_pa.qtd_disponivel == Decimal("20")


@pytest.mark.asyncio
async def test_multiplos_itens_mesma_receita_agregam(
    db: AsyncSession, service: VendasService, tenant_id, receita, saldo_pa
):
    """Mesma receita em 2 itens: validação agrega qtd antes de debitar.

    Cenário: 2 itens de 12 brownies cada = 24, mas só tem 20.
    Sem agregação, cada item passaria isolado (12 < 20). Com agregação, falha.
    """
    with pytest.raises(EstoquePAInsuficienteError):
        await service.criar(
            tenant_id,
            CriarVendaRequest(
                canal="loja_fisica",
                itens=[
                    VendaItemRequest(
                        receita_id=receita.id,
                        quantidade=Decimal("12"),
                        preco_unitario=Decimal("15"),
                    ),
                    VendaItemRequest(
                        receita_id=receita.id,
                        quantidade=Decimal("12"),
                        preco_unitario=Decimal("13"),  # preço diferente, ex: desconto
                    ),
                ],
            ),
        )
    await db.refresh(saldo_pa)
    assert saldo_pa.qtd_disponivel == Decimal("20")


@pytest.mark.asyncio
async def test_cancelar_venda_estorna_estoque_pa(
    db: AsyncSession, service: VendasService, tenant_id, receita, saldo_pa
):
    venda = await service.criar(
        tenant_id,
        CriarVendaRequest(
            canal="whatsapp",
            itens=[
                VendaItemRequest(
                    receita_id=receita.id,
                    quantidade=Decimal("7"),
                    preco_unitario=Decimal("15"),
                )
            ],
        ),
    )
    await db.refresh(saldo_pa)
    assert saldo_pa.qtd_disponivel == Decimal("13")

    await service.cancelar(venda.id, tenant_id)
    await db.refresh(saldo_pa)
    # Estornou os 7.
    assert saldo_pa.qtd_disponivel == Decimal("20")


@pytest.mark.asyncio
async def test_venda_com_canal_invalido_falha(
    db: AsyncSession, service: VendasService, tenant_id, receita
):
    # Pydantic field_validator rejeita antes de chegar no service.
    with pytest.raises(Exception):  # ValueError → wraps ValidationError
        await service.criar(
            tenant_id,
            CriarVendaRequest(
                canal="canal_inexistente",
                itens=[
                    VendaItemRequest(
                        receita_id=receita.id,
                        quantidade=Decimal("1"),
                        preco_unitario=Decimal("10"),
                    )
                ],
            ),
        )


@pytest.mark.asyncio
async def test_venda_com_receita_inexistente_falha(
    db: AsyncSession, service: VendasService, tenant_id
):
    with pytest.raises(ValidationError):
        await service.criar(
            tenant_id,
            CriarVendaRequest(
                canal="whatsapp",
                itens=[
                    VendaItemRequest(
                        receita_id=uuid4(),
                        quantidade=Decimal("1"),
                        preco_unitario=Decimal("10"),
                    )
                ],
            ),
        )


@pytest.mark.asyncio
async def test_isolamento_de_tenant(
    db: AsyncSession, service: VendasService, tenant_id, receita, saldo_pa
):
    venda = await service.criar(
        tenant_id,
        CriarVendaRequest(
            canal="whatsapp",
            itens=[
                VendaItemRequest(
                    receita_id=receita.id,
                    quantidade=Decimal("3"),
                    preco_unitario=Decimal("15"),
                )
            ],
        ),
    )
    # Tenant correto vê
    encontrados = await service.listar(tenant_id)
    assert any(v.id == venda.id for v in encontrados)
    # Outro tenant não vê
    do_outro = await service.listar(uuid4())
    assert not any(v.id == venda.id for v in do_outro)
