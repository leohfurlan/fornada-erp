"""Monitor autenticado, com acesso limitado ao tenant configurado para o piloto."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, get_tenant_id
from core.config import settings
from domain.ifood.schemas import AlertFeed, MonitorView
from infrastructure.database.models import Usuario
from infrastructure.database.session import get_db
from infrastructure.ifood.notifications import NotificationRepository
from infrastructure.ifood.repository import IfoodRepository

router = APIRouter(prefix="/integracoes/ifood", tags=["Integrações"])


@router.get("/monitor", response_model=MonitorView)
async def monitor(
    tenant_id: UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> MonitorView:
    if tenant_id != settings.ifood_tenant_id or settings.ifood_test_merchant_id is None:
        return MonitorView(
            habilitado=False, intervalo_segundos=settings.ifood_poll_interval_seconds
        )
    view = await IfoodRepository(db, tenant_id, settings.ifood_test_merchant_id).view(
        settings.ifood_enabled,
        settings.ifood_poll_interval_seconds,
    )
    view.alertas_habilitados = settings.ifood_notifications_enabled
    view.whatsapp_habilitado = settings.ifood_whatsapp_enabled
    view.whatsapp_final = (
        settings.ifood_whatsapp_phone.get_secret_value()[-4:]
        if settings.ifood_whatsapp_enabled
        else None
    )
    return view


def alerts_enabled(tenant_id: UUID) -> bool:
    return bool(
        settings.ifood_enabled
        and settings.ifood_notifications_enabled
        and tenant_id == settings.ifood_tenant_id
        and settings.ifood_test_merchant_id
    )


@router.get("/alertas", response_model=AlertFeed)
async def alerts(
    response: Response,
    user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertFeed:
    response.headers["Cache-Control"] = "no-store"
    if not alerts_enabled(user.tenant_id):
        return AlertFeed()
    return await NotificationRepository(db, user.tenant_id, settings.ifood_test_merchant_id).feed(
        user.id
    )


@router.post("/alertas/{alert_id}/lido", status_code=204)
async def read_alert(
    alert_id: UUID, user: Usuario = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    if not alerts_enabled(user.tenant_id) or not await NotificationRepository(
        db,
        user.tenant_id,
        settings.ifood_test_merchant_id,
    ).read(alert_id, user.id):
        raise HTTPException(status_code=404, detail="Aviso indisponível.")
    return Response(status_code=204)
