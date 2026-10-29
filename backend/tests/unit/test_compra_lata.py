"""Entrada de latas usa o conteudo informado, sem presumir peso por lata."""

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from domain.compras.comercial import ComprasComerciais
from domain.compras.comercial_schemas import CompraRevisada, ItemRevisado, ProdutoDados
from domain.compras.review_errors import PurchaseReviewError


def prever_sem_io(service, compra):
    # Todos os awaits usam AsyncMock: nenhum banco, socket ou event loop e necessario.
    coroutine = service.prever(uuid4(), compra)
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    finally:
        coroutine.close()
    raise AssertionError("A previa tentou realizar I/O no teste unitario")


@pytest.mark.parametrize("unidade", ["lata", "Lata", " LATA ", "un"])
@pytest.mark.parametrize("quantidade", ["1", "3"])
def test_previa_lata_converte_conteudo_para_kg(unidade, quantidade):
    repo = AsyncMock()
    repo.duplicadas.return_value = []
    service = ComprasComerciais(repo, AsyncMock())
    quantidade = Decimal(quantidade)
    compra = CompraRevisada(itens=[ItemRevisado(
        criar_novo=True, nome="Doce de leite", unidade_principal="kg",
        descricao_original="DOCE LEITE ITAMBE 395G TRAD",
        quantidade=quantidade, unidade=unidade, custo_unitario=Decimal("12.98"),
        preco_total=quantidade * Decimal("12.98"), aceitar_excecao=True,
        produto_novo=ProdutoDados(
            nome="DOCE LEITE ITAMBE 395G TRAD", marca="ITAMBE",
            conteudo_embalagem=Decimal("395"), unidade_conteudo="g",
        ),
    )])

    previa = prever_sem_io(service, compra)

    assert previa.pode_confirmar
    assert previa.itens[0].quantidade_principal == quantidade * Decimal("0.395")
    assert previa.itens[0].fator_aplicado == Decimal("0.395")
    assert previa.itens[0].unidade_principal == "kg"


def test_lata_sem_conteudo_nao_presume_peso():
    service = ComprasComerciais(AsyncMock(), AsyncMock())
    compra = CompraRevisada(itens=[ItemRevisado(
        criar_novo=True, nome="Doce de leite", unidade_principal="kg",
        descricao_original="DOCE DE LEITE", quantidade=Decimal("1"), unidade="lata",
        custo_unitario=Decimal("12.98"), preco_total=Decimal("12.98"),
        aceitar_excecao=True,
    )])

    with pytest.raises(PurchaseReviewError) as exc:
        prever_sem_io(service, compra)

    assert exc.value.issue["code"] == "fiscal_conversion_required"
