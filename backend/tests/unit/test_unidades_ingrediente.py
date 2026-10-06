from decimal import Decimal
import pytest
from pydantic import ValidationError as SchemaError
from domain.exceptions import ValidationError
from domain.estoque.unidades import converter_para_principal
from domain.estoque.schemas import CriarIngredienteRequest


def test_fator_depende_do_ingrediente_e_sem_float():
    assert converter_para_principal(Decimal("1.5"), "Xícara", "g", [{"unidade": "xícara", "fator": "120"}]) == Decimal("180")
    assert converter_para_principal(Decimal("1.5"), "xícara", "g", [{"unidade": "xícara", "fator": "180"}]) == Decimal("270")
    assert converter_para_principal(Decimal("3"), "colher", "g", [{"unidade": "colher", "fator": "0.1"}]) == Decimal("0.3")


def test_metricas_e_ausencia_de_densidade_implicita():
    assert converter_para_principal(Decimal("0.5"), "kg", "g") == Decimal("500")
    with pytest.raises(ValidationError):
        converter_para_principal(Decimal("1"), "ml", "g")
    with pytest.raises(ValidationError):
        converter_para_principal(Decimal("1"), "pitada", "g")


@pytest.mark.parametrize("alternativas", [[{"unidade": "xícara", "fator": "0"}], [{"unidade": "xícara", "fator": "-1"}], [{"unidade": "Xícara", "fator": "120"}, {"unidade": "xícara", "fator": "120"}]])
def test_fatores_invalidos_e_duplicatas(alternativas):
    with pytest.raises(SchemaError):
        CriarIngredienteRequest(nome="Farinha", unidade="g", unidades_alternativas=alternativas)
