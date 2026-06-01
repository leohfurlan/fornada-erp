"""Testes de integração do fluxo de Ordem de Produção (Sprint 3).

Cobre o caminho crítico do PCP:
  - Planejada → Em Produção (reserva ingredientes)
  - Em Produção → Finalizada com qtd_produzida ≠ planejada (debita ingredientes pelo planejado, gera estoque PA pelo produzido)
  - Cancelamento em produção estorna reserva
  - Estoque insuficiente bloqueia início
  - Perda total (qtd_produzida=0) não gera estoque PA
"""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from domain.estoque.repository import EstoqueRepository
from domain.estoque_pa.repository import EstoquePARepository
from domain.estoque_pa.service import EstoquePAService
from domain.exceptions import EstoqueInsuficienteError, ValidationError
from domain.producao.repository import ProducaoRepository
from domain.producao.schemas import CriarOrdemProducaoRequest
from domain.producao.service import ProducaoService
from infrastructure.database.models import (
    EstoqueProdutoAcabado,
    Ingrediente,
    Receita,
    ReceitaIngrediente,
    Tenant,
)


@pytest_asyncio.fixture
async def tenant_id(db: AsyncSession):
    tenant = Tenant(nome="Padaria PCP")
    db.add(tenant)
    await db.flush()
    return tenant.id


@pytest_asyncio.fixture
async def farinha(db: AsyncSession, tenant_id):
    ing = Ingrediente(
        tenant_id=tenant_id,
        codigo=1,
        tipo="ingrediente",
        nome="Farinha",
        unidade="kg",
        estoque_atual=Decimal("10"),
        quantidade_reservada=Decimal("0"),
        estoque_minimo=Decimal("1"),
        custo_medio=Decimal("5"),
    )
    db.add(ing)
    await db.flush()
    return ing


@pytest_asyncio.fixture
async def receita(db: AsyncSession, tenant_id, farinha):
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
    db.add(
        ReceitaIngrediente(
            receita_id=r.id,
            ingrediente_id=farinha.id,
            quantidade=Decimal("0.2"),  # 200g por brownie
            unidade="kg",
        )
    )
    await db.flush()
    return r


@pytest_asyncio.fixture
async def service(db: AsyncSession) -> ProducaoService:
    return ProducaoService(
        ProducaoRepository(db),
        EstoqueRepository(db),
        EstoquePAService(EstoquePARepository(db)),
    )


@pytest.mark.asyncio
async def test_iniciar_producao_reserva_ingredientes(
    db: AsyncSession, service: ProducaoService, tenant_id, receita, farinha
):
    op = await service.criar(
        tenant_id,
        CriarOrdemProducaoRequest(receita_id=receita.id, qtd_planejada=Decimal("10")),
    )
    await service.mudar_status(op.id, tenant_id, "em_producao")

    await db.refresh(farinha)
    # 10 brownies × 0.2 kg = 2 kg reservados.
    assert farinha.estoque_atual == Decimal("10")
    assert farinha.quantidade_reservada == Decimal("2.0000")


@pytest.mark.asyncio
async def test_finalizar_com_qtd_produzida_diferente(
    db: AsyncSession, service: ProducaoService, tenant_id, receita, farinha
):
    """Cenário chave: planejei 10, saíram 8 (queimou 2).

    Ingredientes baixam pelo PLANEJADO (consumi 2kg); estoque PA recebe o REAL (8).
    """
    op = await service.criar(
        tenant_id,
        CriarOrdemProducaoRequest(receita_id=receita.id, qtd_planejada=Decimal("10")),
    )
    await service.mudar_status(op.id, tenant_id, "em_producao")
    await service.mudar_status(op.id, tenant_id, "finalizada", qtd_produzida=Decimal("8"))

    await db.refresh(farinha)
    # Ingredientes: consumiu 2kg do planejado.
    assert farinha.estoque_atual == Decimal("8.0000")
    assert farinha.quantidade_reservada == Decimal("0")

    # Estoque PA recebeu 8 unidades reais.
    from sqlalchemy import select
    result = await db.execute(
        select(EstoqueProdutoAcabado).where(
            EstoqueProdutoAcabado.receita_id == receita.id
        )
    )
    saldo_pa = result.scalar_one()
    assert saldo_pa.qtd_disponivel == Decimal("8.000")


@pytest.mark.asyncio
async def test_perda_total_qtd_produzida_zero(
    db: AsyncSession, service: ProducaoService, tenant_id, receita, farinha
):
    """qtd_produzida=0 (queimou tudo): ingredientes saem, estoque PA não cresce."""
    op = await service.criar(
        tenant_id,
        CriarOrdemProducaoRequest(receita_id=receita.id, qtd_planejada=Decimal("5")),
    )
    await service.mudar_status(op.id, tenant_id, "em_producao")
    await service.mudar_status(op.id, tenant_id, "finalizada", qtd_produzida=Decimal("0"))

    await db.refresh(farinha)
    # 5 × 0.2 = 1 kg consumido.
    assert farinha.estoque_atual == Decimal("9.0000")

    from sqlalchemy import select
    result = await db.execute(
        select(EstoqueProdutoAcabado).where(
            EstoqueProdutoAcabado.receita_id == receita.id
        )
    )
    # Estoque PA pode não ter sido criado se nada entrou; aceita None.
    saldo_pa = result.scalar_one_or_none()
    assert saldo_pa is None or saldo_pa.qtd_disponivel == Decimal("0")


@pytest.mark.asyncio
async def test_cancelar_em_producao_estorna_reserva(
    db: AsyncSession, service: ProducaoService, tenant_id, receita, farinha
):
    op = await service.criar(
        tenant_id,
        CriarOrdemProducaoRequest(receita_id=receita.id, qtd_planejada=Decimal("10")),
    )
    await service.mudar_status(op.id, tenant_id, "em_producao")
    await db.refresh(farinha)
    assert farinha.quantidade_reservada == Decimal("2.0000")

    await service.mudar_status(op.id, tenant_id, "cancelada")
    await db.refresh(farinha)
    assert farinha.estoque_atual == Decimal("10")
    assert farinha.quantidade_reservada == Decimal("0")


@pytest.mark.asyncio
async def test_iniciar_sem_estoque_suficiente_falha(
    db: AsyncSession, service: ProducaoService, tenant_id, receita, farinha
):
    # 60 brownies × 0.2 kg = 12 kg, mas só tem 10 kg.
    op = await service.criar(
        tenant_id,
        CriarOrdemProducaoRequest(receita_id=receita.id, qtd_planejada=Decimal("60")),
    )
    with pytest.raises(EstoqueInsuficienteError):
        await service.mudar_status(op.id, tenant_id, "em_producao")

    # Nada reservado (validação atomica).
    await db.refresh(farinha)
    assert farinha.quantidade_reservada == Decimal("0")


@pytest.mark.asyncio
async def test_finalizar_sem_qtd_produzida_falha(
    db: AsyncSession, service: ProducaoService, tenant_id, receita
):
    op = await service.criar(
        tenant_id,
        CriarOrdemProducaoRequest(receita_id=receita.id, qtd_planejada=Decimal("10")),
    )
    await service.mudar_status(op.id, tenant_id, "em_producao")
    with pytest.raises(ValidationError):
        await service.mudar_status(op.id, tenant_id, "finalizada")
