from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import structlog

from domain.estoque_pa.service import EstoquePAService
from domain.exceptions import ConflictError, NotFoundError, ValidationError
from domain.pedidos.repository import PedidosRepository
from domain.pedidos.schemas import (
    AtualizarClienteRequest,
    AtualizarPedidoRequest,
    ClienteResponse,
    CriarClienteRequest,
    CriarPedidoRequest,
    PedidoItemRequest,
    PedidoItemResponse,
    PedidoResponse,
)
from domain.pedidos.state_machine import (
    STATUS_DELETAVEIS,
    STATUS_EDITAVEIS,
    STATUS_ENTREGUE,
    pode_transicionar,
    proximas_transicoes,
)
from infrastructure.database.models import Cliente, Pedido

logger = structlog.get_logger(__name__)


def _cliente_to_response(c: Cliente) -> ClienteResponse:
    return ClienteResponse.model_validate(c)


def _pedido_to_response(p: Pedido) -> PedidoResponse:
    itens = [
        PedidoItemResponse(
            id=it.id,
            receita_id=it.receita_id,
            nome_receita=it.receita.nome if it.receita else "(receita removida)",
            quantidade=it.quantidade,
            preco_unitario=it.preco_unitario,
            subtotal=(it.quantidade * it.preco_unitario).quantize(Decimal("0.01")),
            observacoes=it.observacoes,
        )
        for it in p.itens
    ]
    return PedidoResponse(
        id=p.id,
        tenant_id=p.tenant_id,
        numero=p.numero,
        cliente_id=p.cliente_id,
        cliente_nome=p.cliente.nome if p.cliente else None,
        status=p.status,
        data_entrega=p.data_entrega,
        valor_total=p.valor_total,
        observacoes=p.observacoes,
        foto_referencia_url=p.foto_referencia_url,
        created_at=p.created_at,
        updated_at=p.updated_at,
        itens=itens,
        proximas_transicoes=sorted(proximas_transicoes(p.status)),
    )


def _calcular_valor_total(itens: list[PedidoItemRequest]) -> Decimal:
    total = sum((it.quantidade * it.preco_unitario for it in itens), Decimal("0"))
    return total.quantize(Decimal("0.01"))


