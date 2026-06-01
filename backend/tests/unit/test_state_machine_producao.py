"""Testes da máquina de estados de OP."""

import pytest

from domain.producao.state_machine import (
    STATUS_CANCELADA,
    STATUS_EM_PRODUCAO,
    STATUS_FINALIZADA,
    STATUS_PLANEJADA,
    pode_transicionar,
    proximas_transicoes,
)


class TestTransicoesValidas:
    def test_planejada_pode_iniciar(self) -> None:
        assert pode_transicionar(STATUS_PLANEJADA, STATUS_EM_PRODUCAO)

    def test_planejada_pode_cancelar(self) -> None:
        assert pode_transicionar(STATUS_PLANEJADA, STATUS_CANCELADA)

    def test_em_producao_pode_finalizar(self) -> None:
        assert pode_transicionar(STATUS_EM_PRODUCAO, STATUS_FINALIZADA)

    def test_em_producao_pode_cancelar(self) -> None:
        assert pode_transicionar(STATUS_EM_PRODUCAO, STATUS_CANCELADA)


class TestTransicoesInvalidas:
    def test_nao_pode_pular_planejada_para_finalizada(self) -> None:
        # Tem que reservar ingredientes (em_producao) antes de debitar.
        assert not pode_transicionar(STATUS_PLANEJADA, STATUS_FINALIZADA)

    def test_finalizada_eh_terminal(self) -> None:
        assert proximas_transicoes(STATUS_FINALIZADA) == frozenset()

    def test_cancelada_eh_terminal(self) -> None:
        assert proximas_transicoes(STATUS_CANCELADA) == frozenset()

    def test_status_desconhecido(self) -> None:
        assert proximas_transicoes("foo") == frozenset()


class TestProximas:
    @pytest.mark.parametrize(
        "status,esperado",
        [
            (STATUS_PLANEJADA, {STATUS_EM_PRODUCAO, STATUS_CANCELADA}),
            (STATUS_EM_PRODUCAO, {STATUS_FINALIZADA, STATUS_CANCELADA}),
            (STATUS_FINALIZADA, set()),
            (STATUS_CANCELADA, set()),
        ],
    )
    def test_conjunto(self, status: str, esperado: set[str]) -> None:
        assert proximas_transicoes(status) == frozenset(esperado)
