import pytest
from domain.exceptions import ValidationError
from domain.usuarios.telefone import normalizar_telefone


def test_preserva_nono_digito_e_normaliza_mascara():
    assert normalizar_telefone("(11) 98765-4321", "BR") == "+5511987654321"
    assert normalizar_telefone("+5511987654321", "BR") == "+5511987654321"


@pytest.mark.parametrize("telefone, regiao", [("1198765432", "BR"), ("abc", "BR"), ("123", "ZZ"), ("123", "PT")])
def test_rejeita_numero_invalido(telefone, regiao):
    with pytest.raises(ValidationError):
        normalizar_telefone(telefone, regiao)
