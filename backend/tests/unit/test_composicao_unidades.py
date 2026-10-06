from decimal import Decimal
import pytest
from domain.exceptions import ValidationError
from domain.receitas.composicao import converter_quantidade
from domain.producao.ficha import necessidade


@pytest.mark.parametrize("quantidade, origem, destino, esperado", [
    ("30", "g", "kg", "0.03"), ("0.025", "kg", "g", "25"),
    ("300", "ml", "l", "0.3"), ("2", "unidade", "un", "2"),
    ("1", "pct", "pct", "1"),
])
def test_conversao_deterministica(quantidade, origem, destino, esperado):
    assert converter_quantidade(Decimal(quantidade), origem, destino) == Decimal(esperado)


@pytest.mark.parametrize("origem,destino", [("g", "ml"), ("un", "kg"), ("pct", "un")])
def test_nao_converte_dimensoes_sem_contrato(origem, destino):
    with pytest.raises(ValidationError):
        converter_quantidade(Decimal("1"), origem, destino)


def test_rejeita_consumo_arredondado_para_zero():
    with pytest.raises(ValidationError):
        necessidade({"bases": {"00000000-0000-0000-0000-000000000001": "0.0001"}}, "bases", Decimal("1"))
