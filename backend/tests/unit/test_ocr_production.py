import pytest

from core.config import settings
from domain.exceptions import ValidationError
from infrastructure.ocr.gemma_adapter import GemmaOCRAdapter


async def test_production_never_returns_fake_items_without_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "google_ai_api_key", "")
    with pytest.raises(ValidationError, match="indisponível"):
        await GemmaOCRAdapter().processar_imagem(b"image")


async def test_invalid_ocr_json_does_not_return_fake_items(monkeypatch) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(settings, "google_ai_api_key", "test")
    adapter = GemmaOCRAdapter()
    client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs: SimpleNamespace(text="invalid json")
        )
    )
    monkeypatch.setattr(adapter, "_get_client", lambda: client)
    with pytest.raises(ValidationError, match="nova foto"):
        await adapter.processar_imagem(b"image")
