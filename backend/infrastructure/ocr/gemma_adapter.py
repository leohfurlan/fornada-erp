"""
Adapter de visão usando Gemma 4 via Google AI Studio.

Envia a imagem do cupom fiscal e extrai itens, quantidades e preços
via prompt de visão estruturado. Retorna lista padronizada de itens.
"""

import asyncio
import json
from decimal import Decimal

import structlog

from core.config import settings
from domain.compras.extraction import ItemOCR, ResultadoOCR, receipt_from_mapping
from domain.exceptions import ValidationError

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


class GemmaOCRAdapter:
    """OCR de cupons com validação independente da resposta do modelo."""

    def __init__(self) -> None:
        self._model_name = settings.gemma_ocr_model
        self._client = None

    def _get_client(self):  # type: ignore[no-untyped-def]
        if self._client is None:
            try:
                from google import genai

                self._client = genai.Client(api_key=settings.google_ai_api_key)
            except ImportError:
                raise RuntimeError("Instale google-genai: pip install google-genai") from None
        return self._client

    async def processar_imagem(
        self, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> ResultadoOCR:
        """Processa imagem de cupom fiscal e retorna itens extraídos."""
        if not settings.google_ai_api_key:
            logger.warning("ocr_sem_api_key", fonte="gemma4")
            if settings.is_production:
                raise ValidationError(
                    "A leitura de cupons está indisponível. Tente novamente mais tarde."
                )
            return self._resultado_mock()

        try:
            client = self._get_client()
            from google.genai import types

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self._model_name,
                config=types.GenerateContentConfig(
                    temperature=settings.gemma_ocr_temperature,
                    thinking_config=types.ThinkingConfig(
                        thinking_level=settings.gemma_ocr_thinking_level.upper(),
                        include_thoughts=False,
                    ),
                ),
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    _PROMPT_OCR,
                ],
            )

            raw_text = response.text.strip()
            dados = json.loads(raw_text, parse_float=Decimal)
            result = receipt_from_mapping(dados, "gemma4")

            logger.info(
                "ocr_concluido",
                source="gemma4",
                itens_extraidos=len(result.itens),
            )

            return result

        except json.JSONDecodeError as e:
            logger.warning("ocr_json_invalido", source="gemma4")
            raise ValidationError(
                "Não conseguimos ler esse cupom. Tire uma nova foto e tente novamente."
            ) from e
        except ValidationError:
            raise
        except Exception:
            logger.warning("ocr_erro", source="gemma4")
            raise ValidationError(
                "Não conseguimos ler esse cupom. Envie outra foto ou use ITEM."
            ) from None

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
