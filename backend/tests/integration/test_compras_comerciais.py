"""Cenários comerciais com PostgreSQL real e OCR/transportes determinísticos."""

import asyncio
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from core.security import create_access_token
from domain.compras.comercial import ComprasComerciais
from domain.compras.comercial_schemas import (
    CompraRevisada,
    FornecedorCriar,
    ItemObservado,
    ItemRevisado,
    ProdutoCriar,
    ProdutoDados,
    ProdutoEditar,
    VinculoEditar,
)
from domain.compras.reconhecimento import ReconhecimentoCompras
from domain.compras.repository import ComprasRepository
from domain.estoque.repository import EstoqueRepository
from domain.estoque.schemas import CriarIngredienteRequest
from domain.estoque.service import EstoqueService
from domain.exceptions import ConflictError, NotFoundError, ValidationError
from infrastructure.database.compras_models import AliasCompra, Compra
from infrastructure.database.models import Ingrediente, MovimentacaoEstoque, Tenant, Usuario

DESCRIPTION = "COBERTURA EM BARRA DR.OETKER 1,01KG"


async def test_catalogo_aprovacao_por_produto_e_loja_inativada(comercial, db):
    from domain.compras.comercial_schemas import FornecedorEditar

    service, tenant, material, fornecedor, produto = comercial
    segundo = await service.catalogo.criar_produto(
        tenant,
        ProdutoCriar(
            ingrediente_id=material.id,
            nome="Outra barra",
            marca="Outra marca",
            conteudo_embalagem=Decimal("1"),
            unidade_conteudo="kg",
            aprovado=True,
        ),
    )
    assert await service.repo.aprovados(tenant, segundo.id) == []
    assert await service.repo.aprovados(tenant, produto.id) == [fornecedor.id]
    assert (await service.catalogo.listar_produtos(tenant, material.id, True, 1, 1)).total == 2
    assert await count(db, MovimentacaoEstoque, tenant) == 0
    await service.catalogo.editar_fornecedor(
        tenant,
        fornecedor.id,
        FornecedorEditar(revisao=fornecedor.revisao, nome="Loja revisada", cnpj="38533519000108"),
    )
    with pytest.raises(ConflictError):
        await service.catalogo.criar_fornecedor(
            tenant, FornecedorCriar(nome="Duplicada", cnpj="38533519000108")
        )
    with pytest.raises(ConflictError):
        await service.catalogo.editar_fornecedor(
            tenant, fornecedor.id, FornecedorEditar(revisao=1, nome="Edição antiga")
        )
    another = await service.catalogo.criar_fornecedor(tenant, FornecedorCriar(nome="Nova loja"))
    with pytest.raises(ConflictError):
        await service.catalogo.editar_fornecedor(
            tenant, another.id, FornecedorEditar(revisao=another.revisao, cnpj="38533519000108")
        )
    stores = await service.catalogo.listar_fornecedores(tenant, "revisada", 50, 0)
    assert stores.total == 1 and stores.itens[0].nome == "Loja revisada"
    purchase = await service.confirmar(tenant, request(material, fornecedor, produto), uuid4())
    with pytest.raises(ConflictError):
        await service.catalogo.apagar_fornecedor(tenant, fornecedor.id, 1)
    await service.catalogo.apagar_fornecedor(tenant, fornecedor.id, fornecedor.revisao)
    with pytest.raises(NotFoundError):
        await service.repo.fornecedor(tenant, fornecedor.id)
    history = await service.detalhe(tenant, purchase.compra_id)
    assert history.fornecedor_nome_snapshot == "Loja revisada"
    assert (await service.catalogo.listar_fornecedores(tenant, None, 50, 0)).total == 1


async def test_catalogo_conversao_especifica_precisa_confirmacao(comercial):
    service, tenant, material, fornecedor, _ = comercial
    dados = ProdutoCriar(
        ingrediente_id=material.id,
        nome="Pacote especial",
        marca="Marca",
        conteudo_embalagem=Decimal("1"),
        unidade_conteudo="pct",
        aprovado=True,
        fornecedores_aprovados=[fornecedor.id],
    )
    with pytest.raises(ValidationError):
        await service.catalogo.criar_produto(tenant, dados)
    dados.fator_para_principal = Decimal("2")
    product = await service.catalogo.criar_produto(tenant, dados)
    data = request(material, fornecedor, product)
    data.itens[0].descricao_original = "PACOTE ESPECIAL"
    assert (await service.prever(tenant, data)).itens[0].quantidade_principal == Decimal("2")
    dados.unidade_conteudo = "kg"
    with pytest.raises(ValidationError):
        await service.catalogo.criar_produto(tenant, dados)


