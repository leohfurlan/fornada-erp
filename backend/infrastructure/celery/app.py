from celery import Celery

from core.config import settings

celery_app = Celery(
    "fornada",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["infrastructure.celery.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
)
