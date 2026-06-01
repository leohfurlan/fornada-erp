"""Testes de integração do fluxo da Agenda de Produção.

Cobrem o ciclo de vida de itens (criar → listar → mover → concluir → deletar),
join com nome do cliente em itens de pedido, isolamento entre tenants e
período sem itens (lista vazia, não erro).
"""

from datetime import date, time
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from domain.agenda.repository import AgendaRepository
from domain.agenda.schemas import (
    AtualizarAgendaItemRequest,
    CriarAgendaItemRequest,
    MoverAgendaItemRequest,
)
from domain.agenda.service import AgendaService
from domain.exceptions import NotFoundError, ValidationError
from infrastructure.database.models import Cliente, Pedido, Receita, Tenant


@pytest_asyncio.fixture
async def tenant_id(db: AsyncSession):
    tenant = Tenant(nome="Agenda Tenant A")
    db.add(tenant)
    await db.flush()
    return tenant.id


@pytest_asyncio.fixture
async def outro_tenant_id(db: AsyncSession):
    tenant = Tenant(nome="Agenda Tenant B")
    db.add(tenant)
    await db.flush()
    return tenant.id


@pytest_asyncio.fixture
async def receita(db: AsyncSession, tenant_id):
    r = Receita(
        tenant_id=tenant_id,
        nome="Bolo de Cenoura",
        categoria="Doce",
        rendimento=Decimal("1"),
        rendimento_unidade="unidade",
        margem_desejada=Decimal("0.30"),
    )
    db.add(r)
    await db.flush()
    return r


@pytest_asyncio.fixture
async def pedido(db: AsyncSession, tenant_id):
    cliente = Cliente(tenant_id=tenant_id, nome="Dona Maria")
    db.add(cliente)
    await db.flush()
    p = Pedido(
        tenant_id=tenant_id,
        numero=1,
        cliente_id=cliente.id,
        status="aprovado",
        data_entrega=date(2026, 6, 5),
        valor_total=Decimal("100"),
    )
    db.add(p)
    await db.flush()
    return p


@pytest_asyncio.fixture
async def service(db: AsyncSession) -> AgendaService:
    return AgendaService(AgendaRepository(db))


@pytest.mark.asyncio
async def test_ciclo_de_vida_item_receita(
    db: AsyncSession, service: AgendaService, tenant_id, receita
):
    # Criar item vinculado a receita.
    criado = await service.criar_item(
        tenant_id,
        CriarAgendaItemRequest(
            titulo="Produzir bolo",
            tipo="receita",
            data=date(2026, 6, 3),  # quarta
            hora_inicio=time(8, 0),
            hora_fim=time(10, 0),
            receita_id=receita.id,
        ),
    )
    assert criado.nome_receita == "Bolo de Cenoura"
    assert criado.duracao_minutos == 120
    assert criado.concluido is False

    # Listar pela semana (segunda 01 a domingo 07).
    semana = await service.listar_semana(tenant_id, date(2026, 6, 1))
    assert len(semana) == 1
    assert semana[0].id == criado.id

    # Mover para outra data e horário.
    movido = await service.mover_item(
        tenant_id,
        criado.id,
        MoverAgendaItemRequest(
            data=date(2026, 6, 10), hora_inicio=time(14, 0), hora_fim=time(15, 0)
        ),
    )
    assert movido.data == date(2026, 6, 10)
    assert movido.hora_inicio == time(14, 0)
    assert movido.duracao_minutos == 60
    # Saiu da semana anterior.
    assert await service.listar_semana(tenant_id, date(2026, 6, 1)) == []

    # Marcar concluído.
    concluido = await service.marcar_concluido(tenant_id, criado.id, True)
    assert concluido.concluido is True

    # Deletar (soft).
    await service.deletar_item(tenant_id, criado.id)
    assert await service.listar_dia(tenant_id, date(2026, 6, 10)) == []


@pytest.mark.asyncio
async def test_pedido_concluido_some_da_fila(
    db: AsyncSession, service: AgendaService, tenant_id, pedido
):
    """Item vinculado a pedido entregue/concluído não aparece na listagem."""
    criado = await service.criar_item(
        tenant_id,
        CriarAgendaItemRequest(
            titulo="Preparar encomenda",
            tipo="pedido",
            data=date(2026, 6, 4),
            pedido_id=pedido.id,
        ),
    )
    # Enquanto o pedido está aprovado, aparece.
    semana = await service.listar_semana(tenant_id, date(2026, 6, 1))
    assert [i.id for i in semana] == [criado.id]

    # Pedido entregue → item sai da fila.
    pedido.status = "entregue"
    await db.flush()
    assert await service.listar_semana(tenant_id, date(2026, 6, 1)) == []

    # Status legado "finalizado" também esconde.
    pedido.status = "finalizado"
    await db.flush()
    assert await service.listar_dia(tenant_id, date(2026, 6, 4)) == []

    # Mas tarefas sem vínculo de pedido continuam visíveis no mesmo período.
    tarefa = await service.criar_item(
        tenant_id,
        CriarAgendaItemRequest(titulo="Lavar formas", tipo="tarefa", data=date(2026, 6, 4)),
    )
    restantes = await service.listar_dia(tenant_id, date(2026, 6, 4))
    assert [i.id for i in restantes] == [tarefa.id]


