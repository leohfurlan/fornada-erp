from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.vendas.schemas import CriarVendaRequest
from infrastructure.database.models import (
    Cliente,
    Receita,
    Venda,
    VendaItem,
)


class VendasRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _proximo_numero(self, tenant_id: UUID) -> int:
        result = await self._db.execute(
            select(func.coalesce(func.max(Venda.numero), 0)).where(
                Venda.tenant_id == tenant_id
            )
        )
        return int(result.scalar() or 0) + 1

    async def criar(
        self,
        tenant_id: UUID,
        data: CriarVendaRequest,
        valor_total: Decimal,
    ) -> Venda:
        numero = await self._proximo_numero(tenant_id)
        venda = Venda(
            tenant_id=tenant_id,
            numero=numero,
            cliente_id=data.cliente_id,
            canal=data.canal,
            data_venda=data.data_venda or datetime.now(UTC),
            valor_total=valor_total,
            observacoes=data.observacoes,
        )
        self._db.add(venda)
        await self._db.flush()
        for item in data.itens:
            self._db.add(
                VendaItem(
                    tenant_id=tenant_id,
                    venda_id=venda.id,
                    receita_id=item.receita_id,
                    quantidade=item.quantidade,
                    preco_unitario=item.preco_unitario,
                    observacoes=item.observacoes,
                )
            )
        await self._db.flush()
        recarregada = await self.buscar_por_id(venda.id, tenant_id)
        assert recarregada is not None
        return recarregada

    async def buscar_por_id(self, venda_id: UUID, tenant_id: UUID) -> Venda | None:
        result = await self._db.execute(
            select(Venda)
            .options(
                selectinload(Venda.cliente),
                selectinload(Venda.itens).selectinload(VendaItem.receita),
            )
            .where(
                Venda.id == venda_id,
                Venda.tenant_id == tenant_id,
                Venda.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def listar(
        self,
        tenant_id: UUID,
        canal: str | None = None,
        cliente_id: UUID | None = None,
        data_de: date | None = None,
        data_ate: date | None = None,
    ) -> list[Venda]:
        stmt = (
            select(Venda)
            .options(
                selectinload(Venda.cliente),
                selectinload(Venda.itens).selectinload(VendaItem.receita),
            )
            .where(Venda.tenant_id == tenant_id, Venda.deleted_at.is_(None))
        )
        if canal:
            stmt = stmt.where(Venda.canal == canal)
        if cliente_id:
            stmt = stmt.where(Venda.cliente_id == cliente_id)
        if data_de:
            stmt = stmt.where(Venda.data_venda >= data_de)
        if data_ate:
            stmt = stmt.where(Venda.data_venda <= data_ate)
        stmt = stmt.order_by(desc(Venda.data_venda))
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete(self, venda: Venda) -> None:
        venda.deleted_at = datetime.now(UTC)
        await self._db.flush()

    async def buscar_receita(self, receita_id: UUID, tenant_id: UUID) -> Receita | None:
        result = await self._db.execute(
            select(Receita).where(
                Receita.id == receita_id,
                Receita.tenant_id == tenant_id,
                Receita.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def buscar_cliente(self, cliente_id: UUID, tenant_id: UUID) -> Cliente | None:
        result = await self._db.execute(
            select(Cliente).where(
                Cliente.id == cliente_id,
                Cliente.tenant_id == tenant_id,
                Cliente.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
