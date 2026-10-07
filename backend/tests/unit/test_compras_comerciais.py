"""Limites das requests e preservação de identidade comercial."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from domain.compras.comercial_schemas import ProdutoDados
from domain.compras.identificadores import normalizar_descricao, validar_cnpj, validar_gtin
from domain.compras.reconhecimento import data_lida


def test_normalizacao_preserva_variante_e_peso():
    assert normalizar_descricao("DR.OETKER 1,01KG") == normalizar_descricao("dr oetker 1.01 kg")
    assert normalizar_descricao("BRANCO 1,01KG") != normalizar_descricao("AO LEITE 1,01KG")
    assert normalizar_descricao("BRANCO 1,01KG") != normalizar_descricao("BRANCO 1,05KG")


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity", "0.000000001", "100000000"])
def test_conteudo_invalido(value):
    with pytest.raises(ValidationError):
        ProdutoDados(
            nome="Barra", marca="Marca", conteudo_embalagem=Decimal(value), unidade_conteudo="kg"
        )


def test_identificadores_digitos_invalidos_e_null():
    assert validar_gtin("4006381333931") == "4006381333931"
    assert validar_cnpj("38.533.519/0001-08") == "38533519000108"
    assert validar_gtin(None) is None
    for code in ("4006381333932", "1234", "0000000000000"):
        with pytest.raises(ValueError):
            validar_gtin(code)
    with pytest.raises(ValueError):
        validar_cnpj("38.533.519/0001-09")


def test_data_ilegivel_nao_e_hoje():
    assert data_lida(None) is None
    assert data_lida("ilegível") is None
    assert str(data_lida("03/10/2026")) == "2026-10-03"


def test_patch_rejeita_null_obrigatorio_e_permite_fabricante_desconhecido():
    from domain.compras.comercial_schemas import FornecedorEditar, ProdutoEditar

    with pytest.raises(ValidationError):
        ProdutoEditar(revisao=1, marca=None)
    with pytest.raises(ValidationError):
        FornecedorEditar(revisao=1, nome=None)
    assert ProdutoEditar(revisao=1, fabricante=None).fabricante is None
