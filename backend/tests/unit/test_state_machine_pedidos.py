"""Testes da máquina de estados de pedidos (Sprint 3 — simplificada).

Sprint 3 removeu os status intermediários `em_producao` e `finalizado` do
fluxo de Pedido — quem produz é a Ordem de Produção. Pedido agora vai
direto de `aprovado` para `entregue`.
"""

import pytest

from domain.pedidos.state_machine import (
    STATUS_APROVADO,
    STATUS_CANCELADO,
    STATUS_EM_PRODUCAO,
    STATUS_ENTREGUE,
    STATUS_FINALIZADO,
    STATUS_ORCAMENTO,
    pode_transicionar,
    proximas_transicoes,
)


class TestTransicoesValidas:
    def test_orcamento_pode_ir_para_aprovado(self) -> None:
        assert pode_transicionar(STATUS_ORCAMENTO, STATUS_APROVADO)

    def test_orcamento_pode_ir_para_cancelado(self) -> None:
        assert pode_transicionar(STATUS_ORCAMENTO, STATUS_CANCELADO)

    def test_aprovado_pode_ir_para_entregue(self) -> None:
        # Sprint 3: pedido vai direto pra entregue (produção é responsabilidade da OP).
        assert pode_transicionar(STATUS_APROVADO, STATUS_ENTREGUE)

    def test_aprovado_pode_ir_para_cancelado(self) -> None:
        assert pode_transicionar(STATUS_APROVADO, STATUS_CANCELADO)


class TestTransicoesInvalidas:
    def test_em_producao_nao_eh_alcancavel(self) -> None:
        # Status legado — não está mais no grafo de transições.
        assert not pode_transicionar(STATUS_ORCAMENTO, STATUS_EM_PRODUCAO)
        assert not pode_transicionar(STATUS_APROVADO, STATUS_EM_PRODUCAO)

    def test_finalizado_nao_eh_alcancavel(self) -> None:
        assert not pode_transicionar(STATUS_APROVADO, STATUS_FINALIZADO)

    def test_orcamento_nao_pula_para_entregue(self) -> None:
        # Tem que passar por aprovado primeiro.
        assert not pode_transicionar(STATUS_ORCAMENTO, STATUS_ENTREGUE)

    def test_nao_pode_voltar_de_aprovado_para_orcamento(self) -> None:
        assert not pode_transicionar(STATUS_APROVADO, STATUS_ORCAMENTO)

    def test_entregue_eh_terminal(self) -> None:
        assert proximas_transicoes(STATUS_ENTREGUE) == frozenset()

    def test_cancelado_eh_terminal(self) -> None:
        assert proximas_transicoes(STATUS_CANCELADO) == frozenset()

    def test_status_legado_eh_terminal(self) -> None:
        # Pedidos pré-refator que ficaram nesses status não conseguem mais transicionar.
        assert proximas_transicoes(STATUS_EM_PRODUCAO) == frozenset()
        assert proximas_transicoes(STATUS_FINALIZADO) == frozenset()

    def test_status_desconhecido_nao_transiciona(self) -> None:
        assert proximas_transicoes("foo") == frozenset()
        assert not pode_transicionar("foo", "aprovado")


class TestProximasTransicoes:
    @pytest.mark.parametrize(
        "status,esperado",
        [
            (STATUS_ORCAMENTO, {STATUS_APROVADO, STATUS_CANCELADO}),
            (STATUS_APROVADO, {STATUS_ENTREGUE, STATUS_CANCELADO}),
            (STATUS_ENTREGUE, set()),
            (STATUS_CANCELADO, set()),
        ],
    )
    def test_conjunto_de_transicoes(self, status: str, esperado: set[str]) -> None:
        assert proximas_transicoes(status) == frozenset(esperado)
