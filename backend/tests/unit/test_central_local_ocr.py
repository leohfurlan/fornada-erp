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
