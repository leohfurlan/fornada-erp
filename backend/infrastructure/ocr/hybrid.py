"""OCR local primeiro; extração de visão quando texto não basta."""

import asyncio
import re
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path

from domain.compras.extraction import ItemOCR, ReceiptExtractor, ResultadoOCR, validate_receipt
from domain.exceptions import ValidationError

_NUMBER = r"\d+(?:[.,]\d+)?"
_ITEM = re.compile(
    rf"^(.+?)\s+({_NUMBER})\s+(kg|g|l|ml|un|und|pct|cx)\s*[xX×]\s*"
    rf"(?:R\$\s*)?({_NUMBER})\s+(?:R\$\s*)?({_NUMBER})$",
    re.IGNORECASE,
)
_TOTAL = re.compile(rf"^TOTAL(?:\s+A\s+PAGAR)?\s*[:=]?\s*(?:R\$\s*)?({_NUMBER})$", re.IGNORECASE)


def parse_receipt_text(text: str) -> ResultadoOCR | None:
    """Aceita apenas linhas explícitas e total reconciliado; demais layouts vão à visão."""
    items = []
    totals = []
    for line in text.splitlines():
        line = line.strip()
        match = _ITEM.fullmatch(line)
        if match:
            name, quantity, unit, price, total = match.groups()
            items.append(
                ItemOCR(
                    name,
                    Decimal(quantity.replace(",", ".")),
                    unit.lower(),
                    Decimal(price.replace(",", ".")),
                    Decimal(total.replace(",", ".")),
                )
            )
        total_match = _TOTAL.fullmatch(line)
        if total_match:
            totals.append(Decimal(total_match[1].replace(",", ".")))
    if not items or len(totals) != 1:
        return None
    try:
        result = validate_receipt(ResultadoOCR(items, totals[0], None, None, fonte="tesseract"))
    except ValidationError:
        return None
    return result if not result.avisos else None


class TesseractTextExtractor:
    async def extract(self, image: bytes) -> str:
        def run():
            with tempfile.TemporaryDirectory(prefix="fornada-ocr-") as directory:
                path = Path(directory) / "receipt"
                path.write_bytes(image)
                result = subprocess.run(
                    ["tesseract", str(path), "stdout", "-l", "por", "--psm", "6"],
                    check=True,
                    capture_output=True,
                    timeout=15,
                )
                return result.stdout.decode("utf-8", errors="replace")[:100000]

        return await asyncio.to_thread(run)


class HybridReceiptExtractor:
    def __init__(self, vision: ReceiptExtractor, text=None):
        self.vision = vision
        self.text = text or TesseractTextExtractor()

    async def processar_imagem(self, image_bytes: bytes, mime_type="image/jpeg") -> ResultadoOCR:
        try:
            text = await self.text.extract(image_bytes)
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            text = ""
        parsed = parse_receipt_text(text)
        if parsed is not None:
            return parsed
        # Nenhum item parcial é mesclado: a visão relê o documento inteiro.
        return validate_receipt(await self.vision.processar_imagem(image_bytes, mime_type))
