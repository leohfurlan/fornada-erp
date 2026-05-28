from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_id
from domain.configuracoes.repository import ConfiguracoesRepository
from domain.configuracoes.schemas import (
    AtualizarEtapaPadraoRequest,
    ConfiguracaoCustoRequest,
    ConfiguracaoCustoResponse,
    CriarEtapaPadraoRequest,
    EtapaPadraoResponse,
)
from domain.exceptions import NotFoundError
from infrastructure.database.session import get_db

router = APIRouter(prefix="/configuracoes", tags=["Configurações"])


def get_repo(db: AsyncSession = Depends(get_db)) -> ConfiguracoesRepository:
    return ConfiguracoesRepository(db)


# -------- Etapas padrão --------


@router.get("/etapas", response_model=list[EtapaPadraoResponse])
async def listar_etapas(
    tenant_id: UUID = Depends(get_tenant_id),
    repo: ConfiguracoesRepository = Depends(get_repo),
) -> list[EtapaPadraoResponse]:
    """Lista etapas pré-cadastradas para reutilizar em receitas."""
    etapas = await repo.listar_etapas(tenant_id)
    return [EtapaPadraoResponse.model_validate(e) for e in etapas]


@router.post("/etapas", response_model=EtapaPadraoResponse, status_code=status.HTTP_201_CREATED)
async def criar_etapa(
    data: CriarEtapaPadraoRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    repo: ConfiguracoesRepository = Depends(get_repo),
    db: AsyncSession = Depends(get_db),
) -> EtapaPadraoResponse:
    """Cadastra uma etapa padrão (mão de obra direta ou indireta)."""
    etapa = await repo.criar_etapa(tenant_id, data)
    await db.commit()
    return EtapaPadraoResponse.model_validate(etapa)


@router.patch("/etapas/{etapa_id}", response_model=EtapaPadraoResponse)
async def atualizar_etapa(
    etapa_id: UUID,
    data: AtualizarEtapaPadraoRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    repo: ConfiguracoesRepository = Depends(get_repo),
    db: AsyncSession = Depends(get_db),
) -> EtapaPadraoResponse:
    etapa = await repo.buscar_etapa(etapa_id, tenant_id)
    if not etapa:
        raise NotFoundError("Etapa padrão", str(etapa_id))
    for campo, valor in data.model_dump(exclude_unset=True).items():
        if valor is not None:
            setattr(etapa, campo, valor)
    await db.commit()
    return EtapaPadraoResponse.model_validate(etapa)


@router.delete("/etapas/{etapa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_etapa(
    etapa_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    repo: ConfiguracoesRepository = Depends(get_repo),
    db: AsyncSession = Depends(get_db),
) -> None:
    from datetime import datetime

    etapa = await repo.buscar_etapa(etapa_id, tenant_id)
    if not etapa:
        raise NotFoundError("Etapa padrão", str(etapa_id))
    etapa.deleted_at = datetime.utcnow()
    await db.commit()


# -------- Configuração de custo + valor/hora --------


@router.get("/custos", response_model=ConfiguracaoCustoResponse)
async def buscar_configuracao_custos(
    tenant_id: UUID = Depends(get_tenant_id),
    repo: ConfiguracoesRepository = Depends(get_repo),
) -> ConfiguracaoCustoResponse:
    """Retorna a configuração de custo operacional, horas mensais e valor/hora."""
    config = await repo.buscar_config(tenant_id)
    usuario = await repo.buscar_usuario_por_tenant(tenant_id)

    custo_mensal = config.custo_operacional_mensal if config else Decimal("0")
    horas = config.horas_mensais if config else Decimal("160")
    valor_hora = usuario.valor_hora if usuario else Decimal("0")
    custo_por_hora = (custo_mensal / horas) if horas > 0 else Decimal("0")

    return ConfiguracaoCustoResponse(
        custo_operacional_mensal=custo_mensal,
        horas_mensais=horas,
        valor_hora=valor_hora,
        custo_por_hora=custo_por_hora.quantize(Decimal("0.01")),
    )


@router.put("/custos", response_model=ConfiguracaoCustoResponse)
async def atualizar_configuracao_custos(
    data: ConfiguracaoCustoRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    repo: ConfiguracoesRepository = Depends(get_repo),
    db: AsyncSession = Depends(get_db),
) -> ConfiguracaoCustoResponse:
    """Atualiza custo operacional mensal, horas mensais e valor/hora da confeiteira."""
    await repo.upsert_config(
        tenant_id=tenant_id,
        custo_operacional_mensal=data.custo_operacional_mensal,
        horas_mensais=data.horas_mensais,
    )
    usuario = await repo.buscar_usuario_por_tenant(tenant_id)
    if usuario:
        usuario.valor_hora = data.valor_hora
    await db.commit()

    custo_por_hora = (
        data.custo_operacional_mensal / data.horas_mensais if data.horas_mensais > 0 else Decimal("0")
    )
    return ConfiguracaoCustoResponse(
        custo_operacional_mensal=data.custo_operacional_mensal,
        horas_mensais=data.horas_mensais,
        valor_hora=data.valor_hora,
        custo_por_hora=custo_por_hora.quantize(Decimal("0.01")),
    )