async def test_codigo_interno_da_loja_e_conflito_com_gtin(comercial):
    service, tenant, material, fornecedor, produto = comercial
    produto = await service.catalogo.editar_produto(
        tenant, produto.id, ProdutoEditar(revisao=produto.revisao, gtin="4006381333931")
    )
    data = request(material, fornecedor, produto)
    data.itens[0].codigo_loja = "INTERNO-A"
    await service.confirmar(tenant, data, uuid4())
    scanner = ReconhecimentoCompras(service, None)
    observed = ItemObservado(
        indice=0, descricao="PRODUTO SEM DESCRIÇÃO COMPLETA", codigo_loja="INTERNO-A"
    )
    known = (await scanner.reconhecer(tenant, fornecedor.id, [observed])).itens[0]
    assert known.produto_id == produto.id and known.reconhecimento == "codigo_loja"
    other = await service.catalogo.criar_fornecedor(tenant, FornecedorCriar(nome="Outra loja"))
    assert (await scanner.reconhecer(tenant, other.id, [observed])).itens[0].produto_id is None
    second = await service.catalogo.criar_produto(
        tenant,
        ProdutoCriar(
            ingrediente_id=material.id,
            nome="Outra cobertura branca",
            marca="Outra marca",
            variante="Branco",
            conteudo_embalagem=Decimal("1.01"),
            unidade_conteudo="kg",
            aprovado=True,
            fornecedores_aprovados=[fornecedor.id],
        ),
    )
    data = request(material, fornecedor, second)
    data.itens[0].descricao_original = "OUTRA MARCA COBERTURA BRANCA 1,01KG"
    data.itens[0].codigo_loja = "INTERNO-B"
    await service.confirmar(tenant, data, uuid4())
    observed.codigo_loja = "INTERNO-B"
    observed.gtin = "4006381333931"
    observed.gtin_confirmado = True
    conflict = (await scanner.reconhecer(tenant, fornecedor.id, [observed])).itens[0]
    assert conflict.reconhecimento == "conflito" and conflict.produto_id is None
    assert len(conflict.candidatos) == 2


@pytest.mark.parametrize(
    "metadados",
    [
        {"variante_observada": "Ao leite"},
        {"conteudo_observado": Decimal("1.05"), "unidade_conteudo_observada": "kg"},
        {"conteudo_observado": Decimal("1.01"), "unidade_conteudo_observada": "l"},
    ],
)
async def test_metadados_contraditorios_bloqueiam_alias_confirmado(comercial, metadados):
    service, tenant, material, fornecedor, produto = comercial
    await service.confirmar(tenant, request(material, fornecedor, produto), uuid4())
    response = await ReconhecimentoCompras(service, None).reconhecer(
        tenant, fornecedor.id, [ItemObservado(indice=0, descricao=DESCRIPTION, **metadados)]
    )
    item = response.itens[0]
    assert item.reconhecimento == "conflito"
    assert item.produto_id is None and item.ingrediente_id is None
    assert item.pendencias


async def test_soma_dos_itens_nao_pode_ultrapassar_precision_estoque(comercial, db):
    service, tenant, material, fornecedor, produto = comercial
    row = await db.scalar(select(Ingrediente).where(Ingrediente.id == material.id))
    row.estoque_atual = Decimal("99999997")
    await db.flush()
    data = request(material, fornecedor, produto)
    data.itens = [data.itens[0].model_copy(deep=True) for _ in range(3)]
    with pytest.raises(ValidationError):
        await service.prever(tenant, data)
    with pytest.raises(ValidationError):
        await service.confirmar(tenant, data, uuid4())
    assert await count(db, Compra, tenant) == 0
    assert await count(db, MovimentacaoEstoque, tenant) == 0


