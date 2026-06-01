from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta
from uuid import UUID

import structlog

from domain.agenda.repository import AgendaRepository
from domain.agenda.schemas import (
    AgendaItemResponse,
    AtualizarAgendaItemRequest,
    CriarAgendaItemRequest,
    MoverAgendaItemRequest,
)
from domain.exceptions import NotFoundError, ValidationError
from infrastructure.database.models import AgendaItem

logger = structlog.get_logger(__name__)


def _duracao_minutos(hora_inicio: time | None, hora_fim: time | None) -> int | None:
    """Minutos entre início e fim no mesmo dia. None se não houver intervalo."""
    if hora_inicio is None or hora_fim is None:
        return None
    base = date(2000, 1, 1)
    delta = datetime.combine(base, hora_fim) - datetime.combine(base, hora_inicio)
    return int(delta.total_seconds() // 60)


def _nome_pedido(item: AgendaItem) -> str | None:
    if item.pedido is None:
        return None
    cliente = item.pedido.cliente.nome if item.pedido.cliente else "Sem cliente"
    return f"Pedido #{item.pedido.numero} - {cliente}"


def _to_response(item: AgendaItem) -> AgendaItemResponse:
    return AgendaItemResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        titulo=item.titulo,
        tipo=item.tipo,
        data=item.data,
        hora_inicio=item.hora_inicio,
        hora_fim=item.hora_fim,
        cor=item.cor,
        concluido=item.concluido,
        observacoes=item.observacoes,
        receita_id=item.receita_id,
        pedido_id=item.pedido_id,
        ordem_producao_id=item.ordem_producao_id,
        nome_receita=item.receita.nome if item.receita else None,
        nome_pedido=_nome_pedido(item),
        numero_op=item.ordem_producao.numero if item.ordem_producao else None,
        duracao_minutos=_duracao_minutos(item.hora_inicio, item.hora_fim),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _intervalo_semana(data_referencia: date) -> tuple[date, date]:
    """Segunda a domingo da semana que contém data_referencia.

    weekday(): segunda=0 ... domingo=6.
    """
    segunda = data_referencia - timedelta(days=data_referencia.weekday())
    domingo = segunda + timedelta(days=6)
    return segunda, domingo


def _intervalo_mes(ano: int, mes: int) -> tuple[date, date]:
    primeiro = date(ano, mes, 1)
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    ultimo = date(ano, mes, ultimo_dia)
    return primeiro, ultimo


class AgendaService:
    """Serviço da Agenda de Produção.

    Planejamento livre — não cria nem altera Receitas, Pedidos ou OPs; apenas
    referencia esses recursos (validando que pertencem ao tenant) para exibir
    rótulos cruzados na agenda. Sem efeito em estoque.
    """

    def __init__(self, repo: AgendaRepository) -> None:
        self._repo = repo

    # --------- Leitura por período ---------

    async def listar_semana(
        self, tenant_id: UUID, data_referencia: date
    ) -> list[AgendaItemResponse]:
        inicio, fim = _intervalo_semana(data_referencia)
        itens = await self._repo.listar_por_periodo(tenant_id, inicio, fim)
        return [_to_response(i) for i in itens]

    async def listar_mes(self, tenant_id: UUID, ano: int, mes: int) -> list[AgendaItemResponse]:
        if not 1 <= mes <= 12:
            raise ValidationError("Mês deve estar entre 1 e 12")
        inicio, fim = _intervalo_mes(ano, mes)
        itens = await self._repo.listar_por_periodo(tenant_id, inicio, fim)
        return [_to_response(i) for i in itens]

    async def listar_dia(self, tenant_id: UUID, data: date) -> list[AgendaItemResponse]:
        itens = await self._repo.listar_por_periodo(tenant_id, data, data)
        return [_to_response(i) for i in itens]

    # --------- Escrita ---------

    async def _validar_vinculos(self, tenant_id: UUID, dados: CriarAgendaItemRequest) -> None:
        if dados.tipo == "receita":
            if dados.receita_id is None:
                raise ValidationError("Selecione a receita para criar um item do tipo receita")
            if not await self._repo.receita_existe(tenant_id, dados.receita_id):
                raise ValidationError("Receita não encontrada")
        elif dados.tipo == "pedido":
            if dados.pedido_id is None:
                raise ValidationError("Selecione o pedido para criar um item do tipo pedido")
            if not await self._repo.pedido_existe(tenant_id, dados.pedido_id):
                raise ValidationError("Pedido não encontrado")
        elif dados.tipo == "tarefa":
            if dados.receita_id is not None or dados.pedido_id is not None:
                raise ValidationError("Uma tarefa não pode estar vinculada a uma receita ou pedido")

        # OP é vínculo de leitura cruzada opcional (qualquer tipo).
        if dados.ordem_producao_id is not None and not await self._repo.op_existe(
            tenant_id, dados.ordem_producao_id
        ):
            raise ValidationError("Ordem de produção não encontrada")

    async def criar_item(
        self, tenant_id: UUID, dados: CriarAgendaItemRequest
    ) -> AgendaItemResponse:
        await self._validar_vinculos(tenant_id, dados)
        item = await self._repo.criar(tenant_id, dados)
        logger.info(
            "agenda.item.criado",
            tenant_id=str(tenant_id),
            user_id=None,
            action="create",
            entity="agenda_item",
            entity_id=str(item.id),
            item_id=str(item.id),
            tipo=item.tipo,
            data=item.data.isoformat(),
        )
        return _to_response(item)

    async def atualizar_item(
        self, tenant_id: UUID, item_id: UUID, dados: AtualizarAgendaItemRequest
    ) -> AgendaItemResponse:
        item = await self._repo.buscar_por_id(tenant_id, item_id)
        if not item:
            raise NotFoundError("Item da agenda", str(item_id))

        # Valida vínculos se foram enviados.
        if dados.receita_id is not None and not await self._repo.receita_existe(
            tenant_id, dados.receita_id
        ):
            raise ValidationError("Receita não encontrada")
        if dados.pedido_id is not None and not await self._repo.pedido_existe(
            tenant_id, dados.pedido_id
        ):
            raise ValidationError("Pedido não encontrado")
        if dados.ordem_producao_id is not None and not await self._repo.op_existe(
            tenant_id, dados.ordem_producao_id
        ):
            raise ValidationError("Ordem de produção não encontrada")

        item = await self._repo.atualizar(item, dados)
        recarregado = await self._repo.buscar_por_id(tenant_id, item_id)
        assert recarregado is not None
        logger.info(
            "agenda.item.atualizado",
            tenant_id=str(tenant_id),
            action="update",
            entity="agenda_item",
            entity_id=str(item_id),
            item_id=str(item_id),
        )
        return _to_response(recarregado)

    async def marcar_concluido(
        self, tenant_id: UUID, item_id: UUID, concluido: bool
    ) -> AgendaItemResponse:
        item = await self._repo.buscar_por_id(tenant_id, item_id)
        if not item:
            raise NotFoundError("Item da agenda", str(item_id))
        await self._repo.marcar_concluido(item, concluido)
        # Recarrega: o flush expira updated_at (onupdate=now()) e relacionamentos
        # lazy não podem ser resolvidos fora do contexto async.
        recarregado = await self._repo.buscar_por_id(tenant_id, item_id)
        assert recarregado is not None
        logger.info(
            "agenda.item.concluido",
            tenant_id=str(tenant_id),
            action="conclude",
            entity="agenda_item",
            entity_id=str(item_id),
            item_id=str(item_id),
            concluido=concluido,
        )
        return _to_response(recarregado)

    async def mover_item(
        self,
        tenant_id: UUID,
        item_id: UUID,
        dados: MoverAgendaItemRequest,
    ) -> AgendaItemResponse:
        """Reposiciona o item (drag-and-drop): só data e horário."""
        item = await self._repo.buscar_por_id(tenant_id, item_id)
        if not item:
            raise NotFoundError("Item da agenda", str(item_id))

        data_anterior = item.data
        hora_anterior = item.hora_inicio
        item.data = dados.data
        item.hora_inicio = dados.hora_inicio
        item.hora_fim = dados.hora_fim
        await self._repo.atualizar(item, AtualizarAgendaItemRequest())
        # Recarrega: o flush expira updated_at (onupdate=now()) e relacionamentos
        # lazy não podem ser resolvidos fora do contexto async.
        recarregado = await self._repo.buscar_por_id(tenant_id, item_id)
        assert recarregado is not None

        logger.info(
            "agenda.item.movido",
            tenant_id=str(tenant_id),
            action="move",
            entity="agenda_item",
            entity_id=str(item_id),
            item_id=str(item_id),
            data_anterior=data_anterior.isoformat(),
            data_nova=dados.data.isoformat(),
            hora_anterior=hora_anterior.isoformat() if hora_anterior else None,
            hora_nova=dados.hora_inicio.isoformat() if dados.hora_inicio else None,
        )
        return _to_response(recarregado)

    async def deletar_item(self, tenant_id: UUID, item_id: UUID) -> None:
        item = await self._repo.buscar_por_id(tenant_id, item_id)
        if not item:
            raise NotFoundError("Item da agenda", str(item_id))
        await self._repo.deletar(item)
        logger.info(
            "agenda.item.deletado",
            tenant_id=str(tenant_id),
            action="delete",
            entity="agenda_item",
            entity_id=str(item_id),
            item_id=str(item_id),
        )
