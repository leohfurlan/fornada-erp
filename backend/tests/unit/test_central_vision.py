import json
from types import SimpleNamespace

import pytest

from domain.exceptions import ValidationError
from infrastructure.ocr.central_vision import CentralVisionExtractor, parse_vision


def payload(**changes):
    data = dict(
        itens=[
            dict(
                descricao="CHOCOLATE",
                quantidade=1,
                unidade="un",
                preco_unitario=35.99,
                preco_total=35.99,
                marca="DR OETKER",
                conteudo_embalagem=1.01,
                unidade_conteudo="kg",
            )
        ],
        total=35.99,
        estabelecimento="EMPORIO",
        data="03/10/2026",
    )
    data.update(changes)
    return json.dumps(data)


def test_complete_vision_preserves_fiscal_and_package_quantities():
    result = parse_vision(payload())
    assert result.itens[0].quantidade == 1
    assert str(result.itens[0].conteudo_embalagem) == "1.01"
    assert result.fonte == "google_vision" and not result.avisos


def test_unreadable_numbers_are_not_defaulted():
    data = json.loads(payload())
    data["itens"][0]["quantidade"] = None
    result = parse_vision(json.dumps(data))
    assert result.itens[0].quantidade is None and result.avisos
    assert "quantidade" in result.itens[0].campos_pendentes


def test_inconsistent_vision_cannot_prepare_summary():
    data = json.loads(payload())
    data["itens"][0]["quantidade"] = 2
    assert parse_vision(json.dumps(data)).avisos


@pytest.mark.parametrize("text", ["{}", "not json", "[]", payload(itens=[])])
def test_malformed_vision_fails(text):
    with pytest.raises(ValidationError):
        parse_vision(text)


@pytest.mark.asyncio
async def test_disabled_vision_never_calls_provider():
    with pytest.raises(ValidationError):
        await CentralVisionExtractor(
            SimpleNamespace(central_public_ocr_enabled=False)
        ).processar_imagem(b"image")
