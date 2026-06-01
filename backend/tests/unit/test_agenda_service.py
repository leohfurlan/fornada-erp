"""Testes unitários da Agenda de Produção.

Cobrem lógica pura (cálculo de intervalos, duração, validação de cor) e as
regras de vínculo do service usando um repositório fake (sem banco).
"""

from datetime import date, time
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from domain.agenda.schemas import CriarAgendaItemRequest
from domain.agenda.service import (
    AgendaService,
    _duracao_minutos,
    _intervalo_mes,
    _intervalo_semana,
)
from domain.exceptions import ValidationError


class FakeRepo:
    """Repositório fake — só responde às verificações de vínculo."""

    def __init__(self, receita_ok: bool = True, pedido_ok: bool = True, op_ok: bool = True) -> None:
        self._receita_ok = receita_ok
        self._pedido_ok = pedido_ok
        self._op_ok = op_ok

    async def receita_existe(self, tenant_id, receita_id) -> bool:
        return self._receita_ok

    async def pedido_existe(self, tenant_id, pedido_id) -> bool:
        return self._pedido_ok

    async def op_existe(self, tenant_id, op_id) -> bool:
        return self._op_ok


class TestIntervaloSemana:
    def test_quarta_resulta_segunda_a_domingo(self) -> None:
        # 2026-06-03 é uma quarta-feira.
        inicio, fim = _intervalo_semana(date(2026, 6, 3))
        assert inicio == date(2026, 6, 1)  # segunda
        assert fim == date(2026, 6, 7)  # domingo

    def test_segunda_eh_o_proprio_inicio(self) -> None:
        inicio, fim = _intervalo_semana(date(2026, 6, 1))  # segunda
        assert inicio == date(2026, 6, 1)
        assert fim == date(2026, 6, 7)

    def test_domingo_fecha_a_semana(self) -> None:
        inicio, fim = _intervalo_semana(date(2026, 6, 7))  # domingo
        assert inicio == date(2026, 6, 1)
        assert fim == date(2026, 6, 7)


class TestIntervaloMes:
    def test_junho_tem_30_dias(self) -> None:
        inicio, fim = _intervalo_mes(2026, 6)
        assert inicio == date(2026, 6, 1)
        assert fim == date(2026, 6, 30)

    def test_fevereiro_bissexto(self) -> None:
        inicio, fim = _intervalo_mes(2028, 2)
        assert fim == date(2028, 2, 29)


class TestDuracaoMinutos:
    def test_intervalo_de_90_minutos(self) -> None:
        assert _duracao_minutos(time(8, 0), time(9, 30)) == 90

    def test_sem_horario_retorna_none(self) -> None:
        assert _duracao_minutos(None, None) is None
        assert _duracao_minutos(time(8, 0), None) is None


class TestValidacaoCorHex:
    def test_cor_valida(self) -> None:
        req = CriarAgendaItemRequest(
            titulo="x", tipo="tarefa", data=date(2026, 6, 1), cor="#f97316"
        )
        assert req.cor == "#f97316"

    def test_cor_invalida_levanta(self) -> None:
        with pytest.raises(PydanticValidationError):
            CriarAgendaItemRequest(titulo="x", tipo="tarefa", data=date(2026, 6, 1), cor="laranja")

    def test_hora_fim_antes_do_inicio_levanta(self) -> None:
        with pytest.raises(PydanticValidationError):
            CriarAgendaItemRequest(
                titulo="x",
                tipo="tarefa",
                data=date(2026, 6, 1),
                hora_inicio=time(10, 0),
                hora_fim=time(9, 0),
            )


@pytest.mark.asyncio
class TestValidacaoVinculos:
    async def test_receita_sem_receita_id_levanta(self) -> None:
        service = AgendaService(FakeRepo())  # type: ignore[arg-type]
        dados = CriarAgendaItemRequest(titulo="Bolo", tipo="receita", data=date(2026, 6, 1))
        with pytest.raises(ValidationError):
            await service._validar_vinculos(uuid4(), dados)

    async def test_tarefa_com_receita_id_levanta(self) -> None:
        service = AgendaService(FakeRepo())  # type: ignore[arg-type]
        dados = CriarAgendaItemRequest(
            titulo="Lavar louça",
            tipo="tarefa",
            data=date(2026, 6, 1),
            receita_id=uuid4(),
        )
        with pytest.raises(ValidationError):
            await service._validar_vinculos(uuid4(), dados)

    async def test_pedido_sem_pedido_id_levanta(self) -> None:
        service = AgendaService(FakeRepo())  # type: ignore[arg-type]
        dados = CriarAgendaItemRequest(titulo="Encomenda", tipo="pedido", data=date(2026, 6, 1))
        with pytest.raises(ValidationError):
            await service._validar_vinculos(uuid4(), dados)

    async def test_receita_inexistente_levanta(self) -> None:
        service = AgendaService(FakeRepo(receita_ok=False))  # type: ignore[arg-type]
        dados = CriarAgendaItemRequest(
            titulo="Bolo", tipo="receita", data=date(2026, 6, 1), receita_id=uuid4()
        )
        with pytest.raises(ValidationError):
            await service._validar_vinculos(uuid4(), dados)

    async def test_receita_valida_passa(self) -> None:
        service = AgendaService(FakeRepo())  # type: ignore[arg-type]
        dados = CriarAgendaItemRequest(
            titulo="Bolo", tipo="receita", data=date(2026, 6, 1), receita_id=uuid4()
        )
        # Não deve levantar.
        await service._validar_vinculos(uuid4(), dados)
