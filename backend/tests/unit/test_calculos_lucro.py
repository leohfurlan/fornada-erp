"""Testes das novas funções de lucro/custo da Sprint 2."""

from decimal import Decimal

from domain.receitas.calculos import (
    ConfiguracaoCustoCalculo,
    ItemIngredienteCalculo,
    calcular_custo_por_hora_produzida,
    calcular_custo_total,
    calcular_lucro_estimado,
    calcular_lucro_por_minuto,
)


class TestCalcularCustoPorHoraProduzida:
    def test_calculo_simples(self) -> None:
        # R$ 60 de custo / 2h = R$ 30/h
        assert calcular_custo_por_hora_produzida(
            Decimal("60.00"), Decimal("2")
        ) == Decimal("30.00")

    def test_tempo_zero_retorna_none(self) -> None:
        # Sem tempo ativo não dá pra calcular taxa horária.
        assert calcular_custo_por_hora_produzida(Decimal("100"), Decimal("0")) is None

    def test_tempo_negativo_retorna_none(self) -> None:
        assert calcular_custo_por_hora_produzida(Decimal("100"), Decimal("-1")) is None

    def test_arredondamento_para_centavos(self) -> None:
        # 10 / 3 = 3.333... → 3.33
        assert calcular_custo_por_hora_produzida(
            Decimal("10"), Decimal("3")
        ) == Decimal("3.33")


class TestCalcularLucroPorMinuto:
    def test_calculo_simples(self) -> None:
        # Lucro/un = R$ 5; rendimento = 12; tempo ativo = 60 min.
        # Lucro total = 60. Por minuto = 60 / 60 = 1.00.
        assert calcular_lucro_por_minuto(
            Decimal("5.00"), Decimal("12"), 60
        ) == Decimal("1.00")

    def test_tempo_zero_retorna_none(self) -> None:
        assert calcular_lucro_por_minuto(Decimal("5"), Decimal("12"), 0) is None

    def test_lucro_negativo_funciona(self) -> None:
        # Se está dando prejuízo, retorna valor negativo — a UI pode destacar.
        assert calcular_lucro_por_minuto(
            Decimal("-2"), Decimal("10"), 60
        ) == Decimal("-0.33")


class TestCustoTotalComEmbalagem:
    """Garante que embalagem entra no custo total separadamente dos ingredientes."""

    def test_embalagem_soma_no_custo_total(self) -> None:
        ingredientes = [
            ItemIngredienteCalculo(
                nome="Farinha",
                quantidade=Decimal("1"),
                custo_medio_por_unidade=Decimal("5"),
            )
        ]
        embalagens = [
            ItemIngredienteCalculo(
                nome="Caixinha",
                quantidade=Decimal("1"),
                custo_medio_por_unidade=Decimal("2"),
            )
        ]
        config = ConfiguracaoCustoCalculo(
            custo_operacional_mensal=Decimal("0"),
            horas_mensais=Decimal("100"),
        )
        resultado = calcular_custo_total(
            ingredientes=ingredientes,
            embalagens=embalagens,
            config=config,
            tempo_ativo_horas=Decimal("0"),
            tempo_total_horas=Decimal("0"),
            valor_hora=Decimal("0"),
            rendimento=Decimal("1"),
        )
        assert resultado.custo_ingredientes == Decimal("5.0000")
        assert resultado.custo_embalagem == Decimal("2.0000")
        # 5 (ingr) + 2 (emb) + 0 (op) + 0 (mo) = 7
        assert resultado.custo_total == Decimal("7.00")

    def test_sem_embalagem_zerado(self) -> None:
        config = ConfiguracaoCustoCalculo(
            custo_operacional_mensal=Decimal("0"), horas_mensais=Decimal("100")
        )
        resultado = calcular_custo_total(
            ingredientes=[],
            config=config,
            tempo_ativo_horas=Decimal("0"),
            tempo_total_horas=Decimal("0"),
            valor_hora=Decimal("0"),
            rendimento=Decimal("1"),
        )
        assert resultado.custo_embalagem == Decimal("0")


class TestFluxoCompletoLucro:
    """Cenário end-to-end: receita rende 10un, vendida a R$ 15, com 30 min de mão de obra ativa."""

    def test_lucro_e_metricas_horarias(self) -> None:
        ingredientes = [
            ItemIngredienteCalculo(
                nome="Açúcar",
                quantidade=Decimal("2"),
                custo_medio_por_unidade=Decimal("3"),
            )
        ]
        config = ConfiguracaoCustoCalculo(
            custo_operacional_mensal=Decimal("0"), horas_mensais=Decimal("100")
        )
        # tempo ativo = 30 min = 0.5h
        resultado = calcular_custo_total(
            ingredientes=ingredientes,
            config=config,
            tempo_ativo_horas=Decimal("0.5"),
            tempo_total_horas=Decimal("0.5"),
            valor_hora=Decimal("20"),  # R$ 20/h
            rendimento=Decimal("10"),
        )
        # custo: 6 (ingr) + 0 (op) + 10 (mão de obra) = 16
        assert resultado.custo_total == Decimal("16.00")
        # custo/un = 1.60
        assert resultado.custo_por_unidade == Decimal("1.60")

        # Vendendo a R$ 15/un:
        preco_venda = Decimal("15.00")
        lucro_unitario = calcular_lucro_estimado(preco_venda, resultado.custo_por_unidade)
        assert lucro_unitario == Decimal("13.40")

        # Custo/hora produzida: 16 / 0.5 = 32
        custo_por_hora = calcular_custo_por_hora_produzida(
            resultado.custo_total, Decimal("0.5")
        )
        assert custo_por_hora == Decimal("32.00")

        # Lucro/min: (13.40 × 10) / 30 = 4.47 (arredondado)
        lucro_min = calcular_lucro_por_minuto(lucro_unitario, Decimal("10"), 30)
        assert lucro_min == Decimal("4.47")
