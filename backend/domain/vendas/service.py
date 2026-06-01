from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import structlog

from domain.estoque_pa.service import EstoquePAService
from domain.exceptions import (
    EstoquePAInsuficienteError,
    NotFoundError,
    ValidationError,
)
from domain.vendas.repository import VendasRepository
from domain.vendas.schemas import (
    CriarVendaRequest,
    VendaItemRequest,
    VendaItemResponse,
    VendaResponse,
)
from infrastructure.database.models import Venda

logger = structlog.get_logger(__name__)


def _to_response(v: Venda) -> VendaResponse:
    itens = [
        VendaItemResponse(
            id=it.id,
            receita_id=it.receita_id,
            nome_receita=it.receita.nome if it.receita else "(receita removida)",
            quantidade=it.quantidade,
            preco_unitario=it.preco_unitario,
            subtotal=(it.quantidade * it.preco_unitario).quantize(Decimal("0.01")),
            observacoes=it.observacoes,
        )
        for it in v.itens
    ]
    return VendaResponse(
        id=v.id,
        tenant_id=v.tenant_id,
        numero=v.numero,
        cliente_id=v.cliente_id,
        cliente_nome=v.cliente.nome if v.cliente else None,
        canal=v.canal,
        data_venda=v.data_venda,
        valor_total=v.valor_total,
        observacoes=v.observacoes,
        created_at=v.created_at,
        itens=itens,
    )


def _calcular_valor(itens: list[VendaItemRequest]) -> Decimal:
    total = sum((it.quantidade * it.preco_unitario for it in itens), Decimal("0"))
    return total.quantize(Decimal("0.01"))


class VendasService:
    """Serviço de Vendas — registra saídas multicanal e debita estoque PA."""

    def __init__(
        self, repo: VendasRepository, estoque_pa: EstoquePAService
    ) -> None:
        self._repo = repo
        self._estoque_pa = estoque_pa

    async def criar(self, tenant_id: UUID, data: CriarVendaRequest) -> VendaResponse:
        # Valida referências
        if data.cliente_id is not None:
            c = await self._repo.buscar_cliente(data.cliente_id, tenant_id)
            if not c:
                raise ValidationError(f"Cliente {data.cliente_id} não encontrado")
        for item in data.itens:
            r = await self._repo.buscar_receita(item.receita_id, tenant_id)
            if not r:
                raise ValidationError(f"Receita {item.receita_id} não encontrada")

        # Pré-valida saldo PA pra cada item ANTES de salvar a venda (atômico).
        # Se faltar saldo em qualquer item, raise antes de persistir nada.
        # Agrega quantidade por receita_id (mesma receita em múltiplos itens soma).
        necessidade: dict[UUID, Decimal] = {}
        for item in data.itens:
            necessidade[item.receita_id] = (
                necessidade.get(item.receita_id, Decimal("0")) + item.quantidade
            )
        for receita_id, qty in necessidade.items():
            saldo = await self._estoque_pa._repo.buscar_ou_criar(  # noqa: SLF001
                receita_id, tenant_id, for_update=True
            )
            if saldo.qtd_disponivel < qty:
                receita_nome = saldo.receita.nome if saldo.receita else "(receita)"
                raise EstoquePAInsuficienteError(
                    receita=receita_nome,
                    disponivel=float(saldo.qtd_disponivel),
                    necessario=float(qty),
                )

        valor_total = _calcular_valor(data.itens)
        venda = await self._repo.criar(tenant_id, data, valor_total)

        # Debita estoque PA (sabemos que tem saldo).
        for receita_id, qty in necessidade.items():
            await self._estoque_pa.debitar(
                receita_id=receita_id,
                tenant_id=tenant_id,
                quantidade=qty,
                origem=f"venda:{venda.numero}",
            )

        logger.info(
            "venda_criada",
            tenant_id=str(tenant_id),
            action="create",
            entity="venda",
            entity_id=str(venda.id),
            numero=venda.numero,
            canal=venda.canal,
        )
        return _to_response(venda)

    async def listar(
        self,
        tenant_id: UUID,
        canal: str | None = None,
        cliente_id: UUID | None = None,
        data_de: date | None = None,
        data_ate: date | None = None,
    ) -> list[VendaResponse]:
        vendas = await self._repo.listar(
            tenant_id, canal=canal, cliente_id=cliente_id, data_de=data_de, data_ate=data_ate
        )
        return [_to_response(v) for v in vendas]

    async def buscar(self, venda_id: UUID, tenant_id: UUID) -> VendaResponse:
        v = await self._repo.buscar_por_id(venda_id, tenant_id)
        if not v:
            raise NotFoundError("Venda", str(venda_id))
        return _to_response(v)

    async def cancelar(self, venda_id: UUID, tenant_id: UUID) -> None:
        """Cancela venda: estorna estoque PA e marca como deletada.

        Agrega itens por receita para estornar com uma única entrada por receita.
        """
        venda = await self._repo.buscar_por_id(venda_id, tenant_id)
        if not venda:
            raise NotFoundError("Venda", str(venda_id))

        estorno: dict[UUID, Decimal] = {}
        for it in venda.itens:
            estorno[it.receita_id] = estorno.get(it.receita_id, Decimal("0")) + it.quantidade
        for receita_id, qty in estorno.items():
            await self._estoque_pa.incrementar(
                receita_id=receita_id,
                tenant_id=tenant_id,
                quantidade=qty,
                origem=f"venda_cancelada:{venda.numero}",
            )

        await self._repo.soft_delete(venda)
        logger.info(
            "venda_cancelada",
            tenant_id=str(tenant_id),
            action="cancel",
            entity="venda",
            entity_id=str(venda_id),
            numero=venda.numero,
        )