class PedidosService:
    """Serviço de pedidos (encomendas).

    Sprint 3: pedido NÃO mexe mais em ingredientes. Apenas registra a
    encomenda e, ao "entregue", debita o estoque de produto acabado.
    Quem produz é a Ordem de Produção (domínio separado).
    """

    def __init__(self, repo: PedidosRepository, estoque_pa: EstoquePAService) -> None:
        self._repo = repo
        self._estoque_pa = estoque_pa

    # --------- Clientes ---------

    async def criar_cliente(
        self, tenant_id: UUID, data: CriarClienteRequest
    ) -> ClienteResponse:
        cliente = await self._repo.criar_cliente(tenant_id, data)
        logger.info(
            "cliente_criado",
            tenant_id=str(tenant_id),
            action="create",
            entity="cliente",
            entity_id=str(cliente.id),
        )
        return _cliente_to_response(cliente)

    async def listar_clientes(self, tenant_id: UUID) -> list[ClienteResponse]:
        clientes = await self._repo.listar_clientes(tenant_id)
        return [_cliente_to_response(c) for c in clientes]

    async def buscar_cliente(self, cliente_id: UUID, tenant_id: UUID) -> ClienteResponse:
        c = await self._repo.buscar_cliente(cliente_id, tenant_id)
        if not c:
            raise NotFoundError("Cliente", str(cliente_id))
        return _cliente_to_response(c)

    async def atualizar_cliente(
        self, cliente_id: UUID, tenant_id: UUID, data: AtualizarClienteRequest
    ) -> ClienteResponse:
        c = await self._repo.buscar_cliente(cliente_id, tenant_id)
        if not c:
            raise NotFoundError("Cliente", str(cliente_id))
        await self._repo.atualizar_cliente(c, data)
        logger.info(
            "cliente_atualizado",
            tenant_id=str(tenant_id),
            action="update",
            entity="cliente",
            entity_id=str(cliente_id),
        )
        return _cliente_to_response(c)

    async def deletar_cliente(self, cliente_id: UUID, tenant_id: UUID) -> None:
        c = await self._repo.buscar_cliente(cliente_id, tenant_id)
        if not c:
            raise NotFoundError("Cliente", str(cliente_id))
        await self._repo.deletar_cliente(c)
        logger.info(
            "cliente_deletado",
            tenant_id=str(tenant_id),
            action="delete",
            entity="cliente",
            entity_id=str(cliente_id),
        )

    # --------- Pedidos ---------

    async def criar_pedido(
        self, tenant_id: UUID, data: CriarPedidoRequest
    ) -> PedidoResponse:
        await self._validar_referencias(tenant_id, data.cliente_id, data.itens)

        valor_total = _calcular_valor_total(data.itens)
        pedido = await self._repo.criar_pedido(tenant_id, data, valor_total)

        logger.info(
            "pedido_criado",
            tenant_id=str(tenant_id),
            action="create",
            entity="pedido",
            entity_id=str(pedido.id),
            numero=pedido.numero,
        )
        return _pedido_to_response(pedido)

    async def listar_pedidos(
        self,
        tenant_id: UUID,
        status: str | None = None,
        cliente_id: UUID | None = None,
        data_de=None,
        data_ate=None,
    ) -> list[PedidoResponse]:
        pedidos = await self._repo.listar_pedidos(
            tenant_id, status=status, cliente_id=cliente_id, data_de=data_de, data_ate=data_ate
        )
        return [_pedido_to_response(p) for p in pedidos]

    async def buscar_pedido(self, pedido_id: UUID, tenant_id: UUID) -> PedidoResponse:
        p = await self._repo.buscar_pedido_por_id(pedido_id, tenant_id)
        if not p:
            raise NotFoundError("Pedido", str(pedido_id))
        return _pedido_to_response(p)

    async def atualizar_pedido(
        self, pedido_id: UUID, tenant_id: UUID, data: AtualizarPedidoRequest
    ) -> PedidoResponse:
        pedido = await self._repo.buscar_pedido_por_id(pedido_id, tenant_id)
        if not pedido:
            raise NotFoundError("Pedido", str(pedido_id))
        if pedido.status not in STATUS_EDITAVEIS:
            raise ConflictError(
                "Pedidos só podem ser editados enquanto estão em orçamento. "
                "Status atual: " + pedido.status
            )

        await self._validar_referencias(tenant_id, data.cliente_id, data.itens)

        if data.cliente_id is not None:
            pedido.cliente_id = data.cliente_id
        if data.data_entrega is not None:
            pedido.data_entrega = data.data_entrega
        if data.observacoes is not None:
            pedido.observacoes = data.observacoes
        if data.foto_referencia_url is not None:
            pedido.foto_referencia_url = data.foto_referencia_url

        if data.itens is not None:
            await self._repo.substituir_itens(pedido, data.itens, tenant_id)
            pedido.valor_total = _calcular_valor_total(data.itens)

        recarregado = await self._repo.buscar_pedido_por_id(pedido_id, tenant_id)
        assert recarregado is not None

        logger.info(
            "pedido_atualizado",
            tenant_id=str(tenant_id),
            action="update",
            entity="pedido",
            entity_id=str(pedido_id),
        )
        return _pedido_to_response(recarregado)

    async def deletar_pedido(self, pedido_id: UUID, tenant_id: UUID) -> None:
        pedido = await self._repo.buscar_pedido_por_id(pedido_id, tenant_id)
        if not pedido:
            raise NotFoundError("Pedido", str(pedido_id))
        if pedido.status not in STATUS_DELETAVEIS:
            raise ConflictError(
                "Só é possível excluir pedidos em orçamento ou cancelados. "
                "Status atual: " + pedido.status
            )
        await self._repo.soft_delete_pedido(pedido)
        logger.info(
            "pedido_deletado",
            tenant_id=str(tenant_id),
            action="delete",
            entity="pedido",
            entity_id=str(pedido_id),
        )

    async def mudar_status(
        self, pedido_id: UUID, tenant_id: UUID, novo_status: str
    ) -> PedidoResponse:
        pedido = await self._repo.buscar_pedido_por_id(pedido_id, tenant_id)
        if not pedido:
            raise NotFoundError("Pedido", str(pedido_id))

        if not pode_transicionar(pedido.status, novo_status):
            raise ValidationError(
                f"Não é possível mudar de '{pedido.status}' para '{novo_status}'."
            )

        de = pedido.status
        # Single side effect remaining: ao entregar, debita estoque PA.
        # Atômico (valida tudo antes); se faltar saldo, raise antes de mexer.
        if novo_status == STATUS_ENTREGUE:
            await self._estoque_pa.debitar_para_pedido(pedido, tenant_id)

        pedido.status = novo_status
        await self._repo._db.flush()  # noqa: SLF001

        logger.info(
            "pedido_status_alterado",
            tenant_id=str(tenant_id),
            action="status_change",
            entity="pedido",
            entity_id=str(pedido_id),
            de=de,
            para=novo_status,
        )

        recarregado = await self._repo.buscar_pedido_por_id(pedido_id, tenant_id)
        assert recarregado is not None
        return _pedido_to_response(recarregado)

    # --------- Validações ---------

    async def _validar_referencias(
        self,
        tenant_id: UUID,
        cliente_id: UUID | None,
        itens: list[PedidoItemRequest] | None,
    ) -> None:
        if cliente_id is not None:
            c = await self._repo.buscar_cliente(cliente_id, tenant_id)
            if not c:
                raise ValidationError(f"Cliente {cliente_id} não encontrado")
        if itens is not None:
            for item in itens:
                receita = await self._repo.buscar_receita(item.receita_id, tenant_id)
                if not receita:
                    raise ValidationError(
                        f"Receita {item.receita_id} não encontrada"
                    )
