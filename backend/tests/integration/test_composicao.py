from decimal import Decimal
from uuid import uuid4

import pytest

from domain.estoque.repository import EstoqueRepository
from domain.estoque_pa.repository import EstoquePARepository
from domain.estoque_pa.service import EstoquePAService
from domain.exceptions import ConflictError, ValidationError, EstoquePAInsuficienteError
from domain.producao.repository import ProducaoRepository
from domain.producao.service import ProducaoService
from domain.producao.schemas import CriarOrdemProducaoRequest
from domain.receitas.repository import ReceitaRepository
from domain.receitas.service import ReceitaService
from domain.receitas.ficha_service import FichaTecnicaService
from domain.receitas.ficha_tecnica import FichaTecnicaInput
from infrastructure.database.models import Tenant, Receita, Ingrediente, ReceitaIngrediente


async def preparar(db):
    tenant = Tenant(nome="Composição")
    db.add(tenant)
    await db.flush()
    materia = Ingrediente(tenant_id=tenant.id, codigo=1, nome="Leite", tipo="ingrediente", unidade="kg", custo_medio=Decimal("10"), estoque_atual=Decimal("10"))
    copo = Ingrediente(tenant_id=tenant.id, codigo=2, nome="Copo", tipo="embalagem", unidade="un", custo_medio=Decimal("1"), estoque_atual=Decimal("10"))
    base = Receita(tenant_id=tenant.id, nome="Brigadeiro", categoria="Base", rendimento=Decimal("1000"), rendimento_unidade="g", margem_desejada=Decimal("0.3"))
    produto = Receita(tenant_id=tenant.id, nome="Sedução", categoria="Produto", rendimento=Decimal("1"), rendimento_unidade="un", margem_desejada=Decimal("0.3"))
    db.add_all([materia, copo, base, produto])
    await db.flush()
    db.add(ReceitaIngrediente(receita_id=base.id, ingrediente_id=materia.id, quantidade=Decimal("1"), unidade="kg"))
    await db.flush()
    ficha = FichaTecnicaInput(descricao_produto="Sedução", revisao=0, composicao_ativa=True, passos=[
        dict(descricao="Copo", tipo="embalagem", quantidade="1", unidade="un", ingrediente_id=copo.id),
        dict(descricao="Brigadeiro", tipo="componente", quantidade="30", unidade="g", receita_base_id=base.id),
        dict(descricao="Brigadeiro", tipo="componente", quantidade="0.030", unidade="kg", receita_base_id=base.id),
    ])
    await FichaTecnicaService(db).salvar(produto.id, tenant.id, ficha)
    return tenant, materia, copo, base, produto, ficha


@pytest.mark.asyncio
async def test_custo_reserva_snapshot_e_consumo_sem_dupla_baixa(db):
    tenant, materia, copo, base, produto, ficha = await preparar(db)
    receitas = ReceitaService(ReceitaRepository(db), db)
    resposta = await receitas.buscar(produto.id, tenant.id)
    assert resposta.custo.custo_ingredientes == Decimal("0.60")
    assert resposta.custo.custo_embalagem == Decimal("1.00")
    assert resposta.custo.custo_total == Decimal("1.60")
    # Unidade diferente no ingrediente da base não multiplica custo por mil.
    from domain.receitas.schemas import AtualizarReceitaRequest, IngredienteInput
    await receitas.atualizar(base.id, tenant.id, AtualizarReceitaRequest(ingredientes=[IngredienteInput(ingrediente_id=materia.id, quantidade="1000", unidade="g")]))
    assert (await receitas.buscar(produto.id, tenant.id)).custo.custo_total == Decimal("1.60")
    pa = EstoquePAService(EstoquePARepository(db))
    await pa.incrementar(base.id, tenant.id, Decimal("1000"), "teste")
    producao = ProducaoService(ProducaoRepository(db), EstoqueRepository(db), pa)
    op = await producao.criar(tenant.id, CriarOrdemProducaoRequest(receita_id=produto.id, qtd_planejada="2"))
    assert Decimal(op.ficha_snapshot["bases"][str(base.id)]) == Decimal("60")
    # Mudança posterior não muda o consumo congelado desta produção.
    alterada = ficha.model_copy(deep=True)
    alterada.revisao = 1
    alterada.passos[1].quantidade = Decimal("100")
    await FichaTecnicaService(db).salvar(produto.id, tenant.id, alterada)
    await producao.mudar_status(op.id, tenant.id, "em_producao")
    saldo = await pa.buscar_saldo(base.id, tenant.id)
    assert saldo.qtd_disponivel == Decimal("880")
    assert saldo.qtd_reservada == Decimal("120")
    with pytest.raises(EstoquePAInsuficienteError):
        await pa.debitar(base.id, tenant.id, Decimal("900"), "venda")
    await producao.mudar_status(op.id, tenant.id, "finalizada", Decimal("2"))
    assert (await pa.buscar_saldo(base.id, tenant.id)).qtd_disponivel == Decimal("880")
    assert (await pa.buscar_saldo(base.id, tenant.id)).qtd_reservada == 0
    assert (await pa.buscar_saldo(produto.id, tenant.id)).qtd_disponivel == 2
    assert materia.estoque_atual == Decimal("10")
    assert copo.estoque_atual == Decimal("8")
    with pytest.raises(ConflictError):
        await receitas.deletar(base.id, tenant.id)
    with pytest.raises(ConflictError):
        await receitas.atualizar(base.id, tenant.id, AtualizarReceitaRequest(rendimento_unidade="kg"))