async def test_whatsapp_converte_produto_aprovado_e_preserva_nota(comercial, db):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from domain.compras.comercial_schemas import FornecedorEditar
    from domain.compras.service import ComprasService
    from domain.whatsapp.messages import IncomingMessage
    from domain.whatsapp.service import WhatsAppService
    from infrastructure.database.whatsapp_models import WhatsAppCompra
    from infrastructure.ocr.gemma_adapter import ItemOCR, ResultadoOCR

    service, tenant, material, fornecedor, produto = comercial
    await service.catalogo.editar_fornecedor(
        tenant, fornecedor.id, FornecedorEditar(revisao=fornecedor.revisao, cnpj="38533519000108")
    )
    await service.confirmar(tenant, request(material, fornecedor, produto), uuid4())
    phone = "55" + str(uuid4().int)[:11]
    user = Usuario(
        tenant_id=tenant,
        nome="WhatsApp teste",
        telefone="+" + phone,
        email=f"{uuid4()}@example.com",
        senha_hash="unused",
    )
    db.add(user)
    await db.flush()
    ocr = SimpleNamespace(
        processar_imagem=AsyncMock(
            return_value=ResultadoOCR(
                itens=[
                    ItemOCR(DESCRIPTION, Decimal("1"), "un", Decimal("35.99"), Decimal("35.99"))
                ],
                estabelecimento="EMPORIO PONTO X",
                data="03/10/2026",
                total=Decimal("35.99"),
                cnpj="38533519000108",
            )
        )
    )
    adapter = SimpleNamespace(
        image=AsyncMock(return_value=(b"test", "image/jpeg")), send_text=AsyncMock()
    )
    chat = WhatsAppService(db, adapter, ComprasService(service.estoque, ocr))
    response = await chat.handle(IncomingMessage(phone, "foto", "", True, {}))
    assert "CONFIRMAR" in response
    await db.flush()
    draft = await db.scalar(select(WhatsAppCompra).where(WhatsAppCompra.tenant_id == tenant))
    assert draft.contexto["compra_v2"]["itens"][0]["unidade"] == "un"
    assert await count(db, MovimentacaoEstoque, tenant) == 1  # foto só prepara
    response = await chat.handle(IncomingMessage(phone, "confirmar", "CONFIRMAR", False, {}))
    assert "Compra salva" in response
    await db.flush()
    assert await count(db, MovimentacaoEstoque, tenant) == 2
    assert (await service.estoque.buscar(material.id, tenant)).estoque_atual == Decimal("2.0200")
    row = await db.scalar(
        select(Compra).where(Compra.tenant_id == tenant, Compra.origem == "whatsapp")
    )
    history = await service.detalhe(tenant, row.id)
    assert history.data_compra == date(2026, 10, 3)
    assert history.estabelecimento_original == "EMPORIO PONTO X"
    assert history.itens[0].snapshot["quantidade_original"] == "1"
    assert history.itens[0].snapshot["unidade_original"] == "un"
    assert history.itens[0].snapshot["marca"] == "Dr. Oetker"
    assert "Não há compra pendente" in await chat.handle(
        IncomingMessage(phone, "retry", "CONFIRMAR", False, {})
    )
    assert await count(db, MovimentacaoEstoque, tenant) == 2
    adapter.send_text.assert_not_awaited()  # nenhum transporte real


@pytest_asyncio.fixture
async def comercial(db):
    tenant = Tenant(nome="Conta compras")
    db.add(tenant)
    await db.flush()
    service = ComprasComerciais(ComprasRepository(db), EstoqueService(EstoqueRepository(db)))
    material = await service.estoque.criar_ingrediente(
        tenant.id, CriarIngredienteRequest(nome="Chocolate branco", unidade="kg")
    )
    fornecedor = await service.catalogo.criar_fornecedor(
        tenant.id, FornecedorCriar(nome="Mercado de teste")
    )
    produto = await service.catalogo.criar_produto(
        tenant.id,
        ProdutoCriar(
            ingrediente_id=material.id,
            nome="Cobertura branca",
            marca="Dr. Oetker",
            variante="Branco",
            conteudo_embalagem=Decimal("1.01"),
            unidade_conteudo="kg",
            aprovado=True,
            fornecedores_aprovados=[fornecedor.id],
        ),
    )
    return service, tenant.id, material, fornecedor, produto


