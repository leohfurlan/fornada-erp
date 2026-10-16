from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from domain.estoque.schemas import AjusteEstoqueRequest
from domain.estoque.service import EstoqueService
from domain.exceptions import ConflictError, NotFoundError, ValidationError


class EstoqueRepositoryFake:
    def __init__(self, *, estoque: str = "5", reservado: str = "0") -> None:
        self.tenant_id = uuid4()
        self.ingrediente = SimpleNamespace(
            id=uuid4(),
            tenant_id=self.tenant_id,
            codigo=1,
            tipo="ingrediente",
            nome="Farinha",
            unidade="kg",
            unidades_alternativas=[],
            estoque_atual=Decimal(estoque),
            quantidade_reservada=Decimal(reservado),
            estoque_minimo=Decimal("0"),
            custo_medio=Decimal("8.5000"),
            data_custo_atualizado=None,
        )
        self.movimentacoes: list[SimpleNamespace] = []

    async def travar_tenant(self, tenant_id) -> None:
        # O tenant é travado antes da consulta; um tenant diferente simplesmente
        # não encontrará o material em buscar_por_id.
        return None

    async def buscar_por_id(self, ingrediente_id, tenant_id, *, for_update=False):
        if ingrediente_id != self.ingrediente.id or tenant_id != self.tenant_id:
            return None
        assert for_update
        return self.ingrediente

    async def salvar_movimentacao(self, **values):
        movimento = SimpleNamespace(
            id=uuid4(),
            created_at=datetime.now(UTC),
            **values,
        )
        self.movimentacoes.append(movimento)
        return movimento


def executar_sem_event_loop(coroutine):
    """Executa a coroutine do serviço com o repositório síncrono de teste."""
    try:
        coroutine.send(None)
    except StopIteration as resultado:
        return resultado.value
    raise AssertionError("O repositório fake não deve suspender a operação")


def test_ajuste_define_saldo_e_registra_delta_sem_mudar_custo():
    repo = EstoqueRepositoryFake()
    service = EstoqueService(repo)

    response = executar_sem_event_loop(
        service.ajustar_saldo(
            repo.ingrediente.id,
            repo.tenant_id,
            AjusteEstoqueRequest(quantidade_alvo=Decimal("3.25")),
        )
    )

    assert response.estoque_atual == Decimal("3.25")
    assert response.custo_medio == Decimal("8.5000")
    assert len(repo.movimentacoes) == 1
    assert repo.movimentacoes[0].tipo == "ajuste"
    assert repo.movimentacoes[0].quantidade == Decimal("-1.75")
    assert repo.movimentacoes[0].origem == "ajuste"


def test_ajuste_aumenta_saldo_com_diferenca_positiva():
    repo = EstoqueRepositoryFake(estoque="2")
    service = EstoqueService(repo)

    response = executar_sem_event_loop(
        service.ajustar_saldo(
            repo.ingrediente.id,
            repo.tenant_id,
            AjusteEstoqueRequest(quantidade_alvo=Decimal("3")),
        )
    )

    assert response.estoque_atual == Decimal("3")
    assert repo.movimentacoes[0].quantidade == Decimal("1")


def test_ajuste_nao_reduz_saldo_abaixo_do_reservado():
    repo = EstoqueRepositoryFake(estoque="5", reservado="2")
    service = EstoqueService(repo)

    with pytest.raises(ConflictError, match="abaixo da quantidade reservada"):
        executar_sem_event_loop(
            service.ajustar_saldo(
                repo.ingrediente.id,
                repo.tenant_id,
                AjusteEstoqueRequest(quantidade_alvo=Decimal("1")),
            )
        )

    assert repo.ingrediente.estoque_atual == Decimal("5")
    assert repo.movimentacoes == []


def test_ajuste_igual_ao_saldo_atual_e_item_de_outro_tenant_sao_rejeitados():
    repo = EstoqueRepositoryFake()
    service = EstoqueService(repo)

    with pytest.raises(ValidationError, match="corresponde ao estoque atual"):
        executar_sem_event_loop(
            service.ajustar_saldo(
                repo.ingrediente.id,
                repo.tenant_id,
                AjusteEstoqueRequest(quantidade_alvo=Decimal("5")),
            )
        )
    with pytest.raises(NotFoundError):
        executar_sem_event_loop(
            service.ajustar_saldo(
                repo.ingrediente.id,
                uuid4(),
                AjusteEstoqueRequest(quantidade_alvo=Decimal("4")),
            )
        )

    assert repo.movimentacoes == []