@pytest.mark.asyncio
async def test_cancelamento_devolve_reservas_dos_componentes(db):
    tenant, _, copo, base, produto, _ = await preparar(db)
    pa = EstoquePAService(EstoquePARepository(db))
    await pa.incrementar(base.id, tenant.id, Decimal("1000"), "teste")
    producao = ProducaoService(ProducaoRepository(db), EstoqueRepository(db), pa)
    op = await producao.criar(tenant.id, CriarOrdemProducaoRequest(receita_id=produto.id, qtd_planejada="1"))
    await producao.mudar_status(op.id, tenant.id, "em_producao")
    await producao.mudar_status(op.id, tenant.id, "cancelada")
    assert (await pa.buscar_saldo(base.id, tenant.id)).qtd_disponivel == 1000
    assert copo.quantidade_reservada == 0


@pytest.mark.asyncio
async def test_custo_inclui_trabalho_da_base_e_montagem_sem_duplo_rateio(db):
    from infrastructure.database.models import ConfiguracaoCusto, ReceitaEtapa, Usuario
    tenant, _, _, base, produto, _ = await preparar(db)
    db.add_all([
        ConfiguracaoCusto(tenant_id=tenant.id, custo_operacional_mensal=Decimal("160"), horas_mensais=Decimal("160")),
        Usuario(tenant_id=tenant.id, nome="QA", email=f"{uuid4().hex}@example.com", senha_hash="fixture", valor_hora=Decimal("60")),
        ReceitaEtapa(receita_id=base.id, nome="Preparar base", duracao_minutos=30, tipo_mao_obra="direta", ordem=0),
        ReceitaEtapa(receita_id=produto.id, nome="Montar copo", duracao_minutos=6, tipo_mao_obra="direta", ordem=0),
    ])
    await db.flush()
    custo = (await ReceitaService(ReceitaRepository(db), db).buscar(produto.id, tenant.id)).custo
    assert custo.custo_ingredientes == Decimal("0.60")
    assert custo.custo_embalagem == Decimal("1.00")
    assert custo.custo_operacional == Decimal("0.13")
    assert custo.custo_mao_obra_direta == Decimal("7.80")
    assert custo.custo_total == Decimal("9.53")


@pytest.mark.asyncio
async def test_rejeita_ciclo_tenant_e_unidades_incompativeis(db):
    tenant, _, _, base, produto, ficha = await preparar(db)
    service = FichaTecnicaService(db)
    for unidade, alvo in [("ml", base.id), ("g", produto.id), ("g", uuid4())]:
        alterada = ficha.model_copy(deep=True)
        alterada.revisao = 1
        alterada.passos[1].unidade = unidade
        alterada.passos[1].receita_base_id = alvo
        with pytest.raises(ValidationError):
            await service.salvar(produto.id, tenant.id, alterada)
