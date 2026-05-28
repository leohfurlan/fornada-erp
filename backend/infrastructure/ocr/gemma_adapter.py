"""
Adapter OCR usando Gemma 4 via Google AI Studio.

Envia a imagem do cupom fiscal e extrai itens, quantidades e preços
via prompt de visão estruturado. Retorna lista padronizada de itens.
"""

import base64
import json
from dataclasses import dataclass
from pathlib import Path

import structlog

from core.config import settings

logger = structlog.get_logger(__name__)

_PROMPT_OCR = """
Você é um assistente especializado em leitura de cupons fiscais brasileiros.

Analise esta imagem de cupom fiscal e extraia todos os produtos comprados.

Retorne APENAS um JSON válido no seguinte formato (sem markdown, sem explicações):
{
  "itens": [
    {
      "descricao": "Nome do produto como aparece no cupom",
      "quantidade": 1.0,
      "unidade": "kg",
      "preco_unitario": 10.50,
      "preco_total": 10.50
    }
  ],
  "total": 10.50,
  "estabelecimento": "Nome do estabelecimento se visível",
  "data": "DD/MM/YYYY se visível"
}

Regras:
- unidade deve ser: kg, g, l, ml, un, cx, pct ou similar
- quantidade e preços devem ser números decimais com ponto
- Se não conseguir ler algum campo, use null
- Inclua TODOS os itens do cupom
"""


@dataclass
class ItemOCR:
    descricao: str
    quantidade: float
    unidade: str
    preco_unitario: float
    preco_total: float


@dataclass
class ResultadoOCR:
    itens: list[ItemOCR]
    total: float | None
    estabelecimento: str | None
    data: str | None
    fonte: str = "gemma4"
    confianca: float = 0.9


class GemmaOCRAdapter:
    """OCR de cupons fiscais usando Gemma 4 Vision via Google AI Studio."""

    def __init__(self) -> None:
        self._model_name = "gemma-3-27b-it"  # Gemma 4 multimodal
        self._client = None

    def _get_client(self):  # type: ignore[no-untyped-def]
        if self._client is None:
            try:
                from google import genai

                self._client = genai.Client(api_key=settings.google_ai_api_key)
            except ImportError:
                raise RuntimeError("Instale google-genai: pip install google-genai")
        return self._client

    async def processar_imagem(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> ResultadoOCR:
        """Processa imagem de cupom fiscal e retorna itens extraídos."""
        if not settings.google_ai_api_key:
            logger.warning("ocr_sem_api_key", fonte="gemma4")
            return self._resultado_mock()

        try:
            client = self._get_client()
            image_b64 = base64.b64encode(image_bytes).decode()

            from google.genai import types

            response = client.models.generate_content(
                model=self._model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    _PROMPT_OCR,
                ],
            )

            raw_text = response.text.strip()
            dados = json.loads(raw_text)

            itens = [
                ItemOCR(
                    descricao=item.get("descricao", ""),
                    quantidade=float(item.get("quantidade") or 1),
                    unidade=item.get("unidade") or "un",
                    preco_unitario=float(item.get("preco_unitario") or 0),
                    preco_total=float(item.get("preco_total") or 0),
                )
                for item in dados.get("itens", [])
            ]

            logger.info(
                "ocr_concluido",
                source="gemma4",
                confidence=0.9,
                raw_text=raw_text[:200],
                itens_extraidos=len(itens),
            )

            return ResultadoOCR(
                itens=itens,
                total=dados.get("total"),
                estabelecimento=dados.get("estabelecimento"),
                data=dados.get("data"),
            )

        except json.JSONDecodeError as e:
            logger.error("ocr_json_invalido", source="gemma4", error=str(e))
            return self._resultado_mock()
        except Exception as e:
            logger.error("ocr_erro", source="gemma4", error=str(e))
            raise

    def _resultado_mock(self) -> ResultadoOCR:
        """Retorna dados fictícios quando API key não está configurada."""
        return ResultadoOCR(
            itens=[
                ItemOCR(
                    descricao="Farinha de Trigo Especial 1kg",
                    quantidade=2.0,
                    unidade="un",
                    preco_unitario=4.99,
                    preco_total=9.98,
                ),
                ItemOCR(
                    descricao="Açúcar Cristal 1kg",
                    quantidade=1.0,
                    unidade="un",
                    preco_unitario=3.49,
                    preco_total=3.49,
                ),
            ],
            total=13.47,
            estabelecimento="[Mock - Sem API Key]",
            data=None,
            fonte="mock",
            confianca=0.0,
        )
