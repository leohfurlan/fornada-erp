from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.dashboard.schemas import AlertaEstoque, DashboardResumoResponse
from infrastructure.database.models import Ingrediente, OrdemProducao, Pedido, Venda

logger = structlog.get_logger(__name__)

TZ_BR = ZoneInfo("America/Sao_Paulo")

# Ordem de criticidade para ordenação dos alertas (menor = mais urgente).
_CRITICIDADE = {"zerado": 0, "critico": 1, "baixo": 2}


def _hoje_br() -> date:
    """Data corrente no fuso de São Paulo (referência do negócio)."""
    return datetime.now(TZ_BR).date()


def _status_estoque(estoque_atual: Decimal, reservada: Decimal, minimo: Decimal) -> str:
    """Classifica o estoque de um ingrediente. Espelha domain.estoque.service."""
    saldo = estoque_atual - reservada
    if saldo <= 0:
        return "zerado"
    if minimo > 0:
        ratio = saldo / minimo
        if ratio <= Decimal("0.5"):
            return "critico"
        if ratio <= Decimal("1"):
            return "baixo"
    return "ok"


class DashboardService:
    """Resumo agregado do dia para a home. Queries diretas, sem repository."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def resumo(self, tenant_id: UUID) -> DashboardResumoResponse:
        hoje = _hoje_br()
        segunda = hoje - timedelta(days=hoje.weekday())
        domingo = segunda + timedelta(days=6)

        faturamento, total_vendas = await self._faturamento_semana(tenant_id, segunda, domingo)
        pedidos_em_aberto = await self._pedidos_em_aberto(tenant_id)
        ops_hoje = await self._ops_hoje(tenant_id, hoje)
        ops_em_producao = await self._ops_em_producao(tenant_id)
        alertas, total_criticos = await self._alertas_estoque(tenant_id)

        logger.info(
            "dashboard.resumo.consultado",
            tenant_id=str(tenant_id),
            action="read",
            entity="dashboard",
        )

        return DashboardResumoResponse(
            faturamento_semana=faturamento,
            # TODO: calcular lucro real via join receitas.custo × vendas
            lucro_estimado_semana=None,
            total_vendas_semana=total_vendas,
            pedidos_em_aberto=pedidos_em_aberto,
            ops_hoje=ops_hoje,
            ops_em_producao=ops_em_producao,
            alertas_estoque=alertas,
            total_ingredientes_criticos=total_criticos,
        )

    async def _faturamento_semana(
        self, tenant_id: UUID, segunda: date, domingo: date
    ) -> tuple[Decimal, int]:
        # data_venda é timestamptz — converte para a data local antes de comparar.
        data_local = func.date(func.timezone("America/Sao_Paulo", Venda.data_venda))
        stmt = select(
            func.coalesce(func.sum(Venda.valor_total), 0),
            func.count(Venda.id),
        ).where(
            Venda.tenant_id == tenant_id,
            Venda.deleted_at.is_(None),
            data_local.between(segunda, domingo),
        )
        total, qtd = (await self._db.execute(stmt)).one()
        return Decimal(total), int(qtd)

    async def _pedidos_em_aberto(self, tenant_id: UUID) -> int:
        stmt = select(func.count(Pedido.id)).where(
            Pedido.tenant_id == tenant_id,
            Pedido.deleted_at.is_(None),
            Pedido.status.in_(("orcamento", "aprovado")),
        )
        return int((await self._db.execute(stmt)).scalar_one())

    async def _ops_hoje(self, tenant_id: UUID, hoje: date) -> int:
        stmt = select(func.count(OrdemProducao.id)).where(
            OrdemProducao.tenant_id == tenant_id,
            OrdemProducao.deleted_at.is_(None),
            OrdemProducao.data_prevista == hoje,
            OrdemProducao.status.in_(("planejada", "em_producao")),
        )
        return int((await self._db.execute(stmt)).scalar_one())

    async def _ops_em_producao(self, tenant_id: UUID) -> int:
        stmt = select(func.count(OrdemProducao.id)).where(
            OrdemProducao.tenant_id == tenant_id,
            OrdemProducao.deleted_at.is_(None),
            OrdemProducao.status == "em_producao",
        )
        return int((await self._db.execute(stmt)).scalar_one())

    async def _alertas_estoque(self, tenant_id: UUID) -> tuple[list[AlertaEstoque], int]:
        # Pré-filtra no banco os candidatos a alerta (zerado ou abaixo do mínimo);
        # a classificação fina (baixo/critico/zerado) é feita em Python para
        # reaproveitar exatamente a regra de domain.estoque.service.
        saldo = Ingrediente.estoque_atual - Ingrediente.quantidade_reservada
        stmt = select(Ingrediente).where(
            Ingrediente.tenant_id == tenant_id,
            Ingrediente.deleted_at.is_(None),
            (saldo <= 0) | ((Ingrediente.estoque_minimo > 0) & (saldo <= Ingrediente.estoque_minimo)),
        )
        ingredientes = (await self._db.execute(stmt)).scalars().all()

        alertas: list[AlertaEstoque] = []
        total_criticos = 0
        for ing in ingredientes:
            status = _status_estoque(
                ing.estoque_atual, ing.quantidade_reservada, ing.estoque_minimo
            )
            if status == "ok":
                continue
            if status in ("critico", "zerado"):
                total_criticos += 1
            alertas.append(
                AlertaEstoque(
                    ingrediente_id=ing.id,
                    nome=ing.nome,
                    estoque_atual=ing.estoque_atual - ing.quantidade_reservada,
                    estoque_minimo=ing.estoque_minimo,
                    unidade=ing.unidade,
                    status=status,
                )
            )

        alertas.sort(key=lambda a: (_CRITICIDADE.get(a.status, 9), a.nome))
        return alertas[:5], total_criticos
