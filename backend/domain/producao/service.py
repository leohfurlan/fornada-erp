from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import structlog

from domain.estoque.repository import EstoqueRepository
from domain.estoque_pa.service import EstoquePAService
from domain.exceptions import (
    ConflictError,
    EstoqueInsuficienteError,
    NotFoundError,
    ValidationError,
)
from domain.producao.repository import ProducaoRepository
from domain.producao.schemas import (
    AtualizarOrdemProducaoRequest,
    CriarOrdemProducaoRequest,
    OrdemProducaoResponse,
)
from domain.producao.state_machine import (
    STATUS_CANCELADA,
    STATUS_DELETAVEIS,
    STATUS_EDITAVEIS,
    STATUS_EM_PRODUCAO,
    STATUS_FINALIZADA,
    pode_transicionar,
    proximas_transicoes,
)
from infrastructure.database.models import OrdemProducao, Receita

logger = structlog.get_logger(__name__)


def _to_response(op: OrdemProducao) -> OrdemProducaoResponse:
    return OrdemProducaoResponse(
        id=op.id,
        tenant_id=op.tenant_id,
        numero=op.numero,
        receita_id=op.receita_id,
        nome_receita=op.receita.nome if op.receita else "(receita removida)",
        receita_rendimento=op.receita.rendimento if op.receita else Decimal("1"),
        receita_rendimento_unidade=op.receita.rendimento_unidade if op.receita else "un",
        pedido_id=op.pedido_id,
        pedido_numero=op.pedido.numero if op.pedido else None,
        qtd_planejada=op.qtd_planejada,
        qtd_produzida=op.qtd_produzida,
        status=op.status,
        data_prevista=op.data_prevista,
        observacoes=op.observacoes,
        created_at=op.created_at,
        updated_at=op.updated_at,
        proximas_transicoes=sorted(proximas_transicoes(op.status)),
    )


