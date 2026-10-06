import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest

from core.config import settings
from domain.compras.decisions import CatalogChoice, CatalogMatcher
from domain.compras.extraction import ItemOCR, ResultadoOCR, receipt_from_mapping
from domain.compras.matching import IngredienteRef
from domain.compras.service import ComprasService
from domain.exceptions import ValidationError
from infrastructure.ocr.gemma_adapter import GemmaOCRAdapter
from infrastructure.ocr.hybrid import HybridReceiptExtractor, parse_receipt_text
from infrastructure.ocr.openai_adapter import OpenAIReceiptExtractor
from infrastructure.ocr.xml_adapter import DocumentReceiptExtractor, parse_nfe_xml


def mapping():
    return {
        "itens": [
            {
                "descricao": "Açúcar",
                "quantidade": 2,
                "unidade": "un",
                "preco_unitario": 5.90,
                "preco_total": 11.80,
            }
        ],
        "total": 11.80,
        "estabelecimento": "Mercado",
        "data": None,
    }


@pytest.mark.asyncio
async def test_gemma_sends_selected_model_temperature_and_minimal_thinking(monkeypatch):
    monkeypatch.setattr(settings, "google_ai_api_key", "test-only")
    adapter = GemmaOCRAdapter()
    generate = Mock(return_value=SimpleNamespace(text=json.dumps(mapping())))
    adapter._client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    result = await adapter.processar_imagem(b"test-image")
    request = generate.call_args.kwargs
    assert request["model"] == "gemma-4-26b-a4b-it"
    assert request["config"].temperature == 0.1
    assert request["config"].thinking_config.thinking_level.value == "MINIMAL"
    assert request["config"].thinking_config.include_thoughts is False
    assert result.fonte == "gemma4"
    assert result.confianca is None


@pytest.mark.parametrize("value", [None, True, "NaN", "Infinity", 0, -1])
def test_missing_and_invalid_values_are_never_defaulted(value):
    data = mapping()
    data["itens"][0]["quantidade"] = value
    with pytest.raises(ValidationError):
        receipt_from_mapping(data, "test")


def test_prices_use_decimal_and_no_fake_confidence():
    result = receipt_from_mapping(mapping(), "test")
    assert result.itens[0].preco_unitario == Decimal("5.9")
    assert result.confianca is None


def test_item_total_mismatch_blocks_preview():
    data = mapping()
    data["itens"][0]["preco_total"] = 15
    with pytest.raises(ValidationError, match="não conferem"):
        receipt_from_mapping(data, "test")


def test_grand_total_mismatch_warns_without_changing_prices():
    data = mapping()
    data["total"] = 10
    result = receipt_from_mapping(data, "test")
    assert result.avisos and result.total == Decimal(10)
    assert result.itens[0].preco_total == Decimal("11.8")


async def test_readable_text_skips_paid_vision():
    vision = SimpleNamespace(processar_imagem=AsyncMock())
    text = SimpleNamespace(extract=AsyncMock(return_value="Açúcar 2 UN X 5,90 11,80\nTOTAL 11,80"))
    result = await HybridReceiptExtractor(vision, text).processar_imagem(b"image")
    assert result.fonte == "tesseract"
    vision.processar_imagem.assert_not_called()


async def test_partial_text_falls_back_to_complete_vision_extraction():
    vision_result = receipt_from_mapping(mapping(), "openai")
    vision = SimpleNamespace(processar_imagem=AsyncMock(return_value=vision_result))
    text = SimpleNamespace(extract=AsyncMock(return_value="Açúcar 2 UN X 5,90 11,80\nTOTAL 20,00"))
    result = await HybridReceiptExtractor(vision, text).processar_imagem(b"image")
    vision.processar_imagem.assert_awaited_once()
    assert len(result.itens) == 1 and result.fonte == "openai"


def test_unsupported_layout_is_not_partial_success():
    assert parse_receipt_text("Açúcar 2 UN X 5,90 11,80") is None