def request(material, fornecedor, produto, **changes):
    item = ItemRevisado(
        ingrediente_id=material.id,
        descricao_original=DESCRIPTION,
        quantidade=Decimal("1"),
        unidade="un",
        custo_unitario=Decimal("35.99"),
        preco_total=Decimal("35.99"),
        produto_id=produto.id,
        produto_revisao=produto.revisao,
        guardar_vinculo=True,
        **changes,
    )
    return CompraRevisada(
        itens=[item],
        fornecedor_id=fornecedor.id,
        estabelecimento="Mercado de teste",
        data_compra=date(2026, 1, 3),
    )


async def count(db, model, tenant):
    return await db.scalar(select(func.count()).select_from(model).where(model.tenant_id == tenant))


async def test_primeira_compra_segunda_leitura_e_retry(comercial, db):
    service, tenant, material, fornecedor, produto = comercial
    leitura = ReconhecimentoCompras(service, None)
    observed = ItemObservado(
        indice=0,
        descricao=DESCRIPTION,
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("35.99"),
        preco_total=Decimal("35.99"),
    )
    before = await leitura.reconhecer(tenant, fornecedor.id, [observed])
    assert before.itens[0].produto_id is None
    assert before.itens[0].ingrediente_id is None  # marca não comprova que é branco
    data = request(material, fornecedor, produto)
    preview = await service.prever(tenant, data)
    assert preview.pode_confirmar
    assert preview.itens[0].quantidade_principal == Decimal("1.01")
    assert preview.itens[0].custo_normalizado == Decimal("35.63366337")
    assert await count(db, Compra, tenant) == 0
    chave = uuid4()
    result = await service.confirmar(tenant, data, chave)
    retry = await service.confirmar(tenant, data, chave)
    assert result == retry
    assert await count(db, Compra, tenant) == 1
    assert await count(db, MovimentacaoEstoque, tenant) == 1
    assert await count(db, Ingrediente, tenant) == 1
    after = await leitura.reconhecer(tenant, fornecedor.id, [observed])
    assert after.itens[0].produto_id == produto.id
    assert after.itens[0].reconhecimento == "descricao_loja"
    history = await service.detalhe(tenant, result.compra_id)
    assert history.data_compra == date(2026, 1, 3)
    assert history.itens[0].snapshot["marca"] == "Dr. Oetker"
    assert history.itens[0].snapshot["fabricante"] is None
    assert history.itens[0].snapshot["quantidade_original"] == "1"
    assert history.itens[0].snapshot["unidade_original"] == "un"
    assert (await service.estoque.buscar(material.id, tenant)).estoque_atual == Decimal("1.0100")


async def test_duas_barras_em_gramas(comercial):
    service, tenant, _, fornecedor, _ = comercial
    material = await service.estoque.criar_ingrediente(
        tenant, CriarIngredienteRequest(nome="Outro branco", unidade="g")
    )
    produto = await service.catalogo.criar_produto(
        tenant,
        ProdutoCriar(
            ingrediente_id=material.id,
            nome="Barra branca",
            marca="Teste",
            variante="Branco",
            conteudo_embalagem=Decimal("1.01"),
            unidade_conteudo="kg",
            aprovado=True,
            fornecedores_aprovados=[fornecedor.id],
        ),
    )
    data = request(material, fornecedor, produto)
    data.itens[0].quantidade = Decimal("2")
    data.itens[0].preco_total = Decimal("71.98")
    result = await service.confirmar(tenant, data, uuid4())
    assert result.itens[0].estoque_atual == Decimal("2020")
    assert result.itens[0].custo_medio == Decimal("0.0356")
    assert result.total_selecionado == Decimal("71.98")


@pytest.mark.parametrize(
    "descricao",
    [
        "COBERTURA EM BARRA DR.OETKER 1,05KG",
        "COBERTURA AO LEITE DR.OETKER 1,01KG",
    ],
)
async def test_embalagem_ou_variante_contraditoria_nao_entra(comercial, db, descricao):
    service, tenant, material, fornecedor, produto = comercial
    data = request(material, fornecedor, produto)
    data.itens[0].descricao_original = descricao
    with pytest.raises(ValidationError):
        await service.confirmar(tenant, data, uuid4())
    assert await count(db, Compra, tenant) == 0


