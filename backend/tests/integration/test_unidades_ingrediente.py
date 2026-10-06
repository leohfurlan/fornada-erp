from decimal import Decimal
import pytest
from domain.exceptions import ConflictError, ValidationError
from domain.estoque.repository import EstoqueRepository
from domain.estoque.service import EstoqueService
from domain.estoque.schemas import CriarIngredienteRequest, EntradaEstoqueRequest, AtualizarIngredienteRequest
from domain.receitas.repository import ReceitaRepository
from domain.receitas.service import ReceitaService
from domain.receitas.schemas import CriarReceitaRequest
from domain.producao.ficha import montar_snapshot
from infrastructure.database.models import Tenant


@pytest.mark.asyncio
async def test_entrada_custo_receita_snapshot_e_conversao_em_uso(db):
    tenant = Tenant(nome="Unidades")
    db.add(tenant)
    await db.flush()
    service = EstoqueService(EstoqueRepository(db))
    ing = await service.criar_ingrediente(tenant.id, CriarIngredienteRequest(nome="Farinha", unidade="g", unidades_alternativas=[dict(unidade="xícara", fator="120")]))
    entrada = await service.registrar_entrada(tenant.id, EntradaEstoqueRequest(ingrediente_id=ing.id, quantidade="1", unidade="kg", custo_unitario="10"))
    assert entrada.estoque_atual == Decimal("1000")
    assert entrada.custo_medio == Decimal("0.01")
    repo = ReceitaRepository(db)
    receita = await ReceitaService(repo, db).criar(tenant.id, CriarReceitaRequest(nome="Massa", categoria="Bolos", rendimento="1", rendimento_unidade="un", ingredientes=[dict(ingrediente_id=ing.id, quantidade="1.5", unidade="xícara")], etapas=[]))
    assert receita.custo.custo_ingredientes == Decimal("1.80")
    snapshot = await montar_snapshot(await repo.buscar_por_id(receita.id, tenant.id), repo, tenant.id)
    assert Decimal(snapshot["materiais"][str(ing.id)]) == Decimal("180")
    with pytest.raises(ValidationError):
        await service.atualizar_ingrediente(ing.id, tenant.id, AtualizarIngredienteRequest(unidades_alternativas=[]))
    with pytest.raises(ConflictError):
        await service.atualizar_ingrediente(ing.id, tenant.id, AtualizarIngredienteRequest(unidade="kg"))


@pytest.mark.asyncio
async def test_nao_redefine_equivalencia_metrica(db):
    tenant = Tenant(nome="Métrica")
    db.add(tenant)
    await db.flush()
    with pytest.raises(ConflictError):
        await EstoqueService(EstoqueRepository(db)).criar_ingrediente(tenant.id, CriarIngredienteRequest(nome="Farinha", unidade="g", unidades_alternativas=[dict(unidade="kg", fator="500")]))
