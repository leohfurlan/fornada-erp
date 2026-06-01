from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.pedidos.schemas import (
    AtualizarClienteRequest,
    CriarClienteRequest,
    CriarPedidoRequest,
    PedidoItemRequest,
)
from infrastructure.database.models import Cliente, Pedido, PedidoItem, Receita


class PedidosRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # --------- Clientes ---------

    async def criar_cliente(self, tenant_id: UUID, data: CriarClienteRequest) -> Cliente:
        cliente = Cliente(
            tenant_id=tenant_id,
            nome=data.nome,
            telefone=data.telefone,
            observacoes=data.observacoes,
        )
        self._db.add(cliente)
        await self._db.flush()
        return cliente

    async def buscar_cliente(self, cliente_id: UUID, tenant_id: UUID) -> Cliente | None:
        result = await self._db.execute(
            select(Cliente).where(
                Cliente.id == cliente_id,
                Cliente.tenant_id == tenant_id,
                Cliente.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def listar_clientes(self, tenant_id: UUID) -> list[Cliente]:
        result = await self._db.execute(
            select(Cliente)
            .where(Cliente.tenant_id == tenant_id, Cliente.deleted_at.is_(None))
            .order_by(Cliente.nome)
        )
        return list(result.scalars().all())

    async def atualizar_cliente(
        self, cliente: Cliente, data: AtualizarClienteRequest
    ) -> Cliente:
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(cliente, campo, valor)
        await self._db.flush()
        return cliente

    async def deletar_cliente(self, cliente: Cliente) -> None:
        cliente.deleted_at = datetime.now(UTC)
        await self._db.flush()

    # --------- Pedidos ---------

    async def _proximo_numero(self, tenant_id: UUID) -> int:
        result = await self._db.execute(
            select(func.coalesce(func.max(Pedido.numero), 0)).where(
                Pedido.tenant_id == tenant_id
            )
        )
        return int(result.scalar() or 0) + 1

    async def criar_pedido(
        self, tenant_id: UUID, data: CriarPedidoRequest, valor_total: Decimal
    ) -> Pedido:
        numero = await self._proximo_numero(tenant_id)
        pedido = Pedido(
            tenant_id=tenant_id,
            numero=numero,
            cliente_id=data.cliente_id,
            status="orcamento",
            data_entrega=data.data_entrega,
            valor_total=valor_total,
            observacoes=data.observacoes,
            foto_referencia_url=data.foto_referencia_url,
        )
        self._db.add(pedido)
        await self._db.flush()

        for item in data.itens:
            self._db.add(
                PedidoItem(
                    tenant_id=tenant_id,
                    pedido_id=pedido.id,
                    receita_id=item.receita_id,
                    quantidade=item.quantidade,
                    preco_unitario=item.preco_unitario,
                    observacoes=item.observacoes,
                )
            )
        await self._db.flush()
        recarregado = await self.buscar_pedido_por_id(pedido.id, tenant_id)
        assert recarregado is not None
        return recarregado

    async def buscar_pedido_por_id(self, pedido_id: UUID, tenant_id: UUID) -> Pedido | None:
        result = await self._db.execute(
            select(Pedido)
            .options(
                selectinload(Pedido.cliente),
                selectinload(Pedido.itens).selectinload(PedidoItem.receita),
            )
            .where(
                Pedido.id == pedido_id,
                Pedido.tenant_id == tenant_id,
                Pedido.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def listar_pedidos(
        self,
        tenant_id: UUID,
        status: str | None = None,
        cliente_id: UUID | None = None,
        data_de: date | None = None,
        data_ate: date | None = None,
    ) -> list[Pedido]:
        stmt = (
            select(Pedido)
            .options(
                selectinload(Pedido.cliente),
                selectinload(Pedido.itens).selectinload(PedidoItem.receita),
            )
            .where(Pedido.tenant_id == tenant_id, Pedido.deleted_at.is_(None))
        )
        if status:
            stmt = stmt.where(Pedido.status == status)
        if cliente_id:
            stmt = stmt.where(Pedido.cliente_id == cliente_id)
        if data_de:
            stmt = stmt.where(Pedido.data_entrega >= data_de)
        if data_ate:
            stmt = stmt.where(Pedido.data_entrega <= data_ate)
        stmt = stmt.order_by(desc(Pedido.created_at))
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def substituir_itens(
        self, pedido: Pedido, itens: list[PedidoItemRequest], tenant_id: UUID
    ) -> None:
        for it in list(pedido.itens):
            await self._db.delete(it)
        await self._db.flush()
        for item in itens:
            self._db.add(
                PedidoItem(
                    tenant_id=tenant_id,
                    pedido_id=pedido.id,
                    receita_id=item.receita_id,
                    quantidade=item.quantidade,
                    preco_unitario=item.preco_unitario,
                    observacoes=item.observacoes,
                )
            )
        await self._db.flush()

    async def soft_delete_pedido(self, pedido: Pedido) -> None:
        pedido.deleted_at = datetime.now(UTC)
        await self._db.flush()

    async def buscar_receita(self, receita_id: UUID, tenant_id: UUID) -> Receita | None:
        result = await self._db.execute(
            select(Receita)
            .options(selectinload(Receita.ingredientes))
            .where(
                Receita.id == receita_id,
                Receita.tenant_id == tenant_id,
                Receita.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
