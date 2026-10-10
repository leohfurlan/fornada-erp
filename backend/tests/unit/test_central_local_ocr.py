"""Extração local não inventa itens nem usa visão pública na central."""

from decimal import Decimal

import pytest

from api.routers.central import NoPublicVision
from domain.exceptions import ValidationError
from infrastructure.ocr.hybrid import HybridReceiptExtractor, parse_receipt_text


def test_complete_local_receipt_has_reconciled_decimal_values():
    result = parse_receipt_text("Açúcar 2 UN X 5,90 11,80\nTOTAL 11,80")
    assert result.fonte == "tesseract"
    assert result.itens[0].preco_unitario == Decimal("5.90")
    assert result.total == Decimal("11.80")


@pytest.mark.parametrize(
    "text", ["Açúcar 2 UN X 5,90 11,80", "Açúcar 2 UN X 5,90 11,80\nTOTAL 20,00", "illegible"]
)
def test_incomplete_or_unreconciled_local_text_requires_review(text):
    assert parse_receipt_text(text) is None


async def test_unavailable_local_ocr_requires_manual_review():
    class MissingLocalBinary:
        async def extract(self, image):
            raise FileNotFoundError("synthetic missing local OCR")

    with pytest.raises(ValidationError, match="localmente"):
        await HybridReceiptExtractor(NoPublicVision(), MissingLocalBinary()).processar_imagem(
            b"image"
        )


def test_split_receipt_lines_prefill_without_inventing_receipt_total():
    from infrastructure.ocr.hybrid import parse_partial_receipt_text

    result = parse_partial_receipt_text(
        "123456 COBERTURA EM BARRA\n' 1 UN 35,99000 35,99\nTOTAL ILEGIVEL"
    )
    assert result and result.fonte == "tesseract"
    assert result.itens[0].quantidade == Decimal("1")
    assert result.itens[0].unidade == "un"
    assert result.itens[0].preco_total == Decimal("35.99")
    assert result.total is None
    assert len(result.avisos) >= 2


def test_split_receipt_rejects_inconsistent_item_amounts():
    from infrastructure.ocr.hybrid import parse_partial_receipt_text

    assert parse_partial_receipt_text("123456 FARINHA\n2 UN 10,00 10,00") is None


async def test_hybrid_returns_partial_rows_for_mandatory_review_without_public_vision():
    class LocalText:
        async def extract(self, image):
            return "123456 FARINHA\n2 UN 10,00 20,00"

    result = await HybridReceiptExtractor(NoPublicVision(), LocalText()).processar_imagem(b"image")
    assert result.total is None and result.avisos
    assert len(result.itens) == 1
