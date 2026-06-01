from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_id
from domain.estoque.repository import EstoqueRepository
from domain.estoque.schemas import (
    AtualizarIngredienteRequest,
    CriarIngredienteRequest,
    EntradaEstoqueRequest,
    IngredienteResponse,
    MovimentacaoResponse,
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


@router.patch("/ingredientes/{ingrediente_id}", response_model=IngredienteResponse)
async def atualizar_ingrediente(
    ingrediente_id: UUID,
    data: AtualizarIngredienteRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: EstoqueService = Depends(get_estoque_service),
    db: AsyncSession = Depends(get_db),
) -> IngredienteResponse:
    """Atualiza dados descritivos do ingrediente. Estoque e custo continuam imutáveis aqui."""
    result = await service.atualizar_ingrediente(ingrediente_id, tenant_id, data)
    await db.commit()
    return result


@router.delete("/ingredientes/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_ingrediente(
    ingrediente_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: EstoqueService = Depends(get_estoque_service),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete. Bloqueia se ingrediente está em uso em alguma receita."""
    await service.deletar_ingrediente(ingrediente_id, tenant_id)
    await db.commit()


@router.get(
    "/ingredientes/{ingrediente_id}/movimentacoes",
    response_model=list[MovimentacaoResponse],
)
async def listar_movimentacoes(
    ingrediente_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant_id: UUID = Depends(get_tenant_id),
    service: EstoqueService = Depends(get_estoque_service),
) -> list[MovimentacaoResponse]:
    """Histórico de entradas/saídas do ingrediente, mais recente primeiro."""
    return await service.listar_movimentacoes(ingrediente_id, tenant_id, limit, offset)


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
