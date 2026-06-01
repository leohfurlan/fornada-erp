from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_id
from domain.dashboard.schemas import DashboardResumoResponse
from domain.dashboard.service import DashboardService
from infrastructure.database.session import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/resumo", response_model=DashboardResumoResponse)
async def resumo_dashboard(
    tenant_id: UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DashboardResumoResponse:
    """Resumo agregado do dia para a home: financeiro da semana, operacional e alertas de estoque."""
    return await DashboardService(db).resumo(tenant_id)
