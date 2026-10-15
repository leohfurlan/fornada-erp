"""Converte todas as páginas de um cupom PDF para o leitor de imagens."""

from contextlib import closing
from io import BytesIO

import pypdfium2 as pdfium
from PIL import Image

from domain.exceptions import ValidationError


def render_receipt_pdf(data: bytes) -> bytes:
    try:
        with closing(pdfium.PdfDocument(data)) as document:
            if not 1 <= len(document) <= 5:
                raise ValidationError("Envie um PDF com 1 a 5 páginas.")
            sizes = [document.get_page_size(i) for i in range(len(document))]
            if any(w <= 0 or h <= 0 for w, h in sizes):
                raise ValidationError("O PDF contém uma página inválida.")
            scale = min(2, 2000 / max(w for w, _ in sizes),
                        6000 / sum(h for _, h in sizes))
            width = max(1, max(int(w * scale) for w, _ in sizes))
            height = sum(max(1, int(h * scale)) for _, h in sizes)
            image = Image.new("RGB", (width, height), "white")
            top = 0
            for index, (_, h) in enumerate(sizes):
                page = document[index]
                try:
                    bitmap = page.render(scale=scale)
                    try:
                        frame = bitmap.to_pil().convert("RGB")
                        image.paste(frame, (0, top))
                        frame.close()
                    finally:
                        bitmap.close()
                finally:
                    page.close()
                top += max(1, int(h * scale))
            output = BytesIO()
            image.save(output, format="PNG")
            image.close()
            return output.getvalue()
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(
            "Não foi possível abrir o PDF. Envie um PDF válido e sem senha."
        ) from exc
