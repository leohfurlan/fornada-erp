import asyncio

import structlog

from infrastructure.celery.app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def processar_ocr_cupom(self, task_id: str, image_b64: str, mime_type: str = "image/jpeg") -> dict:
    """Processa OCR de cupom fiscal de forma assíncrona."""
    import base64

    from infrastructure.ocr.gemma_adapter import GemmaOCRAdapter

    async def _run() -> dict:
        adapter = GemmaOCRAdapter()
        image_bytes = base64.b64decode(image_b64)
        resultado = await adapter.processar_imagem(image_bytes, mime_type)
        return {
            "task_id": task_id,
            "itens": [
                {
                    "descricao": item.descricao,
                    "quantidade": item.quantidade,
                    "unidade": item.unidade,
                    "preco_unitario": item.preco_unitario,
                    "preco_total": item.preco_total,
                }
                for item in resultado.itens
            ],
            "total": resultado.total,
            "estabelecimento": resultado.estabelecimento,
            "fonte": resultado.fonte,
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("celery_ocr_erro", task_id=task_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)
