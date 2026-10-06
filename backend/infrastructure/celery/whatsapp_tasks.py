"""Worker sem mídia/base64 na fila, com lock distribuído por remetente."""

import asyncio
import hashlib

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from core.config import settings
from domain.compras.service import ComprasService
from domain.estoque.repository import EstoqueRepository
from domain.estoque.service import EstoqueService
from domain.whatsapp.messages import parse_message
from domain.whatsapp.service import WhatsAppService
from infrastructure.celery.app import celery_app
from infrastructure.ocr.gemma_adapter import GemmaOCRAdapter
from infrastructure.whatsapp.evolution import EvolutionAdapter


async def run_message(payload: dict) -> None:
    if not settings.evolution_enabled:
        return
    incoming = parse_message(payload, settings.evolution_instance)
    if not incoming:
        return
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    key = hashlib.sha256(incoming.phone.encode()).hexdigest()
    try:
        # Celery hard limit < lock TTL, impedindo confirmação concorrente do mesmo remetente.
        async with redis.lock(f"wa:sender:{key}", timeout=180, blocking_timeout=5):
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                compras = ComprasService(EstoqueService(EstoqueRepository(db)), GemmaOCRAdapter())
                await WhatsAppService(db, EvolutionAdapter(), compras).process(incoming)
    finally:
        await engine.dispose()
        await redis.aclose()


@celery_app.task(
    bind=True,
    name="whatsapp.process",
    max_retries=5,
    soft_time_limit=120,
    time_limit=150,
    acks_late=True,
)
def process_whatsapp(self, payload: dict) -> None:
    try:
        asyncio.run(run_message(payload))
    except Exception:
        # Não grava payload, credenciais ou conteúdo pessoal no erro da task.
        raise self.retry(
            exc=RuntimeError("Falha no processamento WhatsApp"), countdown=15
        ) from None
