from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.configuracoes.schemas import CriarEtapaPadraoRequest
from infrastructure.database.models import ConfiguracaoCusto, EtapaPadrao, Usuario


class ConfiguracoesRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # -------- Etapas padrão --------

    async def listar_etapas(self, tenant_id: UUID) -> list[EtapaPadrao]:
        result = await self._db.execute(
            select(EtapaPadrao)
            .where(EtapaPadrao.tenant_id == tenant_id, EtapaPadrao.deleted_at.is_(None))
            .order_by(EtapaPadrao.tipo_mao_obra, EtapaPadrao.nome)
        )
        return list(result.scalars().all())

    async def buscar_etapa(self, etapa_id: UUID, tenant_id: UUID) -> EtapaPadrao | None:
        result = await self._db.execute(
            select(EtapaPadrao).where(
                EtapaPadrao.id == etapa_id,
                EtapaPadrao.tenant_id == tenant_id,
                EtapaPadrao.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def criar_etapa(self, tenant_id: UUID, data: CriarEtapaPadraoRequest) -> EtapaPadrao:
        etapa = EtapaPadrao(
            tenant_id=tenant_id,
            nome=data.nome,
            tipo_mao_obra=data.tipo_mao_obra,
            duracao_minutos_default=data.duracao_minutos_default,
        )
        self._db.add(etapa)
        await self._db.flush()
        return etapa

    # -------- Configuração de custo --------

    async def buscar_config(self, tenant_id: UUID) -> ConfiguracaoCusto | None:
        result = await self._db.execute(
            select(ConfiguracaoCusto).where(
                ConfiguracaoCusto.tenant_id == tenant_id,
                ConfiguracaoCusto.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def upsert_config(
        self, tenant_id: UUID, custo_operacional_mensal, horas_mensais
    ) -> ConfiguracaoCusto:
        config = await self.buscar_config(tenant_id)
        if config:
            config.custo_operacional_mensal = custo_operacional_mensal
            config.horas_mensais = horas_mensais
        else:
            config = ConfiguracaoCusto(
                tenant_id=tenant_id,
                custo_operacional_mensal=custo_operacional_mensal,
                horas_mensais=horas_mensais,
            )
            self._db.add(config)
        await self._db.flush()
        return config

    # -------- Usuário (valor/hora) --------

    async def buscar_usuario_por_tenant(self, tenant_id: UUID) -> Usuario | None:
        result = await self._db.execute(
            select(Usuario)
            .where(
                Usuario.tenant_id == tenant_id,
                Usuario.deleted_at.is_(None),
                Usuario.ativo.is_(True),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
