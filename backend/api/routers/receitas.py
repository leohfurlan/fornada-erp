from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, get_tenant_id
from domain.receitas.repository import ReceitaRepository
from domain.receitas.schemas import AtualizarReceitaRequest, CriarReceitaRequest, ReceitaResponse
from domain.receitas.service import ReceitaService
from infrastructure.database.models import Usuario
from infrastructure.database.session import get_db

router = APIRouter(prefix="/receitas", tags=["Receitas"])


def get_receita_service(db: AsyncSession = Depends(get_db)) -> ReceitaService:
    return ReceitaService(ReceitaRepository(db), db)


@router.post("", response_model=ReceitaResponse, status_code=status.HTTP_201_CREATED)
async def criar_receita(
    data: CriarReceitaRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: ReceitaService = Depends(get_receita_service),
    db: AsyncSession = Depends(get_db),
) -> ReceitaResponse:
    """Cria uma nova receita com ingredientes e etapas. Retorna custo calculado."""
    result = await service.criar(tenant_id, data)
    await db.commit()
    return result


@router.get("", response_model=list[ReceitaResponse])
async def listar_receitas(
    tenant_id: UUID = Depends(get_tenant_id),
    service: ReceitaService = Depends(get_receita_service),
) -> list[ReceitaResponse]:
    """Lista todas as receitas do tenant com custo calculado."""
    return await service.listar(tenant_id)


@router.get("/{receita_id}", response_model=ReceitaResponse)
async def buscar_receita(
    receita_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: ReceitaService = Depends(get_receita_service),
) -> ReceitaResponse:
    """Retorna uma receita com custo detalhado."""
    return await service.buscar(receita_id, tenant_id)


@router.patch("/{receita_id}", response_model=ReceitaResponse)
async def atualizar_receita(
    receita_id: UUID,
    data: AtualizarReceitaRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: ReceitaService = Depends(get_receita_service),
    db: AsyncSession = Depends(get_db),
) -> ReceitaResponse:
    """Atualiza uma receita. Ingredientes/etapas substituem a lista inteira se enviados."""
    result = await service.atualizar(receita_id, tenant_id, data)
    await db.commit()
    return result


@router.delete("/{receita_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_receita(
    receita_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: ReceitaService = Depends(get_receita_service),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove uma receita (soft delete)."""
    await service.deletar(receita_id, tenant_id)
    await db.commit()