async def test_mesma_marca_ou_outra_loja_nao_herda_alias(comercial):
    service, tenant, material, fornecedor, produto = comercial
    await service.confirmar(tenant, request(material, fornecedor, produto), uuid4())
    outro = await service.catalogo.criar_fornecedor(tenant, FornecedorCriar(nome=fornecedor.nome))
    result = await ReconhecimentoCompras(service, None).reconhecer(
        tenant, outro.id, [ItemObservado(indice=0, descricao=DESCRIPTION)]
    )
    assert result.itens[0].produto_id is None


async def test_erro_ultimo_item_rollback_inclusive_cadastros(comercial, db):
    service, tenant, material, fornecedor, produto = comercial
    data = request(material, fornecedor, produto)
    data.itens.append(
        ItemRevisado(
            criar_novo=True,
            nome="Novo",
            descricao_original="Novo",
            unidade="kg",
            quantidade=Decimal("1"),
            custo_unitario=Decimal("5"),
            preco_total=Decimal("4"),
            aceitar_excecao=True,
        )
    )
    with pytest.raises(ValidationError):
        await service.confirmar(tenant, data, uuid4())
    assert await count(db, Compra, tenant) == 0
    assert await count(db, Ingrediente, tenant) == 1
    assert await count(db, AliasCompra, tenant) == 0
    assert await count(db, MovimentacaoEstoque, tenant) == 0


async def test_falha_tardia_desfaz_primeiro_movimento(comercial, db, monkeypatch):
    service, tenant, material, fornecedor, produto = comercial
    data = request(material, fornecedor, produto)
    data.itens.append(data.itens[0].model_copy(deep=True))
    original = service.estoque.registrar_entrada_com_movimento
    chamadas = 0

    async def falha(tenant_id, entrada):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 2:
            raise ValidationError("Falha controlada no segundo item.")
        return await original(tenant_id, entrada)

    monkeypatch.setattr(service.estoque, "registrar_entrada_com_movimento", falha)
    with pytest.raises(ValidationError):
        await service.confirmar(tenant, data, uuid4())
    assert await count(db, Compra, tenant) == 0
    assert await count(db, AliasCompra, tenant) == 0
    assert await count(db, MovimentacaoEstoque, tenant) == 0
    assert (await service.estoque.buscar(material.id, tenant)).estoque_atual == 0


async def test_aprovacao_na_hora_e_excecao_sao_distintas(comercial, db):
    service, tenant, material, fornecedor, _ = comercial
    dados = ProdutoDados(
        nome="Barra",
        marca="Nova marca",
        variante="Branco",
        conteudo_embalagem=Decimal("1.01"),
        unidade_conteudo="kg",
    )
    item = ItemRevisado(
        ingrediente_id=material.id,
        descricao_original=DESCRIPTION,
        quantidade=Decimal("1"),
        unidade="un",
        custo_unitario=Decimal("35.99"),
        preco_total=Decimal("35.99"),
        produto_novo=dados,
        aceitar_excecao=True,
    )
    data = CompraRevisada(itens=[item], fornecedor_id=fornecedor.id)
    exception = await service.confirmar(tenant, data, uuid4())
    history = await service.detalhe(tenant, exception.compra_id)
    product_id = history.itens[0].produto_id
    assert not (await service.repo.produto(tenant, product_id)).aprovado
    assert await service.repo.aprovados(tenant, product_id) == []
    assert await count(db, AliasCompra, tenant) == 0
    item.aceitar_excecao = False
    item.aprovar_produto = True
    item.aprovar_fornecedor = True
    item.guardar_vinculo = True
    approved = await service.confirmar(tenant, data, uuid4())
    approved_product = (await service.detalhe(tenant, approved.compra_id)).itens[0].produto_id
    assert (await service.repo.produto(tenant, approved_product)).aprovado
    assert await service.repo.aprovados(tenant, approved_product) == [fornecedor.id]
    assert await count(db, AliasCompra, tenant) == 1


async def test_chave_corpo_alterado_conflito_e_replay_apos_inativacao(comercial):
    service, tenant, material, fornecedor, produto = comercial
    data = request(material, fornecedor, produto)
    chave = uuid4()
    result = await service.confirmar(tenant, data, chave)
    await service.catalogo.apagar_produto(tenant, produto.id, produto.revisao)
    assert await service.confirmar(tenant, data, chave) == result
    changed = data.model_copy(deep=True)
    changed.itens[0].custo_unitario = Decimal("36")
    changed.itens[0].preco_total = Decimal("36")
    with pytest.raises(ConflictError):
        await service.confirmar(tenant, changed, chave)


