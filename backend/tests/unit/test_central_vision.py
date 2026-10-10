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


@pytest.mark.asyncio
async def test_provider_uses_bounded_single_attempt_and_minimal_thinking(monkeypatch):
    from google import genai

    calls = []

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["http_options"].timeout == 45000
            assert kwargs["http_options"].retry_options.attempts == 1
            self.models = self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def generate_content(self, **kwargs):
            calls.append(kwargs)
            assert kwargs["config"].thinking_config.thinking_level.lower() == "minimal"
            return SimpleNamespace(text=payload())

    monkeypatch.setattr(genai, "Client", Client)
    settings = SimpleNamespace(
        central_public_ocr_enabled=True,
        google_ai_api_key="synthetic",
        central_ocr_model="gemma-4-26b-a4b-it",
    )
    result = await CentralVisionExtractor(settings).processar_imagem(b"synthetic")
    assert len(calls) == 1 and len(result.itens) == 1


def test_repeated_lines_count_is_checked_without_inventing_an_item():
    result = parse_vision(payload(quantidade_itens=2))
    assert len(result.itens) == 1
    assert any("2 itens" in warning for warning in result.avisos)


def test_non_food_category_is_preserved_for_approval():
    data = json.loads(payload())
    data["itens"][0]["tipo_material"] = "descartavel"
    assert parse_vision(json.dumps(data)).itens[0].tipo_material == "descartavel"


@pytest.mark.asyncio
async def test_visual_reading_receives_local_transcription_without_logging(monkeypatch):
    from google import genai

    class Text:
        async def extract(self, image):
            return "synthetic repeated row\nsynthetic repeated row"

    class Client:
        def __init__(self, **kwargs):
            self.models = self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def generate_content(self, **kwargs):
            assert kwargs["contents"][1].count("synthetic repeated row") == 2
            assert "<receipt_text>" in kwargs["contents"][1]
            return SimpleNamespace(text=payload())

    monkeypatch.setattr(genai, "Client", Client)
    settings = SimpleNamespace(
        central_public_ocr_enabled=True,
        google_ai_api_key="synthetic",
        central_ocr_model="gemma-4-26b-a4b-it",
    )
    result = await CentralVisionExtractor(settings, Text()).processar_imagem(b"synthetic")
    assert not result.avisos
