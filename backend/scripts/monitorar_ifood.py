"""Processo de polling independente da tela: python -m scripts.monitorar_ifood [--once]."""

import argparse
import asyncio
import hashlib

import httpx
import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from core.config import settings
from domain.ifood.service import IfoodObservationService
from infrastructure.database.models import Tenant
from infrastructure.ifood.client import IfoodClient
from infrastructure.ifood.repository import IfoodRepository

logger = structlog.get_logger(__name__)


async def run(once: bool = False) -> None:
    """Lock de sessão PostgreSQL mantém exclusão mesmo após commit da inbox/ACK."""
    if not settings.ifood_enabled:
        raise RuntimeError("Ative o monitor iFood no ambiente de desenvolvimento configurado")
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    lock_key = int.from_bytes(
        hashlib.sha256(
            str(settings.ifood_test_merchant_id).encode(),
        ).digest()[:8],
        "big",
        signed=True,
    )
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as http:
            remote = IfoodClient(
                http,
                settings.ifood_client_id,
                settings.ifood_client_secret.get_secret_value(),
                settings.ifood_test_merchant_id,
                settings.ifood_test_merchant_name,
            )
            while True:
                try:
                    async with engine.connect() as connection:
                        acquired = await connection.scalar(
                            text("SELECT pg_try_advisory_lock(:key)"),
                            {"key": lock_key},
                        )
                        await connection.commit()
                        if acquired:
                            try:
                                async with AsyncSession(
                                    bind=connection, expire_on_commit=False
                                ) as db:
                                    tenant = await db.scalar(
                                        select(Tenant).where(
                                            Tenant.id == settings.ifood_tenant_id,
                                            Tenant.ativo.is_(True),
                                            Tenant.deleted_at.is_(None),
                                        )
                                    )
                                    if tenant is None:
                                        raise RuntimeError("Tenant de desenvolvimento indisponível")
                                    store = IfoodRepository(
                                        db,
                                        settings.ifood_tenant_id,
                                        settings.ifood_test_merchant_id,
                                        notifications_since=settings.ifood_notifications_since
                                        if settings.ifood_notifications_enabled
                                        else None,
                                        whatsapp=settings.ifood_whatsapp_enabled,
                                    )
                                    await asyncio.wait_for(
                                        IfoodObservationService(
                                            store,
                                            remote,
                                            settings.ifood_test_merchant_name,
                                            settings.ifood_poll_interval_seconds,
                                        ).tick(),
                                        timeout=110,
                                    )
                            finally:
                                await connection.rollback()
                                await connection.execute(
                                    text("SELECT pg_advisory_unlock(:key)"),
                                    {"key": lock_key},
                                )
                                await connection.commit()
                except Exception as exc:
                    logger.error(
                        "ifood_monitor_falhou",
                        tenant_id=str(settings.ifood_tenant_id),
                        action="poll",
                        entity="ifood_monitor",
                        entity_id=str(settings.ifood_test_merchant_id),
                        error_type=type(exc).__name__,
                    )
                    if once:
                        raise RuntimeError(
                            "Falha no monitor; consulte o diagnóstico sanitizado"
                        ) from None
                if once:
                    return
                try:
                    from infrastructure.celery.ifood_tasks import enqueue_notification

                    await asyncio.wait_for(asyncio.to_thread(enqueue_notification), timeout=5)
                except Exception as exc:
                    logger.error(
                        "ifood_aviso_agendamento_falhou",
                        tenant_id=str(settings.ifood_tenant_id),
                        action="enqueue",
                        entity="ifood_alerta",
                        error_type=type(exc).__name__,
                    )
                await asyncio.sleep(settings.ifood_poll_interval_seconds)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor iFood de teste, sem comandos de pedidos")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.once))
