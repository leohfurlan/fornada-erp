from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_id
from domain.estoque.repository import EstoqueRepository
from domain.estoque.schemas import (
    CriarIngredienteRequest,
    EntradaEstoqueRequest,
    IngredienteResponse,
)
from domain.estoque.service import EstoqueService
from infrastructure.database.session import get_db

router = APIRouter(prefix="/estoque", tags=["Estoque"])


def get_estoque_service(db: AsyncSession = Depends(get_db)) -> EstoqueService:
    return EstoqueService(EstoqueRepository(db))


@router.post(
    "/ingredientes", response_model=IngredienteResponse, status_code=status.HTTP_201_CREATED
)
async def criar_ingrediente(
    data: CriarIngredienteRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: EstoqueService = Depends(get_estoque_service),
    db: AsyncSession = Depends(get_db),
) -> IngredienteResponse:
    """Cadastra um novo ingrediente no estoque."""
    result = await service.criar_ingrediente(tenant_id, data)
    await db.commit()
    return result


@router.get("/ingredientes", response_model=list[IngredienteResponse])
async def listar_ingredientes(
    tenant_id: UUID = Depends(get_tenant_id),
    service: EstoqueService = Depends(get_estoque_service),
) -> list[IngredienteResponse]:
    """Lista todos os ingredientes com status de estoque."""
    return await service.listar(tenant_id)


@router.get("/ingredientes/{ingrediente_id}", response_model=IngredienteResponse)
async def buscar_ingrediente(
    ingrediente_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: EstoqueService = Depends(get_estoque_service),
) -> IngredienteResponse:
    return await service.buscar(ingrediente_id, tenant_id)


@router.post("/entrada", response_model=IngredienteResponse)
async def registrar_entrada(
    data: EntradaEstoqueRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: EstoqueService = Depends(get_estoque_service),
    db: AsyncSession = Depends(get_db),
) -> IngredienteResponse:
    """Registra entrada de ingrediente (compra) e recalcula custo médio."""
    result = await service.registrar_entrada(tenant_id, data)
    await db.commit()
    return result
