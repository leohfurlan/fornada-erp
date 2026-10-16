"""Testes do EstoqueService — operações da Sprint 2: editar, deletar, histórico."""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from domain.estoque.repository import EstoqueRepository
from domain.estoque.schemas import (
    AjusteEstoqueRequest,
    AtualizarIngredienteRequest,
    CriarIngredienteRequest,
    EntradaEstoqueRequest,
)
from domain.estoque.service import EstoqueService
from domain.exceptions import ConflictError, NotFoundError, ValidationError
from infrastructure.database.models import (
    Ingrediente,
    Receita,
    ReceitaIngrediente,
    Tenant,
)


@pytest_asyncio.fixture
async def tenant_id(db: AsyncSession):
    tenant = Tenant(nome="Padaria")
    db.add(tenant)
    await db.flush()
    return tenant.id


@pytest_asyncio.fixture
async def service(db: AsyncSession) -> EstoqueService:
    return EstoqueService(EstoqueRepository(db))


@pytest.mark.asyncio
async def test_criar_e_buscar(service: EstoqueService, tenant_id):
    novo = await service.criar_ingrediente(
        tenant_id,
        CriarIngredienteRequest(
            nome="Açúcar",
            tipo="ingrediente",
            unidade="kg",
            estoque_minimo=Decimal("1"),
            estoque_inicial=Decimal("5"),
            custo_inicial=Decimal("3"),
        ),
    )
    encontrado = await service.buscar(novo.id, tenant_id)
    assert encontrado.nome == "Açúcar"
    assert encontrado.custo_medio == Decimal("3.0000")


@pytest.mark.asyncio
async def test_atualizar_campos_descritivos(
    db: AsyncSession, service: EstoqueService, tenant_id
):
    ing = await service.criar_ingrediente(
        tenant_id,
        CriarIngredienteRequest(nome="Sal", unidade="kg"),
    )
    atualizado = await service.atualizar_ingrediente(
        ing.id,
        tenant_id,
        AtualizarIngredienteRequest(nome="Sal grosso", estoque_minimo=Decimal("0.5")),
    )
    assert atualizado.nome == "Sal grosso"
    assert atualizado.estoque_minimo == Decimal("0.5000")
    # Tipo e unidade permanecem
    assert atualizado.unidade == "kg"


@pytest.mark.asyncio
async def test_atualizar_inexistente_404(service: EstoqueService, tenant_id):
    with pytest.raises(NotFoundError):
        await service.atualizar_ingrediente(
            uuid4(),
            tenant_id,
            AtualizarIngredienteRequest(nome="X"),
        )


@pytest.mark.asyncio
async def test_deletar_ingrediente_sem_uso(
    service: EstoqueService, tenant_id
):
    ing = await service.criar_ingrediente(
        tenant_id, CriarIngredienteRequest(nome="Fermento", unidade="g")
    )
    await service.deletar_ingrediente(ing.id, tenant_id)
    with pytest.raises(NotFoundError):
        await service.buscar(ing.id, tenant_id)


@pytest.mark.asyncio
async def test_deletar_ingrediente_em_uso_bloqueado(
    db: AsyncSession, service: EstoqueService, tenant_id
):
    ing = await service.criar_ingrediente(
        tenant_id, CriarIngredienteRequest(nome="Cacau", unidade="kg")
    )
    # Cria receita que referencia esse ingrediente.
    receita = Receita(
        tenant_id=tenant_id,
        nome="Brigadeiro",
        categoria="Doce",
        rendimento=Decimal("10"),
        rendimento_unidade="unidade",
        margem_desejada=Decimal("0.3"),
    )
    db.add(receita)
    await db.flush()
    db.add(
        ReceitaIngrediente(
            receita_id=receita.id,
            ingrediente_id=ing.id,
            quantidade=Decimal("0.5"),
            unidade="kg",
        )
    )
    await db.flush()

    with pytest.raises(ConflictError):
        await service.deletar_ingrediente(ing.id, tenant_id)


@pytest.mark.asyncio
async def test_listar_movimentacoes_com_cadastro_inicial_e_entrada(
    service: EstoqueService, tenant_id
):
    ing = await service.criar_ingrediente(
        tenant_id,
        CriarIngredienteRequest(
            nome="Manteiga",
            unidade="kg",
            estoque_inicial=Decimal("2"),
            custo_inicial=Decimal("20"),
        ),
    )
    await service.registrar_entrada(
        tenant_id,
        EntradaEstoqueRequest(
            ingrediente_id=ing.id,
            quantidade=Decimal("3"),
            custo_unitario=Decimal("22"),
            origem="compra",
        ),
    )
    movs = await service.listar_movimentacoes(ing.id, tenant_id)
    # Deve haver 2 movimentações (cadastro inicial + compra). A ordem por
    # created_at pode ser ambígua quando timestamps coincidem; aqui só
    # validamos a presença de ambas.
    assert len(movs) == 2
    origens = {m.origem for m in movs}
    assert origens == {"cadastro_inicial", "compra"}


