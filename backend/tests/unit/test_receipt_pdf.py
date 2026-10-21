from io import BytesIO

import pytest
from PIL import Image

from domain.exceptions import ValidationError
from infrastructure.ocr.pdf import render_receipt_pdf


def pdf(pages):
    output = BytesIO()
    images = [Image.new("RGB", (100, 100), color) for color in pages]
    images[0].save(output, format="PDF", save_all=True, append_images=images[1:])
    for image in images:
        image.close()
    return output.getvalue()


def test_pdf_preserves_all_pages_in_image():
    result = render_receipt_pdf(pdf(["red", "blue"]))
    with Image.open(BytesIO(result)) as image:
        assert image.format == "PNG"
        assert image.height == image.width * 2
        assert image.getpixel((20, 20))[0] > 240
        assert image.getpixel((20, image.height - 20))[2] > 240


def test_rejects_too_many_pages():
    with pytest.raises(ValidationError, match="1 a 5 páginas"):
        render_receipt_pdf(pdf(["white"] * 6))


def test_rejects_invalid_pdf():
    with pytest.raises(ValidationError, match="PDF válido e sem senha"):
        render_receipt_pdf(b"invalid")
