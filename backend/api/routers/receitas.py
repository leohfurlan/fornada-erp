from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_id
from domain.receitas.repository import ReceitaRepository
from domain.receitas.schemas import AtualizarReceitaRequest, CriarReceitaRequest, ReceitaResponse
from domain.receitas.service import ReceitaService
from domain.receitas.ficha_tecnica import FichaTecnicaInput, FichaTecnicaResponse, ConsumoComponente
from domain.receitas.ficha_service import FichaTecnicaService
from infrastructure.database.session import get_db

router = APIRouter(prefix="/receitas", tags=["Receitas"])


@router.get("/{receita_id}/consumo-composicao", response_model=list[ConsumoComponente])
async def consumo_composicao(receita_id: UUID, tenant_id: UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_db)) -> list[ConsumoComponente]:
    """Consumo consolidado por fornada, calculado a partir da composição salva."""
    from domain.producao.ficha import montar_snapshot
    from domain.exceptions import NotFoundError
    repo = ReceitaRepository(db)
    receita = await repo.buscar_por_id(receita_id, tenant_id)
    if not receita:
        raise NotFoundError("Receita")
    snapshot = await montar_snapshot(receita, repo, tenant_id)
    return [ConsumoComponente(**linha) for linha in snapshot["consumo"]]


@router.get("/{receita_id}/ficha-tecnica", response_model=FichaTecnicaResponse)
async def buscar_ficha_tecnica(
    receita_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FichaTecnicaResponse:
    """Consulta ficha de montagem exclusivamente do tenant autenticado."""
    return await FichaTecnicaService(db).buscar(receita_id, tenant_id)


@router.put("/{receita_id}/ficha-tecnica", response_model=FichaTecnicaResponse)
async def salvar_ficha_tecnica(
    receita_id: UUID,
    data: FichaTecnicaInput,
    tenant_id: UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FichaTecnicaResponse:
    """Salva ficha sem sobrescrever revisão alterada por outra sessão."""
    result = await FichaTecnicaService(db).salvar(receita_id, tenant_id, data)
    await db.commit()
    return result


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


@router.post(
    "/{receita_id}/duplicar",
    response_model=ReceitaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicar_receita(
    receita_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: ReceitaService = Depends(get_receita_service),
    db: AsyncSession = Depends(get_db),
) -> ReceitaResponse:
    """Duplica uma receita com nome sufixado, ingredientes e etapas idênticos."""
    result = await service.duplicar(receita_id, tenant_id)
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
