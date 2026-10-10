from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from domain.compras.automatic import propose_purchase
from domain.compras.comercial_schemas import LeituraCompra
from domain.exceptions import ValidationError


def reading(**changes):
    data = dict(
        itens=[
            dict(
                indice=0,
                descricao="CHOCOLATE BRANCO 1,01KG",
                quantidade="1",
                unidade="un",
                preco_unitario="35.99",
                preco_total="35.99",
                marca_observada="DR. OETKER",
                conteudo_observado="1.01",
                unidade_conteudo_observada="kg",
            )
        ],
        total_nota="35.99",
        estabelecimento="EMPORIO",
        data_compra="2026-10-03",
        data_original="03/10/2026",
        fornecedor_id=None,
        fornecedores_candidatos=[],
        fonte="google_vision",
        confianca=None,
        aviso_mock=False,
        avisos=[],
    )
    data.update(changes)
    return LeituraCompra.model_validate(data)


def test_new_catalog_is_proposed_without_writes():
    proposal = propose_purchase(reading(), [], [], [])
    item = proposal.itens[0]
    assert item.criar_novo and item.produto_novo.marca == "DR. OETKER"
    assert item.quantidade == 1 and item.produto_novo.conteudo_embalagem == Decimal("1.01")
    assert item.unidade_principal == "kg"
    assert item.aprovar_produto and item.aprovar_fornecedor and item.guardar_vinculo
    assert proposal.fornecedor_novo.nome == "EMPORIO"


def test_existing_exact_product_reused():
    material = SimpleNamespace(
        id=uuid4(), nome="Chocolate branco", unidade="kg", tipo="ingrediente"
    )
    product = SimpleNamespace(
        id=uuid4(),
        ingrediente_id=material.id,
        revisao=3,
        nome="CHOCOLATE BRANCO 1,01KG",
        marca="DR. OETKER",
        conteudo_embalagem=Decimal("1.01"),
        unidade_conteudo="kg",
    )
    proposal = propose_purchase(reading(), [product], [material], [])
    assert proposal.itens[0].produto_id == product.id
    assert not proposal.itens[0].criar_novo


@pytest.mark.parametrize(
    "field,value",
    [
        ("marca_observada", None),
        ("conteudo_observado", None),
        ("quantidade", None),
        ("preco_unitario", Decimal("10")),
    ],
)
def test_missing_or_inconsistent_fields_do_not_prepare(field, value):
    r = reading()
    setattr(r.itens[0], field, value)
    with pytest.raises(ValidationError):
        propose_purchase(r, [], [], [])


def test_warnings_and_missing_supplier_stop_summary():
    for r in [reading(avisos=["Soma divergente"]), reading(estabelecimento=None)]:
        with pytest.raises(ValidationError):
            propose_purchase(r, [], [], [])


def test_multiple_exact_products_require_disambiguation():
    material = SimpleNamespace(
        id=uuid4(), nome="Chocolate branco", unidade="kg", tipo="ingrediente"
    )
    products = [
        SimpleNamespace(
            id=uuid4(),
            ingrediente_id=material.id,
            revisao=1,
            nome="CHOCOLATE BRANCO 1,01KG",
            marca="DR. OETKER",
            conteudo_embalagem=Decimal("1.01"),
            unidade_conteudo="kg",
        )
        for _ in range(2)
    ]
    with pytest.raises(ValidationError):
        propose_purchase(reading(), products, [material], [])
