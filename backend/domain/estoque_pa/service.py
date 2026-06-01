from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import structlog

from domain.estoque_pa.repository import EstoquePARepository
from domain.estoque_pa.schemas import (
    EstoquePAResponse,
    MovimentacaoEstoquePAResponse,
)
from domain.exceptions import EstoquePAInsuficienteError, NotFoundError
from infrastructure.database.models import EstoqueProdutoAcabado, Pedido

logger = structlog.get_logger(__name__)


def _status(eq: EstoqueProdutoAcabado) -> str:
    if eq.qtd_disponivel <= 0:
        return "zerado"
    if eq.qtd_minima > 0 and eq.qtd_disponivel <= eq.qtd_minima:
        return "baixo"
    return "ok"


def _to_response(eq: EstoqueProdutoAcabado) -> EstoquePAResponse:
    return EstoquePAResponse(
        receita_id=eq.receita_id,
        nome_receita=eq.receita.nome if eq.receita else "",
        qtd_disponivel=eq.qtd_disponivel,
        qtd_minima=eq.qtd_minima,
        status=_status(eq),
    )


class EstoquePAService:
    """Saldo de produto acabado por receita.

    Pontos de entrada (incrementar): Ordem de Produção finalizada.
    Pontos de saída (debitar): Venda criada, Pedido entregue.
    Cancelamentos estornam via incrementar.
    """

    def __init__(self, repo: EstoquePARepository) -> None:
        self._repo = repo

    async def incrementar(
        self,
        receita_id: UUID,
        tenant_id: UUID,
        quantidade: Decimal,
        origem: str,
    ) -> EstoqueProdutoAcabado:
        """Soma qtd ao saldo e registra movimentação 'entrada'."""
        if quantidade <= 0:
            return await self._repo.buscar_ou_criar(receita_id, tenant_id)

        saldo = await self._repo.buscar_ou_criar(receita_id, tenant_id)
        saldo.qtd_disponivel += quantidade
        await self._repo.salvar_movimentacao(
            receita_id=receita_id,
            tenant_id=tenant_id,
            tipo="entrada",
            quantidade=quantidade,
            origem=origem,
        )
        logger.info(
            "estoque_pa_entrada",
            tenant_id=str(tenant_id),
            action="entrada",
            entity="estoque_pa",
            entity_id=str(receita_id),
            quantidade=str(quantidade),
            origem=origem,
        )
        return saldo

    async def debitar(
        self,
        receita_id: UUID,
        tenant_id: UUID,
        quantidade: Decimal,
        origem: str,
    ) -> EstoqueProdutoAcabado:
        """Debita qtd do saldo. Raise EstoquePAInsuficienteError se faltar."""
        if quantidade <= 0:
            return await self._repo.buscar_ou_criar(receita_id, tenant_id)

        saldo = await self._repo.buscar_ou_criar(receita_id, tenant_id)
        if saldo.qtd_disponivel < quantidade:
            receita_nome = saldo.receita.nome if saldo.receita else "(receita)"
            raise EstoquePAInsuficienteError(
                receita=receita_nome,
                disponivel=float(saldo.qtd_disponivel),
                necessario=float(quantidade),
            )

        saldo.qtd_disponivel -= quantidade
        await self._repo.salvar_movimentacao(
            receita_id=receita_id,
            tenant_id=tenant_id,
            tipo="saida",
            quantidade=quantidade,
            origem=origem,
        )
        logger.info(
            "estoque_pa_saida",
            tenant_id=str(tenant_id),
            action="saida",
            entity="estoque_pa",
            entity_id=str(receita_id),
            quantidade=str(quantidade),
            origem=origem,
        )
        return saldo

    async def debitar_para_pedido(self, pedido: Pedido, tenant_id: UUID) -> None:
        """Debita estoque PA dos itens do pedido — atômico (valida tudo antes).

        Levanta EstoquePAInsuficienteError no primeiro item sem saldo, sem
        debitar nada. Útil pra transição 'aprovado → entregue'.
        """
        # Primeiro valida tudo
        for item in pedido.itens:
            saldo = await self._repo.buscar_ou_criar(item.receita_id, tenant_id)
            if saldo.qtd_disponivel < item.quantidade:
                receita_nome = saldo.receita.nome if saldo.receita else "(receita)"
                raise EstoquePAInsuficienteError(
                    receita=receita_nome,
                    disponivel=float(saldo.qtd_disponivel),
                    necessario=float(item.quantidade),
                )
        # Depois debita
        for item in pedido.itens:
            await self.debitar(
                receita_id=item.receita_id,
                tenant_id=tenant_id,
                quantidade=item.quantidade,
                origem=f"pedido:{pedido.numero}",
            )

    async def listar_saldos(self, tenant_id: UUID) -> list[EstoquePAResponse]:
        registros = await self._repo.listar(tenant_id)
        return [_to_response(r) for r in registros]

    async def buscar_saldo(
        self, receita_id: UUID, tenant_id: UUID
    ) -> EstoquePAResponse:
        receita = await self._repo.buscar_receita(receita_id, tenant_id)
        if not receita:
            raise NotFoundError("Receita", str(receita_id))
        saldo = await self._repo.buscar_ou_criar(receita_id, tenant_id)
        # Garante relacionamento carregado pro _to_response.
        if not saldo.receita:
            saldo.receita = receita  # type: ignore[assignment]
        return _to_response(saldo)

    async def atualizar_qtd_minima(
        self,
        receita_id: UUID,
        tenant_id: UUID,
        qtd_minima: Decimal,
    ) -> EstoquePAResponse:
        receita = await self._repo.buscar_receita(receita_id, tenant_id)
        if not receita:
            raise NotFoundError("Receita", str(receita_id))
        saldo = await self._repo.buscar_ou_criar(receita_id, tenant_id)
        saldo.qtd_minima = qtd_minima
        if not saldo.receita:
            saldo.receita = receita  # type: ignore[assignment]
        logger.info(
            "estoque_pa_minima_atualizada",
            tenant_id=str(tenant_id),
            action="update",
            entity="estoque_pa",
            entity_id=str(receita_id),
            qtd_minima=str(qtd_minima),
        )
        return _to_response(saldo)

    async def listar_movimentacoes(
        self,
        receita_id: UUID,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MovimentacaoEstoquePAResponse]:
        receita = await self._repo.buscar_receita(receita_id, tenant_id)
        if not receita:
            raise NotFoundError("Receita", str(receita_id))
        movs = await self._repo.listar_movimentacoes(receita_id, tenant_id, limit, offset)
        return [MovimentacaoEstoquePAResponse.model_validate(m) for m in movs]
