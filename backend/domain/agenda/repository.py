from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from domain.agenda.schemas import (
    AtualizarAgendaItemRequest,
    CriarAgendaItemRequest,
)
from infrastructure.database.models import (
    AgendaItem,
    OrdemProducao,
    Pedido,
    Receita,
)


class AgendaRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # --------- Verificação de vínculos (leitura cruzada, escopo do tenant) ---------

    async def receita_existe(self, tenant_id: UUID, receita_id: UUID) -> bool:
        result = await self._db.execute(
            select(Receita.id).where(
                Receita.id == receita_id,
                Receita.tenant_id == tenant_id,
                Receita.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none() is not None

    async def pedido_existe(self, tenant_id: UUID, pedido_id: UUID) -> bool:
        result = await self._db.execute(
            select(Pedido.id).where(
                Pedido.id == pedido_id,
                Pedido.tenant_id == tenant_id,
                Pedido.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none() is not None

    async def op_existe(self, tenant_id: UUID, op_id: UUID) -> bool:
        result = await self._db.execute(
            select(OrdemProducao.id).where(
                OrdemProducao.id == op_id,
                OrdemProducao.tenant_id == tenant_id,
                OrdemProducao.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none() is not None

    async def listar_por_periodo(
        self,
        tenant_id: UUID,
        data_inicio: date,
        data_fim: date,
    ) -> list[AgendaItem]:
        """Itens do tenant cuja data está no intervalo [data_inicio, data_fim].

        Ordena por data e, dentro do dia, por hora_inicio com itens de dia
        inteiro (hora_inicio NULL) por último.
        """
        stmt = (
            select(AgendaItem)
            .options(
                joinedload(AgendaItem.receita),
                joinedload(AgendaItem.pedido).joinedload(Pedido.cliente),
                joinedload(AgendaItem.ordem_producao),
            )
            .where(
                AgendaItem.tenant_id == tenant_id,
                AgendaItem.data >= data_inicio,
                AgendaItem.data <= data_fim,
                AgendaItem.deleted_at.is_(None),
            )
            .order_by(
                AgendaItem.data.asc(),
                AgendaItem.hora_inicio.asc().nullslast(),
            )
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def buscar_por_id(self, tenant_id: UUID, item_id: UUID) -> AgendaItem | None:
        result = await self._db.execute(
            select(AgendaItem)
            .options(
                joinedload(AgendaItem.receita),
                joinedload(AgendaItem.pedido).joinedload(Pedido.cliente),
                joinedload(AgendaItem.ordem_producao),
            )
            .where(
                AgendaItem.id == item_id,
                AgendaItem.tenant_id == tenant_id,
                AgendaItem.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def criar(self, tenant_id: UUID, dados: CriarAgendaItemRequest) -> AgendaItem:
        item = AgendaItem(
            tenant_id=tenant_id,
            titulo=dados.titulo,
            tipo=dados.tipo,
            data=dados.data,
            hora_inicio=dados.hora_inicio,
            hora_fim=dados.hora_fim,
            cor=dados.cor,
            observacoes=dados.observacoes,
            receita_id=dados.receita_id,
            pedido_id=dados.pedido_id,
            ordem_producao_id=dados.ordem_producao_id,
            concluido=False,
        )
        self._db.add(item)
        await self._db.flush()
        recarregado = await self.buscar_por_id(tenant_id, item.id)
        assert recarregado is not None
        return recarregado

    async def atualizar(self, item: AgendaItem, dados: AtualizarAgendaItemRequest) -> AgendaItem:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(item, campo, valor)
        await self._db.flush()
        return item

    async def marcar_concluido(self, item: AgendaItem, concluido: bool) -> AgendaItem:
        item.concluido = concluido
        await self._db.flush()
        return item

    async def deletar(self, item: AgendaItem) -> None:
        item.deleted_at = datetime.now(UTC)
        await self._db.flush()
