from decimal import Decimal
from uuid import UUID

import structlog

from domain.exceptions import NotFoundError, ValidationError
from domain.receitas.calculos import (
    ConfiguracaoCustoCalculo,
    ItemIngredienteCalculo,
    calcular_custo_total,
    calcular_preco_recomendado,
    minutos_para_horas,
)
from domain.receitas.repository import ReceitaRepository
from domain.receitas.schemas import (
    AtualizarReceitaRequest,
    CriarReceitaRequest,
    CustoDetalhadoResponse,
    IngredienteReceitaResponse,
    ReceitaResponse,
)
from infrastructure.database.models import ConfiguracaoCusto, Receita, ReceitaIngrediente
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class ReceitaService:
    def __init__(self, repo: ReceitaRepository, db: AsyncSession) -> None:
        self._repo = repo
        self._db = db

    async def criar(self, tenant_id: UUID, data: CriarReceitaRequest) -> ReceitaResponse:
        """Cria receita e retorna com custo já calculado."""
        for item in data.ingredientes:
            ingrediente = await self._repo.buscar_ingrediente(item.ingrediente_id, tenant_id)
            if not ingrediente:
                raise ValidationError(
                    f"Ingrediente {item.ingrediente_id} não encontrado no estoque"
                )

        receita = await self._repo.criar(tenant_id, data)

        logger.info(
            "receita_criada",
            tenant_id=str(tenant_id),
            action="create",
            entity="receita",
            entity_id=str(receita.id),
        )

        return await self._montar_response(receita, tenant_id)

    async def buscar(self, receita_id: UUID, tenant_id: UUID) -> ReceitaResponse:
        receita = await self._repo.buscar_por_id(receita_id, tenant_id)
        if not receita:
            raise NotFoundError("Receita", str(receita_id))
        return await self._montar_response(receita, tenant_id)

    async def listar(self, tenant_id: UUID) -> list[ReceitaResponse]:
        receitas = await self._repo.listar(tenant_id)
        return [await self._montar_response(r, tenant_id) for r in receitas]

    async def atualizar(
        self, receita_id: UUID, tenant_id: UUID, data: AtualizarReceitaRequest
    ) -> ReceitaResponse:
        """Atualiza receita. Ingredientes/etapas substituem a lista inteira se enviados."""
        receita = await self._repo.buscar_por_id(receita_id, tenant_id)
        if not receita:
            raise NotFoundError("Receita", str(receita_id))

        # Valida ingredientes pertencem ao tenant
        if data.ingredientes is not None:
            for item in data.ingredientes:
                ingrediente = await self._repo.buscar_ingrediente(item.ingrediente_id, tenant_id)
                if not ingrediente:
                    raise ValidationError(
                        f"Ingrediente {item.ingrediente_id} não encontrado no estoque"
                    )

        campos_simples = {
            "nome": data.nome,
            "categoria": data.categoria,
            "rendimento": data.rendimento,
            "rendimento_unidade": data.rendimento_unidade,
            "margem_desejada": data.margem_desejada,
            "modo_preparo": data.modo_preparo,
        }

        await self._repo.atualizar(
            receita,
            campos_simples=campos_simples,
            ingredientes=data.ingredientes,
            etapas=data.etapas,
        )

        # Recarrega com relationships atualizados
        receita = await self._repo.buscar_por_id(receita_id, tenant_id)
        if not receita:
            raise NotFoundError("Receita", str(receita_id))

        logger.info(
            "receita_atualizada",
            tenant_id=str(tenant_id),
            action="update",
            entity="receita",
            entity_id=str(receita_id),
        )
        return await self._montar_response(receita, tenant_id)

    async def deletar(self, receita_id: UUID, tenant_id: UUID) -> None:
        receita = await self._repo.buscar_por_id(receita_id, tenant_id)
        if not receita:
            raise NotFoundError("Receita", str(receita_id))
        await self._repo.deletar(receita)

        logger.info(
            "receita_deletada",
            tenant_id=str(tenant_id),
            action="delete",
            entity="receita",
            entity_id=str(receita_id),
        )

    async def _montar_response(self, receita: Receita, tenant_id: UUID) -> ReceitaResponse:
        """Monta o response completo com custo calculado."""
        config = await self._buscar_config(tenant_id)
        usuario = await self._buscar_valor_hora(tenant_id)

        itens_calculo = [
            ItemIngredienteCalculo(
                nome=ri.ingrediente.nome,
                quantidade=ri.quantidade,
                custo_medio_por_unidade=ri.ingrediente.custo_medio,
            )
            for ri in receita.ingredientes
            if ri.ingrediente
        ]

        tempo_total_min = sum(e.duracao_minutos for e in receita.etapas)
        tempo_ativo_min = sum(
            e.duracao_minutos for e in receita.etapas if e.tipo_mao_obra == "direta"
        )

        custo = calcular_custo_total(
            ingredientes=itens_calculo,
            config=config,
            tempo_ativo_horas=minutos_para_horas(tempo_ativo_min),
            tempo_total_horas=minutos_para_horas(tempo_total_min),
            valor_hora=usuario,
            rendimento=receita.rendimento,
        )
        preco_recomendado = calcular_preco_recomendado(custo.custo_por_unidade, receita.margem_desejada)

        ingredientes_resp = [
            IngredienteReceitaResponse(
                id=ri.id,
                ingrediente_id=ri.ingrediente_id,
                nome_ingrediente=ri.ingrediente.nome if ri.ingrediente else "",
                quantidade=ri.quantidade,
                unidade=ri.unidade,
                custo_total=(ri.quantidade * ri.ingrediente.custo_medio).quantize(Decimal("0.01"))
                if ri.ingrediente
                else Decimal("0"),
            )
            for ri in receita.ingredientes
        ]

        custo_resp = CustoDetalhadoResponse(
            custo_ingredientes=custo.custo_ingredientes,
            custo_operacional=custo.custo_operacional,
            custo_mao_obra_direta=custo.custo_mao_obra_direta,
            custo_total=custo.custo_total,
            custo_por_unidade=custo.custo_por_unidade,
            preco_minimo=custo.preco_minimo,
            preco_recomendado=preco_recomendado,
            tempo_total_minutos=tempo_total_min,
            tempo_ativo_minutos=tempo_ativo_min,
        )

        return ReceitaResponse(
            id=receita.id,
            tenant_id=receita.tenant_id,
            nome=receita.nome,
            categoria=receita.categoria,
            rendimento=receita.rendimento,
            rendimento_unidade=receita.rendimento_unidade,
            margem_desejada=receita.margem_desejada,
            modo_preparo=receita.modo_preparo,
            foto_url=receita.foto_url,
            created_at=receita.created_at,
            updated_at=receita.updated_at,
            ingredientes=ingredientes_resp,
            etapas=[e for e in receita.etapas],
            custo=custo_resp,
        )

    async def _buscar_config(self, tenant_id: UUID) -> ConfiguracaoCustoCalculo:
        result = await self._db.execute(
            select(ConfiguracaoCusto).where(
                ConfiguracaoCusto.tenant_id == tenant_id,
                ConfiguracaoCusto.deleted_at.is_(None),
            )
        )
        config = result.scalar_one_or_none()
        if config:
            return ConfiguracaoCustoCalculo(
                custo_operacional_mensal=config.custo_operacional_mensal,
                horas_mensais=config.horas_mensais,
            )
        return ConfiguracaoCustoCalculo(
            custo_operacional_mensal=Decimal("0"),
            horas_mensais=Decimal("160"),
        )

    async def _buscar_valor_hora(self, tenant_id: UUID) -> Decimal:
        from infrastructure.database.models import Usuario

        result = await self._db.execute(
            select(Usuario.valor_hora).where(
                Usuario.tenant_id == tenant_id,
                Usuario.deleted_at.is_(None),
                Usuario.ativo.is_(True),
            ).limit(1)
        )
        valor = result.scalar_one_or_none()
        return valor or Decimal("0")
