from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.producao.schemas import (
    AtualizarOrdemProducaoRequest,
    CriarOrdemProducaoRequest,
)
from infrastructure.database.models import (
    OrdemProducao,
    Pedido,
    Receita,
    ReceitaIngrediente,
)


class ProducaoRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _proximo_numero(self, tenant_id: UUID) -> int:
        result = await self._db.execute(
            select(func.coalesce(func.max(OrdemProducao.numero), 0)).where(
                OrdemProducao.tenant_id == tenant_id
            )
        )
        return int(result.scalar() or 0) + 1

    async def criar(
        self, tenant_id: UUID, data: CriarOrdemProducaoRequest
    ) -> OrdemProducao:
        numero = await self._proximo_numero(tenant_id)
        op = OrdemProducao(
            tenant_id=tenant_id,
            numero=numero,
            receita_id=data.receita_id,
            pedido_id=data.pedido_id,
            qtd_planejada=data.qtd_planejada,
            status="planejada",
            data_prevista=data.data_prevista,
            observacoes=data.observacoes,
        )
        self._db.add(op)
        await self._db.flush()
        recarregada = await self.buscar_por_id(op.id, tenant_id)
        assert recarregada is not None
        return recarregada

    async def buscar_por_id(
        self, op_id: UUID, tenant_id: UUID
    ) -> OrdemProducao | None:
        result = await self._db.execute(
            select(OrdemProducao)
            .options(
                selectinload(OrdemProducao.receita).selectinload(
                    Receita.ingredientes
                ).selectinload(ReceitaIngrediente.ingrediente),
                selectinload(OrdemProducao.pedido),
            )
            .where(
                OrdemProducao.id == op_id,
                OrdemProducao.tenant_id == tenant_id,
                OrdemProducao.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def listar(
        self,
        tenant_id: UUID,
        status: str | None = None,
        receita_id: UUID | None = None,
        pedido_id: UUID | None = None,
        data_de: date | None = None,
        data_ate: date | None = None,
    ) -> list[OrdemProducao]:
        stmt = (
            select(OrdemProducao)
            .options(
                selectinload(OrdemProducao.receita),
                selectinload(OrdemProducao.pedido),
            )
            .where(
                OrdemProducao.tenant_id == tenant_id,
                OrdemProducao.deleted_at.is_(None),
            )
        )
        if status:
            stmt = stmt.where(OrdemProducao.status == status)
        if receita_id:
            stmt = stmt.where(OrdemProducao.receita_id == receita_id)
        if pedido_id:
            stmt = stmt.where(OrdemProducao.pedido_id == pedido_id)
        if data_de:
            stmt = stmt.where(OrdemProducao.data_prevista >= data_de)
        if data_ate:
            stmt = stmt.where(OrdemProducao.data_prevista <= data_ate)
        # Ordena: planejadas primeiro (por data_prevista), depois em produção, depois finalizadas (recentes primeiro).
        stmt = stmt.order_by(
            OrdemProducao.status,
            OrdemProducao.data_prevista.nullslast(),
            desc(OrdemProducao.created_at),
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def atualizar_campos(
        self, op: OrdemProducao, data: AtualizarOrdemProducaoRequest
    ) -> OrdemProducao:
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(op, campo, valor)
        await self._db.flush()
        return op

    async def soft_delete(self, op: OrdemProducao) -> None:
        op.deleted_at = datetime.now(UTC)
        await self._db.flush()

    async def buscar_receita(
        self, receita_id: UUID, tenant_id: UUID
    ) -> Receita | None:
        result = await self._db.execute(
            select(Receita)
            .options(
                selectinload(Receita.ingredientes).selectinload(
                    ReceitaIngrediente.ingrediente
                )
            )
            .where(
                Receita.id == receita_id,
                Receita.tenant_id == tenant_id,
                Receita.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def buscar_pedido(
        self, pedido_id: UUID, tenant_id: UUID
    ) -> Pedido | None:
        result = await self._db.execute(
            select(Pedido).where(
                Pedido.id == pedido_id,
                Pedido.tenant_id == tenant_id,
                Pedido.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