class ProducaoService:
    """Serviço de Ordens de Produção.

    Centraliza a interface com estoque de ingredientes (reserva/baixa)
    e com estoque PA (entrada ao finalizar). Substitui a lógica que vivia
    em PedidosService na Sprint 2.
    """

    def __init__(
        self,
        repo: ProducaoRepository,
        estoque_ingredientes: EstoqueRepository,
        estoque_pa: EstoquePAService,
    ) -> None:
        self._repo = repo
        self._estoque_ing = estoque_ingredientes
        self._estoque_pa = estoque_pa

    async def criar(
        self, tenant_id: UUID, data: CriarOrdemProducaoRequest
    ) -> OrdemProducaoResponse:
        receita = await self._repo.buscar_receita(data.receita_id, tenant_id)
        if not receita:
            raise ValidationError(f"Receita {data.receita_id} não encontrada")
        if data.pedido_id is not None:
            pedido = await self._repo.buscar_pedido(data.pedido_id, tenant_id)
            if not pedido:
                raise ValidationError(f"Pedido {data.pedido_id} não encontrado")

        op = await self._repo.criar(tenant_id, data)
        logger.info(
            "op_criada",
            tenant_id=str(tenant_id),
            action="create",
            entity="op",
            entity_id=str(op.id),
            numero=op.numero,
            receita_id=str(op.receita_id),
        )
        return _to_response(op)

    async def listar(
        self,
        tenant_id: UUID,
        status: str | None = None,
        receita_id: UUID | None = None,
        pedido_id: UUID | None = None,
        data_de: date | None = None,
        data_ate: date | None = None,
    ) -> list[OrdemProducaoResponse]:
        ops = await self._repo.listar(
            tenant_id,
            status=status,
            receita_id=receita_id,
            pedido_id=pedido_id,
            data_de=data_de,
            data_ate=data_ate,
        )
        return [_to_response(op) for op in ops]

    async def buscar(self, op_id: UUID, tenant_id: UUID) -> OrdemProducaoResponse:
        op = await self._repo.buscar_por_id(op_id, tenant_id)
        if not op:
            raise NotFoundError("Ordem de Produção", str(op_id))
        return _to_response(op)

    async def atualizar(
        self, op_id: UUID, tenant_id: UUID, data: AtualizarOrdemProducaoRequest
    ) -> OrdemProducaoResponse:
        op = await self._repo.buscar_por_id(op_id, tenant_id)
        if not op:
            raise NotFoundError("Ordem de Produção", str(op_id))
        if op.status not in STATUS_EDITAVEIS:
            raise ConflictError(
                "Só é possível editar a OP enquanto está planejada. "
                "Status atual: " + op.status
            )
        # Validações se trocar receita ou pedido
        if data.receita_id is not None:
            r = await self._repo.buscar_receita(data.receita_id, tenant_id)
            if not r:
                raise ValidationError(f"Receita {data.receita_id} não encontrada")
        if data.pedido_id is not None:
            p = await self._repo.buscar_pedido(data.pedido_id, tenant_id)
            if not p:
                raise ValidationError(f"Pedido {data.pedido_id} não encontrado")

        await self._repo.atualizar_campos(op, data)
        recarregada = await self._repo.buscar_por_id(op_id, tenant_id)
        assert recarregada is not None
        logger.info(
            "op_atualizada",
            tenant_id=str(tenant_id),
            action="update",
            entity="op",
            entity_id=str(op_id),
        )
        return _to_response(recarregada)

    async def deletar(self, op_id: UUID, tenant_id: UUID) -> None:
        op = await self._repo.buscar_por_id(op_id, tenant_id)
        if not op:
            raise NotFoundError("Ordem de Produção", str(op_id))
        if op.status not in STATUS_DELETAVEIS:
            raise ConflictError(
                "Só é possível excluir OPs planejadas ou canceladas. "
                "Status atual: " + op.status
            )
        await self._repo.soft_delete(op)
        logger.info(
            "op_deletada",
            tenant_id=str(tenant_id),
            action="delete",
            entity="op",
            entity_id=str(op_id),
        )

    async def mudar_status(
        self,
        op_id: UUID,
        tenant_id: UUID,
        novo_status: str,
        qtd_produzida: Decimal | None = None,
    ) -> OrdemProducaoResponse:
        op = await self._repo.buscar_por_id(op_id, tenant_id)
        if not op:
            raise NotFoundError("Ordem de Produção", str(op_id))

        if not pode_transicionar(op.status, novo_status):
            raise ValidationError(
                f"Não é possível mudar a OP de '{op.status}' para '{novo_status}'."
            )

        de = op.status

        if novo_status == STATUS_FINALIZADA:
            if qtd_produzida is None:
                raise ValidationError(
                    "Informe a quantidade produzida ao finalizar a OP."
                )
            await self._consumir_e_produzir(op, tenant_id, qtd_produzida)
            op.qtd_produzida = qtd_produzida
        elif novo_status == STATUS_EM_PRODUCAO:
            await self._reservar_ingredientes(op, tenant_id)
        elif novo_status == STATUS_CANCELADA and de == STATUS_EM_PRODUCAO:
            await self._estornar_reserva(op, tenant_id)

        op.status = novo_status
        await self._repo._db.flush()  # noqa: SLF001

        logger.info(
            "op_status_alterada",
            tenant_id=str(tenant_id),
            action="status_change",
            entity="op",
            entity_id=str(op_id),
            de=de,
            para=novo_status,
            qtd_produzida=str(qtd_produzida) if qtd_produzida is not None else None,
        )

        recarregada = await self._repo.buscar_por_id(op_id, tenant_id)
        assert recarregada is not None
        return _to_response(recarregada)

    # --------- Efeitos colaterais ---------

    async def _reservar_ingredientes(
        self, op: OrdemProducao, tenant_id: UUID
    ) -> None:
        """Reserva (incrementa quantidade_reservada) dos ingredientes da receita.

        Necessário = ingrediente.quantidade × qtd_planejada da OP.
        Valida disponibilidade total antes de reservar (atômico).
        """
        receita = op.receita
        if receita is None or not receita.ingredientes:
            return  # receita sem ingredientes — nada a reservar

        # Valida tudo antes
        for ri in receita.ingredientes:
            ing = await self._estoque_ing.buscar_por_id(ri.ingrediente_id, tenant_id)
            if not ing:
                raise ValidationError(
                    f"Ingrediente {ri.ingrediente_id} não está mais no estoque."
                )
            necessario = ri.quantidade * op.qtd_planejada
            disponivel = ing.estoque_atual - ing.quantidade_reservada
            if disponivel < necessario:
                raise EstoqueInsuficienteError(
                    ingrediente=ing.nome,
                    disponivel=float(disponivel),
                    necessario=float(necessario),
                )
        # Reserva
        for ri in receita.ingredientes:
            ing = await self._estoque_ing.buscar_por_id(ri.ingrediente_id, tenant_id)
            assert ing is not None
            ing.quantidade_reservada += ri.quantidade * op.qtd_planejada

    async def _consumir_e_produzir(
        self,
        op: OrdemProducao,
        tenant_id: UUID,
        qtd_produzida: Decimal,
    ) -> None:
        """Debita ingredientes (qtd_planejada) e incrementa estoque PA (qtd_produzida).

        A receita consumiu o planejado (independente de quanto saiu), pois os
        ingredientes foram efetivamente usados. A entrada no estoque PA reflete
        a quantidade real produzida — eventual perda é capturada na diferença.
        """
        receita = op.receita
        if receita is None:
            raise ValidationError("Receita da OP não encontrada.")

        # Debita ingredientes (proporcional ao planejado).
        for ri in receita.ingredientes:
            ing = await self._estoque_ing.buscar_por_id(ri.ingrediente_id, tenant_id)
            if not ing:
                raise ValidationError(
                    f"Ingrediente {ri.ingrediente_id} não está mais no estoque."
                )
            consumido = ri.quantidade * op.qtd_planejada
            ing.estoque_atual -= consumido
            ing.quantidade_reservada = max(
                Decimal("0"), ing.quantidade_reservada - consumido
            )
            await self._estoque_ing.salvar_movimentacao(
                tenant_id=tenant_id,
                ingrediente_id=ri.ingrediente_id,
                tipo="saida",
                quantidade=consumido,
                custo_unitario=ing.custo_medio,
                origem=f"producao:{op.numero}",
            )

        # Soma estoque PA com qtd_produzida real (pode ser 0 = perda total).
        if qtd_produzida > 0:
            await self._estoque_pa.incrementar(
                receita_id=op.receita_id,
                tenant_id=tenant_id,
                quantidade=qtd_produzida,
                origem=f"op:{op.numero}",
            )

    async def _estornar_reserva(
        self, op: OrdemProducao, tenant_id: UUID
    ) -> None:
        """Devolve quantidade_reservada quando OP em produção é cancelada."""
        receita = op.receita
        if receita is None:
            return
        for ri in receita.ingredientes:
            ing = await self._estoque_ing.buscar_por_id(ri.ingrediente_id, tenant_id)
            if not ing:
                continue
            ing.quantidade_reservada = max(
                Decimal("0"), ing.quantidade_reservada - ri.quantidade * op.qtd_planejada
            )