async def test_editar_produto_preserva_historia_invalida_alias(comercial):
    service, tenant, material, fornecedor, produto = comercial
    result = await service.confirmar(tenant, request(material, fornecedor, produto), uuid4())
    await service.catalogo.editar_produto(
        tenant,
        produto.id,
        ProdutoEditar(revisao=produto.revisao, conteudo_embalagem=Decimal("1.05")),
    )
    history = await service.detalhe(tenant, result.compra_id)
    assert Decimal(history.itens[0].snapshot["conteudo_embalagem"]) == Decimal("1.01")
    recognized = await ReconhecimentoCompras(service, None).reconhecer(
        tenant, fornecedor.id, [ItemObservado(indice=0, descricao=DESCRIPTION)]
    )
    assert recognized.itens[0].produto_id is None
    assert recognized.itens[0].pendencias


async def test_isolamento_com_controle_positivo_e_filtros(comercial, db):
    service, tenant, material, fornecedor, produto = comercial
    other = Tenant(nome="Outra conta")
    db.add(other)
    await db.flush()
    with pytest.raises(NotFoundError):
        await service.repo.produto(other.id, produto.id)
    with pytest.raises(NotFoundError):
        await service.confirmar(other.id, request(material, fornecedor, produto), uuid4())
    assert await service.repo.produto(tenant, produto.id)
    result = await service.confirmar(tenant, request(material, fornecedor, produto), uuid4())
    with pytest.raises(NotFoundError):
        await service.detalhe(other.id, result.compra_id)
    rows, count_items = await service.repo.historico(other.id)
    assert not rows and count_items == 0
    rows, count_items = await service.repo.historico(tenant, marca="dr. oetker")
    assert count_items == 1 and rows[0].id == result.compra_id


async def test_gtin_confirmado_e_codigos_conflitantes(comercial):
    service, tenant, material, fornecedor, produto = comercial
    await service.catalogo.editar_produto(
        tenant, produto.id, ProdutoEditar(revisao=produto.revisao, gtin="4006381333931")
    )
    await service.confirmar(tenant, request(material, fornecedor, produto), uuid4())
    novo_fornecedor = await service.catalogo.criar_fornecedor(
        tenant, FornecedorCriar(nome="Outra loja")
    )
    scanner = ReconhecimentoCompras(service, None)
    candidate = ItemObservado(indice=0, descricao=DESCRIPTION, gtin="4006381333931")
    assert (await scanner.reconhecer(tenant, novo_fornecedor.id, [candidate])).itens[
        0
    ].produto_id is None
    candidate.gtin_confirmado = True
    identified = (await scanner.reconhecer(tenant, novo_fornecedor.id, [candidate])).itens[0]
    assert identified.produto_id == produto.id
    assert identified.pendencias  # loja diferente ainda precisa ser aprovada
    other = await service.catalogo.criar_produto(
        tenant,
        ProdutoCriar(
            ingrediente_id=material.id,
            nome="Outra branca",
            marca="Outra",
            conteudo_embalagem=Decimal("1.01"),
            unidade_conteudo="kg",
            gtin="7891234567895",
            aprovado=True,
        ),
    )
    conflict = ItemObservado(indice=0, descricao=DESCRIPTION, gtin=other.gtin, gtin_confirmado=True)
    result = await scanner.reconhecer(tenant, fornecedor.id, [conflict])
    assert result.itens[0].reconhecimento == "conflito"
    assert result.itens[0].produto_id is None


async def test_data_ausente_desconto_e_duplicidade_fiscal(comercial):
    service, tenant, material, fornecedor, produto = comercial
    data = request(material, fornecedor, produto)
    data.data_compra = None
    data.itens[0].desconto_item = Decimal("1")
    data.itens[0].preco_total = Decimal("34.99")
    data.identidade_nota = "1" * 44
    data.identidade_confirmada = True
    result = await service.confirmar(tenant, data, uuid4())
    assert result.data_compra is None
    assert (await service.prever(tenant, data)).duplicidade
    with pytest.raises(ConflictError):
        await service.confirmar(tenant, data, uuid4())
    data.confirmar_duplicidade = True
    assert (await service.confirmar(tenant, data, uuid4())).compra_id != result.compra_id


