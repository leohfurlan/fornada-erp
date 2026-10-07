import pytest
from pydantic import ValidationError

from domain.receitas.ficha_tecnica import FichaTecnicaInput, FichaTecnicaResponse


def ficha_data(text: str) -> dict:
    return {
        "descricao_produto": text,
        "especificacao_final": text,
        "revisao": 0,
        "passos": [{
            "descricao": "  Montagem  ", "tipo": "acabamento",
            "quantidade": "1", "unidade": "un",
            "instrucao": text, "especificacao": text,
        }],
    }


@pytest.mark.parametrize("source", [
    "    exemplo de bloco indentado\n    segunda linha\n",
    "Primeira linha  \nSegunda linha  ",
    "## Produto\n\n**Chocolate** e *morango*.\n\n- Montar\n- Finalizar",
])
def test_markdown_roundtrip_preserves_indentation_and_breaks(source: str) -> None:
    request = FichaTecnicaInput.model_validate(ficha_data(source))
    stored = request.model_dump(mode="json")
    response = FichaTecnicaResponse.model_validate(stored)
    assert response.descricao_produto == source
    assert response.especificacao_final == source
    assert response.passos[0].instrucao == source
    assert response.passos[0].especificacao == source
    assert response.passos[0].descricao == "Montagem"


@pytest.mark.parametrize("source", ["", "  ", "\n\t"])
def test_description_still_requires_content(source: str) -> None:
    with pytest.raises(ValidationError):
        FichaTecnicaInput.model_validate(ficha_data(source))
