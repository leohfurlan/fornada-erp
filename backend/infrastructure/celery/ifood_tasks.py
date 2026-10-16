import asyncio

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from core.config import settings
from domain.ifood.notifications import NotificationService
from infrastructure.celery.app import celery_app
from infrastructure.database.models import Tenant
from infrastructure.ifood.notifications import NotificationRepository
from infrastructure.ifood.whatsapp import IfoodWhatsAppSender


async def send_notification() -> None:
    if not (
        settings.ifood_enabled
        and settings.ifood_notifications_enabled
        and settings.ifood_whatsapp_enabled
    ):
        return
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            if (
                await db.scalar(
                    select(Tenant.id).where(
                        Tenant.id == settings.ifood_tenant_id,
                        Tenant.ativo.is_(True),
                        Tenant.deleted_at.is_(None),
                    )
                )
                is None
            ):
                return
            await NotificationService(
                NotificationRepository(
                    db, settings.ifood_tenant_id, settings.ifood_test_merchant_id
                ),
                IfoodWhatsAppSender(),
                settings.ifood_whatsapp_phone.get_secret_value().lstrip("+"),
                settings.frontend_url,
            ).deliver_one()
    finally:
        await engine.dispose()


@celery_app.task(name="ifood.notify", soft_time_limit=60, time_limit=75, acks_late=True)
def notify_ifood() -> None:
    try:
        asyncio.run(send_notification())
    except Exception as exc:
        structlog.get_logger(__name__).error(
            "ifood_aviso_falhou",
            tenant_id=str(settings.ifood_tenant_id),
            action="notify",
            entity="ifood_alerta",
            error_type=type(exc).__name__,
        )
        # A fila durável será revisitada pelo próximo ciclo, sem logar transporte/segredos.


def enqueue_notification() -> None:
    if settings.ifood_notifications_enabled and settings.ifood_whatsapp_enabled:
        notify_ifood.apply_async(retry=False)