@pytest.mark.asyncio
async def test_entrada_recalcula_custo_medio(service: EstoqueService, tenant_id):
    ing = await service.criar_ingrediente(
        tenant_id,
        CriarIngredienteRequest(
            nome="Leite",
            unidade="L",
            estoque_inicial=Decimal("2"),
            custo_inicial=Decimal("5"),  # 2L × R$5
        ),
    )
    # Entrada: 2L × R$7 → média ponderada = (2×5 + 2×7) / 4 = 6
    atualizado = await service.registrar_entrada(
        tenant_id,
        EntradaEstoqueRequest(
            ingrediente_id=ing.id,
            quantidade=Decimal("2"),
            custo_unitario=Decimal("7"),
        ),
    )
    assert atualizado.estoque_atual == Decimal("4.0000")
    assert atualizado.custo_medio == Decimal("6.0000")


@pytest.mark.asyncio
async def test_ajustar_saldo_registra_diferenca_assinada_sem_mudar_custo_medio(
    service: EstoqueService, tenant_id
):
    ingrediente = await service.criar_ingrediente(
        tenant_id,
        CriarIngredienteRequest(
            nome="Farinha",
            unidade="kg",
            estoque_inicial=Decimal("5"),
            custo_inicial=Decimal("8.50"),
        ),
    )

    atualizado = await service.ajustar_saldo(
        ingrediente.id,
        tenant_id,
        AjusteEstoqueRequest(quantidade_alvo=Decimal("3.2500")),
    )
    movimentacoes = await service.listar_movimentacoes(ingrediente.id, tenant_id)

    assert atualizado.estoque_atual == Decimal("3.2500")
    assert atualizado.custo_medio == Decimal("8.5000")
    ajuste = next(mov for mov in movimentacoes if mov.tipo == "ajuste")
    assert ajuste.quantidade == Decimal("-1.7500")
    assert ajuste.custo_unitario == Decimal("8.5000")
    assert ajuste.origem == "ajuste"


@pytest.mark.asyncio
async def test_ajuste_nao_permite_estoque_abaixo_do_reservado(
    db: AsyncSession, service: EstoqueService, tenant_id
):
    ingrediente = await service.criar_ingrediente(
        tenant_id,
        CriarIngredienteRequest(nome="Chocolate", unidade="kg", estoque_inicial=Decimal("4")),
    )
    registro = await db.get(Ingrediente, ingrediente.id)
    assert registro is not None
    registro.quantidade_reservada = Decimal("2")
    await db.flush()

    with pytest.raises(ConflictError, match="abaixo da quantidade reservada"):
        await service.ajustar_saldo(
            ingrediente.id,
            tenant_id,
            AjusteEstoqueRequest(quantidade_alvo=Decimal("1.5")),
        )

    assert (await service.buscar(ingrediente.id, tenant_id)).estoque_atual == Decimal("4")


@pytest.mark.asyncio
async def test_ajuste_igual_ao_saldo_atual_nao_cria_movimentacao(
    service: EstoqueService, tenant_id
):
    ingrediente = await service.criar_ingrediente(
        tenant_id,
        CriarIngredienteRequest(nome="Açúcar", unidade="kg", estoque_inicial=Decimal("2")),
    )

    with pytest.raises(ValidationError, match="corresponde ao estoque atual"):
        await service.ajustar_saldo(
            ingrediente.id,
            tenant_id,
            AjusteEstoqueRequest(quantidade_alvo=Decimal("2")),
        )

    movimentacoes = await service.listar_movimentacoes(ingrediente.id, tenant_id)
    assert not [mov for mov in movimentacoes if mov.tipo == "ajuste"]


@pytest.mark.asyncio
async def test_isolamento_tenant_no_listar(
    service: EstoqueService, tenant_id
):
    await service.criar_ingrediente(
        tenant_id, CriarIngredienteRequest(nome="Banana", unidade="kg")
    )
    # Outro tenant não vê
    outro = uuid4()
    do_outro = await service.listar(outro)
    assert do_outro == []