async def test_external_decision_cannot_choose_foreign_tenant_id():
    own = IngredienteRef(str(uuid4()), "Açúcar", "kg", "ingrediente")
    provider = SimpleNamespace(choose=AsyncMock(return_value=CatalogChoice(str(uuid4()), 1)))
    result = await CatalogMatcher(provider).suggest("Açúcar", "kg", [own])
    assert result.ingrediente_id is None


async def test_ambiguous_catalog_match_abstains():
    candidates = [IngredienteRef(str(uuid4()), "Açúcar", "kg", "ingrediente") for _ in range(2)]
    result = await CatalogMatcher().suggest("Açúcar", "kg", candidates)
    assert result.ingrediente_id is None


async def test_invalid_extraction_does_not_reach_catalog_or_stock():
    stock = SimpleNamespace(listar=AsyncMock())
    extraction = SimpleNamespace(
        processar_imagem=AsyncMock(
            return_value=ResultadoOCR([ItemOCR("Açúcar", None, "kg", 5, 5)], 5, None, None)
        )
    )
    with pytest.raises(ValidationError):
        await ComprasService(stock, extraction).processar_ocr(uuid4(), b"image")
    stock.listar.assert_not_called()


def xml():
    return b"""<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe>
    <ide><mod>65</mod></ide><emit><xNome>Mercado</xNome></emit>
    <det><prod><xProd>Acucar</xProd><qCom>2</qCom><uCom>UN</uCom>
    <vUnCom>5.90</vUnCom><vProd>11.80</vProd></prod></det>
    <total><ICMSTot><vNF>11.80</vNF></ICMSTot></total></infNFe></NFe>"""


async def test_xml_does_not_require_or_call_ai():
    vision = SimpleNamespace(processar_imagem=AsyncMock())
    result = await DocumentReceiptExtractor(vision).processar_imagem(xml(), "application/xml")
    assert result.fonte == "xml_nfe" and result.itens[0].quantidade == Decimal(2)
    vision.processar_imagem.assert_not_called()


async def test_upload_route_accepts_xml_without_creating_stock():
    from api.dependencies import get_tenant_id
    from api.routers.compras import get_compras_service
    from main import app

    stock = SimpleNamespace(listar=AsyncMock(return_value=[]))
    service = ComprasService(stock, DocumentReceiptExtractor(None))
    app.dependency_overrides[get_tenant_id] = lambda: uuid4()
    app.dependency_overrides[get_compras_service] = lambda: service
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/compras/ocr", files={"arquivo": ("nota.xml", xml(), "application/xml")}
            )
        assert response.status_code == 200
        assert response.json()["fonte"] == "xml_nfe"
        assert response.json()["confianca"] is None
        assert response.json()["itens"][0]["quantidade"] == "2"
        stock.listar.assert_awaited_once()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("document", [b"<other/>", b"<!DOCTYPE NFe><NFe/>", b"<broken"])
def test_invalid_or_unsafe_xml_is_rejected(document):
    with pytest.raises(ValidationError):
        parse_nfe_xml(document)


async def test_openai_schema_request_and_response(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_ocr_model", "configured-model")
    original = httpx.AsyncClient

    def handle(request):
        payload = json.loads(request.content)
        assert payload["model"] == "configured-model" and payload["store"] is False
        assert payload["text"]["format"]["strict"] is True
        assert payload["text"]["format"]["schema"]["additionalProperties"] is False
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(mapping())}],
                    }
                ],
            },
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    result = await OpenAIReceiptExtractor().processar_imagem(b"image")
    assert result.fonte == "openai" and result.confianca is None


@pytest.mark.parametrize(
    "body",
    [
        {"status": "incomplete"},
        {
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}],
        },
    ],
)
async def test_openai_refusal_and_incomplete_response_do_not_create_items(monkeypatch, body):
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_ocr_model", "configured-model")
    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)), **kwargs
        ),
    )
    with pytest.raises(ValidationError):
        await OpenAIReceiptExtractor().processar_imagem(b"image")