async def test_medida_direta_nao_multiplica_embalagem_duas_vezes(comercial):
    service, tenant, material, fornecedor, produto = comercial
    data = request(material, fornecedor, produto)
    data.itens[0].unidade = "kg"
    data.itens[0].quantidade = Decimal("1.01")
    data.itens[0].custo_unitario = Decimal("35.63366337")
    preview = await service.prever(tenant, data)
    assert preview.itens[0].quantidade_principal == Decimal("1.01")


async def test_concorrencia_real_mesma_chave_e_compras_distintas(comercial, db):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    TestingSessionLocal = async_sessionmaker(db.bind, expire_on_commit=False)

    service, tenant, material, fornecedor, produto = comercial
    data = request(material, fornecedor, produto)
    data.itens[0].guardar_vinculo = False
    await db.commit()  # libera fixture; sessões concorrentes têm conexões independentes
    chave = uuid4()

    async def comprar(key):
        async with TestingSessionLocal() as session:
            current = ComprasComerciais(
                ComprasRepository(session), EstoqueService(EstoqueRepository(session))
            )
            result = await current.confirmar(tenant, data, key)
            await session.commit()
            return result

    first, replay = await asyncio.gather(comprar(chave), comprar(chave))
    assert first.compra_id == replay.compra_id
    await asyncio.gather(comprar(uuid4()), comprar(uuid4()))
    await db.refresh(await db.get(Ingrediente, material.id))
    assert (await service.estoque.buscar(material.id, tenant)).estoque_atual == Decimal("3.03")
    assert await count(db, Compra, tenant) == 3


async def test_http_catalogo_revisao_historico_auth(comercial, db, client):
    service, tenant, material, fornecedor, produto = comercial
    user = Usuario(
        tenant_id=tenant, nome="Teste", email=f"{uuid4()}@example.com", senha_hash="unused"
    )
    db.add(user)
    await db.flush()
    headers = {"Authorization": f"Bearer {create_access_token(user.id, tenant)}"}
    prefix = "/api/v1/compras"
    assert (await client.get(f"{prefix}/produtos")).status_code in (401, 403)
    listing = await client.get(f"{prefix}/produtos", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["itens"][0]["id"] == str(produto.id)
    changed = await client.patch(
        f"{prefix}/produtos/{produto.id}",
        headers=headers,
        json={"revisao": produto.revisao, "marca": "Marca revisada"},
    )
    assert changed.status_code == 200, changed.text
    outdated = await client.patch(
        f"{prefix}/produtos/{produto.id}",
        headers=headers,
        json={"revisao": 1, "marca": "Não aplicar"},
    )
    assert outdated.status_code == 409
    data = request(material, fornecedor, produto)
    response = await client.post(
        f"{prefix}/v2/confirmar",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json=data.model_dump(mode="json"),
    )
    assert response.status_code == 200, response.text
    history = await client.get(
        f"{prefix}/historico", headers=headers, params={"ingrediente_id": str(material.id)}
    )
    assert history.status_code == 200 and history.json()["total"] == 1
    purchase = await client.get(
        f"{prefix}/historico/{response.json()['compra_id']}", headers=headers
    )
    assert purchase.json()["itens"][0]["snapshot"]["marca"] == "Marca revisada"


async def test_correcao_vinculo_explicita(comercial):
    service, tenant, material, fornecedor, produto = comercial
    await service.confirmar(tenant, request(material, fornecedor, produto), uuid4())
    alias = (await service.repo.aliases(tenant))[0]
    other = await service.catalogo.criar_produto(
        tenant,
        ProdutoCriar(
            ingrediente_id=material.id,
            nome="Outro branco",
            marca="Outro",
            conteudo_embalagem=Decimal("1.01"),
            unidade_conteudo="kg",
            aprovado=True,
        ),
    )
    with pytest.raises(ConflictError):
        await service.catalogo.editar_vinculo(
            tenant,
            alias.id,
            VinculoEditar(revisao=999, produto_id=other.id, produto_revisao=other.revisao),
        )
    corrected = await service.catalogo.editar_vinculo(
        tenant,
        alias.id,
        VinculoEditar(revisao=alias.revisao, produto_id=other.id, produto_revisao=other.revisao),
    )
    assert corrected.produto_id == other.id