@pytest.mark.asyncio
async def test_pedido_cancelado_permanece_na_fila(
    db: AsyncSession, service: AgendaService, tenant_id, pedido
):
    """Cancelado ≠ concluído: o item segue visível (não foi entregue)."""
    criado = await service.criar_item(
        tenant_id,
        CriarAgendaItemRequest(
            titulo="Encomenda", tipo="pedido", data=date(2026, 6, 4), pedido_id=pedido.id
        ),
    )
    pedido.status = "cancelado"
    await db.flush()
    semana = await service.listar_semana(tenant_id, date(2026, 6, 1))
    assert [i.id for i in semana] == [criado.id]


@pytest.mark.asyncio
async def test_item_pedido_traz_nome_cliente(
    db: AsyncSession, service: AgendaService, tenant_id, pedido
):
    criado = await service.criar_item(
        tenant_id,
        CriarAgendaItemRequest(
            titulo="Preparar encomenda",
            tipo="pedido",
            data=date(2026, 6, 4),
            pedido_id=pedido.id,
        ),
    )
    assert criado.nome_pedido == "Pedido #1 - Dona Maria"


@pytest.mark.asyncio
async def test_listar_mes_inclui_todo_o_mes(
    db: AsyncSession, service: AgendaService, tenant_id, receita
):
    for dia in (1, 15, 30):
        await service.criar_item(
            tenant_id,
            CriarAgendaItemRequest(titulo=f"Tarefa {dia}", tipo="tarefa", data=date(2026, 6, dia)),
        )
    itens = await service.listar_mes(tenant_id, 2026, 6)
    assert len(itens) == 3
    # Ordenados por data ascendente.
    assert [i.data.day for i in itens] == [1, 15, 30]


@pytest.mark.asyncio
async def test_periodo_sem_itens_retorna_lista_vazia(
    db: AsyncSession, service: AgendaService, tenant_id
):
    assert await service.listar_semana(tenant_id, date(2026, 1, 1)) == []
    assert await service.listar_dia(tenant_id, date(2026, 1, 1)) == []
    assert await service.listar_mes(tenant_id, 2026, 1) == []


@pytest.mark.asyncio
async def test_isolamento_de_tenant(
    db: AsyncSession,
    service: AgendaService,
    tenant_id,
    outro_tenant_id,
):
    criado = await service.criar_item(
        tenant_id,
        CriarAgendaItemRequest(titulo="Só do tenant A", tipo="tarefa", data=date(2026, 6, 3)),
    )
    # Tenant B não enxerga o item do tenant A.
    assert await service.listar_semana(outro_tenant_id, date(2026, 6, 1)) == []
    # Nem consegue buscá-lo / movê-lo / deletá-lo.
    with pytest.raises(NotFoundError):
        await service.mover_item(
            outro_tenant_id, criado.id, MoverAgendaItemRequest(data=date(2026, 6, 4))
        )
    with pytest.raises(NotFoundError):
        await service.deletar_item(outro_tenant_id, criado.id)


@pytest.mark.asyncio
async def test_criar_receita_de_outro_tenant_falha(
    db: AsyncSession,
    service: AgendaService,
    outro_tenant_id,
    receita,
):
    # receita pertence a tenant_id (A); tenant B não pode vinculá-la.
    with pytest.raises(ValidationError):
        await service.criar_item(
            outro_tenant_id,
            CriarAgendaItemRequest(
                titulo="Bolo alheio",
                tipo="receita",
                data=date(2026, 6, 3),
                receita_id=receita.id,
            ),
        )


@pytest.mark.asyncio
async def test_atualizar_campos_simples(db: AsyncSession, service: AgendaService, tenant_id):
    criado = await service.criar_item(
        tenant_id,
        CriarAgendaItemRequest(
            titulo="Mercado", tipo="tarefa", data=date(2026, 6, 3), cor="#64748b"
        ),
    )
    atualizado = await service.atualizar_item(
        tenant_id,
        criado.id,
        AtualizarAgendaItemRequest(titulo="Mercado + Feira", cor="#16a34a"),
    )
    assert atualizado.titulo == "Mercado + Feira"
    assert atualizado.cor == "#16a34a"
    assert atualizado.tipo == "tarefa"  # inalterado
