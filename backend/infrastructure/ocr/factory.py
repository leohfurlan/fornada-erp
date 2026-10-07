from core.config import settings
from domain.compras.extraction import ReceiptExtractor
from infrastructure.ocr.gemma_adapter import GemmaOCRAdapter
from infrastructure.ocr.hybrid import HybridReceiptExtractor
from infrastructure.ocr.openai_adapter import OpenAIReceiptExtractor
from infrastructure.ocr.xml_adapter import DocumentReceiptExtractor


def get_receipt_extractor() -> ReceiptExtractor:
    provider = (
        settings.ocr_vision_provider if settings.ocr_provider == "hybrid" else settings.ocr_provider
    )
    vision = OpenAIReceiptExtractor() if provider == "openai" else GemmaOCRAdapter()
    image = HybridReceiptExtractor(vision) if settings.ocr_provider == "hybrid" else vision
    return DocumentReceiptExtractor(image)
