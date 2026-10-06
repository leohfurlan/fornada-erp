"""Testes da sugestão de reposição da lista de compras (Sprint 4)."""

from decimal import Decimal

from domain.compras.lista import calcular_sugestao_reposicao


def test_sem_minimo_nao_sugere():
    # Sem estoque mínimo definido não há referência de quanto comprar.
    assert calcular_sugestao_reposicao(Decimal("0"), Decimal("0"), Decimal("5")) is None


def test_saldo_acima_do_minimo_nao_sugere():
    assert calcular_sugestao_reposicao(Decimal("10"), Decimal("3"), Decimal("5")) is None


def test_saldo_no_minimo_sugere_reposicao_ate_o_dobro():
    # mínimo 4, saldo 4 → alvo 8, comprar 4; custo 4 × R$2,50 = R$10,00
    resultado = calcular_sugestao_reposicao(Decimal("4"), Decimal("4"), Decimal("2.50"))
    assert resultado is not None
    quantidade, custo = resultado
    assert quantidade == Decimal("4.0000")
    assert custo == Decimal("10.00")


def test_saldo_abaixo_do_minimo_compra_mais():
    # mínimo 5, saldo 1 → alvo 10, comprar 9; custo 9 × R$1 = R$9,00
    quantidade, custo = calcular_sugestao_reposicao(
        Decimal("1"), Decimal("5"), Decimal("1")
    )
    assert quantidade == Decimal("9.0000")
    assert custo == Decimal("9.00")


def test_saldo_negativo_considera_reserva():
    # saldo -2 (reservado > atual), mínimo 3 → alvo 6, comprar 8
    quantidade, _ = calcular_sugestao_reposicao(
        Decimal("-2"), Decimal("3"), Decimal("4")
    )
    assert quantidade == Decimal("8.0000")
