"""Testes da precificação com taxas (iFood/cartão) — Sprint 4."""

from decimal import Decimal

import pytest

from domain.receitas.calculos import (
    calcular_preco_recomendado,
    calcular_preco_recomendado_com_taxas,
)


class TestPrecoComTaxas:
    def test_sem_taxa_igual_ao_preco_recomendado_normal(self) -> None:
        # taxa_total = 0 deve coincidir com a fórmula sem taxas.
        custo = Decimal("10.00")
        margem = Decimal("0.30")
        assert calcular_preco_recomendado_com_taxas(
            custo, margem, Decimal("0")
        ) == calcular_preco_recomendado(custo, margem)

    def test_taxa_infla_o_preco(self) -> None:
        # custo 10, margem 30%, taxa 20% → 10 / (1 - 0,30 - 0,20) = 10 / 0,5 = 20,00
        assert calcular_preco_recomendado_com_taxas(
            Decimal("10.00"), Decimal("0.30"), Decimal("0.20")
        ) == Decimal("20.00")

    def test_margem_liquida_apos_taxas_bate(self) -> None:
        # Confere a propriedade: preço − taxas − custo = margem × preço.
        custo = Decimal("8.00")
        margem = Decimal("0.40")
        taxa = Decimal("0.12")
        preco = calcular_preco_recomendado_com_taxas(custo, margem, taxa)
        lucro = preco - (preco * taxa) - custo
        # Lucro deve equivaler à margem desejada sobre o preço (tolerância de arredondamento).
        assert abs(lucro - (margem * preco)) <= Decimal("0.01")

    def test_custo_zero_retorna_zero(self) -> None:
        assert calcular_preco_recomendado_com_taxas(
            Decimal("0"), Decimal("0.30"), Decimal("0.10")
        ) == Decimal("0")

    def test_margem_mais_taxa_atingindo_100pct_levanta_erro(self) -> None:
        with pytest.raises(ValueError):
            calcular_preco_recomendado_com_taxas(
                Decimal("10"), Decimal("0.60"), Decimal("0.40")
            )

    def test_valores_negativos_levantam_erro(self) -> None:
        with pytest.raises(ValueError):
            calcular_preco_recomendado_com_taxas(
                Decimal("10"), Decimal("-0.1"), Decimal("0.1")
            )
        with pytest.raises(ValueError):
            calcular_preco_recomendado_com_taxas(
                Decimal("10"), Decimal("0.1"), Decimal("-0.1")
            )
