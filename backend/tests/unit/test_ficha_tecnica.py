from decimal import Decimal

import pytest
from pydantic import ValidationError

from domain.receitas.ficha_tecnica import FichaTecnicaInput, PassoMontagem


def passo(**extras):
    return dict(descricao="Camada de bolo", tipo="componente", quantidade="225", unidade="g", **extras)


def test_faixa_preserva_decimais_e_camadas_repetidas():
    camada = passo(quantidade_minima="200", quantidade_maxima="250")
    ficha = FichaTecnicaInput(descricao_produto="Bolo pequeno", passos=[camada, camada], revisao=0)
    assert len(ficha.passos) == 2
    assert ficha.passos[0].quantidade == Decimal("225")
    assert ficha.model_dump(mode="json")["passos"][0]["quantidade_minima"] == "200"


@pytest.mark.parametrize("limites", [
    {"quantidade_minima": "200"},
    {"quantidade_minima": "250", "quantidade_maxima": "200"},
    {"quantidade_minima": "230", "quantidade_maxima": "250"},
])
def test_rejeita_faixa_incompleta_invertida_ou_fora_do_nominal(limites):
    with pytest.raises(ValidationError):
        PassoMontagem(**passo(**limites))


def test_embalagem_capacidade_nao_substitui_quantidade():
    embalagem = PassoMontagem(descricao="Copo", tipo="embalagem", quantidade="1", unidade="un", especificacao="300 ml")
    assert embalagem.quantidade == Decimal("1")
    assert embalagem.unidade == "un"
