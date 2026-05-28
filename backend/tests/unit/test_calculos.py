"""
Testes do motor de cálculo de custos — cobertura mínima exigida: 95%.
Todos os testes usam Decimal para consistência com o motor de produção.
"""

from decimal import Decimal

import pytest

from domain.receitas.calculos import (
    ConfiguracaoCustoCalculo,
    ItemIngredienteCalculo,
    calcular_custo_ingredientes,
    calcular_custo_mao_obra,
    calcular_custo_medio_novo,
    calcular_custo_operacional,
    calcular_custo_total,
    calcular_lucro_estimado,
    calcular_margem_real,
    calcular_preco_recomendado,
    minutos_para_horas,
)


# ---------------------------------------------------------------------------
# Fixtures reutilizáveis
# ---------------------------------------------------------------------------


@pytest.fixture
def config_padrao() -> ConfiguracaoCustoCalculo:
    """R$ 500/mês de custo operacional, 100h mensais → R$ 5/h."""
    return ConfiguracaoCustoCalculo(
        custo_operacional_mensal=Decimal("500"),
        horas_mensais=Decimal("100"),
    )


@pytest.fixture
def ingredientes_simples() -> list[ItemIngredienteCalculo]:
    return [
        ItemIngredienteCalculo(
            nome="Farinha de trigo",
            quantidade=Decimal("0.5"),
            custo_medio_por_unidade=Decimal("4.00"),
        ),
        ItemIngredienteCalculo(
            nome="Açúcar",
            quantidade=Decimal("0.3"),
            custo_medio_por_unidade=Decimal("3.50"),
        ),
        ItemIngredienteCalculo(
            nome="Manteiga",
            quantidade=Decimal("0.1"),
            custo_medio_por_unidade=Decimal("30.00"),
        ),
    ]


# ---------------------------------------------------------------------------
# calcular_custo_ingredientes
# ---------------------------------------------------------------------------


class TestCalcularCustoIngredientes:
    def test_soma_correta(self, ingredientes_simples: list[ItemIngredienteCalculo]) -> None:
        # 0.5×4 + 0.3×3.50 + 0.1×30 = 2 + 1.05 + 3 = 6.05
        resultado = calcular_custo_ingredientes(ingredientes_simples)
        assert resultado == Decimal("6.0500")

    def test_lista_vazia(self) -> None:
        assert calcular_custo_ingredientes([]) == Decimal("0")

    def test_um_ingrediente(self) -> None:
        items = [
            ItemIngredienteCalculo(
                nome="Chocolate",
                quantidade=Decimal("0.2"),
                custo_medio_por_unidade=Decimal("50.00"),
            )
        ]
        assert calcular_custo_ingredientes(items) == Decimal("10.0000")

    def test_quantidade_grande(self) -> None:
        items = [
            ItemIngredienteCalculo(
                nome="Farinha",
                quantidade=Decimal("10"),
                custo_medio_por_unidade=Decimal("4.20"),
            )
        ]
        assert calcular_custo_ingredientes(items) == Decimal("42.0000")


# ---------------------------------------------------------------------------
# ConfiguracaoCustoCalculo — custo_por_hora
# ---------------------------------------------------------------------------


class TestConfiguracaoCusto:
    def test_custo_por_hora_basico(self, config_padrao: ConfiguracaoCustoCalculo) -> None:
        assert config_padrao.custo_por_hora == Decimal("5.0000")

    def test_custo_por_hora_zero_horas(self) -> None:
        config = ConfiguracaoCustoCalculo(
            custo_operacional_mensal=Decimal("500"),
            horas_mensais=Decimal("0"),
        )
        assert config.custo_por_hora == Decimal("0")

    def test_custo_por_hora_arredondamento(self) -> None:
        config = ConfiguracaoCustoCalculo(
            custo_operacional_mensal=Decimal("1000"),
            horas_mensais=Decimal("160"),
        )
        # 1000/160 = 6.25
        assert config.custo_por_hora == Decimal("6.2500")


# ---------------------------------------------------------------------------
# calcular_custo_operacional
# ---------------------------------------------------------------------------


class TestCalcularCustoOperacional:
    def test_basico(self, config_padrao: ConfiguracaoCustoCalculo) -> None:
        # custo/h = 5, tempo = 2h → 10
        resultado = calcular_custo_operacional(config_padrao, Decimal("2"))
        assert resultado == Decimal("10.00")

    def test_tempo_fracionado(self, config_padrao: ConfiguracaoCustoCalculo) -> None:
        # custo/h = 5, tempo = 1.5h → 7.50
        resultado = calcular_custo_operacional(config_padrao, Decimal("1.5"))
        assert resultado == Decimal("7.50")

    def test_tempo_zero(self, config_padrao: ConfiguracaoCustoCalculo) -> None:
        resultado = calcular_custo_operacional(config_padrao, Decimal("0"))
        assert resultado == Decimal("0.00")


# ---------------------------------------------------------------------------
# calcular_custo_mao_obra
# ---------------------------------------------------------------------------


class TestCalcularCustoMaoObra:
    def test_basico(self) -> None:
        # 2h × R$ 25/h = R$ 50
        resultado = calcular_custo_mao_obra(Decimal("2"), Decimal("25"))
        assert resultado == Decimal("50.00")

    def test_tempo_fracionado(self) -> None:
        # 1.5h × R$ 30/h = R$ 45
        resultado = calcular_custo_mao_obra(Decimal("1.5"), Decimal("30"))
        assert resultado == Decimal("45.00")

    def test_valor_hora_zero(self) -> None:
        resultado = calcular_custo_mao_obra(Decimal("3"), Decimal("0"))
        assert resultado == Decimal("0.00")

    def test_tempo_zero(self) -> None:
        resultado = calcular_custo_mao_obra(Decimal("0"), Decimal("50"))
        assert resultado == Decimal("0.00")


# ---------------------------------------------------------------------------
# calcular_custo_total / CustoDetalhado
# ---------------------------------------------------------------------------


class TestCalcularCustoTotal:
    def test_calculo_completo(
        self,
        ingredientes_simples: list[ItemIngredienteCalculo],
        config_padrao: ConfiguracaoCustoCalculo,
    ) -> None:
        # ingredientes: 6.05
        # operacional: 5/h × 2h = 10
        # mão de obra: 1h × 25/h = 25
        # total = 41.05 / 12 unidades ≈ 3.42
        resultado = calcular_custo_total(
            ingredientes=ingredientes_simples,
            config=config_padrao,
            tempo_ativo_horas=Decimal("1"),
            tempo_total_horas=Decimal("2"),
            valor_hora=Decimal("25"),
            rendimento=Decimal("12"),
        )
        assert resultado.custo_ingredientes == Decimal("6.0500")
        assert resultado.custo_operacional == Decimal("10.00")
        assert resultado.custo_mao_obra_direta == Decimal("25.00")
        assert resultado.custo_total == Decimal("41.05")
        assert resultado.rendimento == Decimal("12")
        assert resultado.custo_por_unidade == Decimal("3.42")

    def test_rendimento_unitario(
        self,
        ingredientes_simples: list[ItemIngredienteCalculo],
        config_padrao: ConfiguracaoCustoCalculo,
    ) -> None:
        resultado = calcular_custo_total(
            ingredientes=ingredientes_simples,
            config=config_padrao,
            tempo_ativo_horas=Decimal("1"),
            tempo_total_horas=Decimal("1"),
            valor_hora=Decimal("20"),
            rendimento=Decimal("1"),
        )
        assert resultado.custo_total == resultado.custo_por_unidade

    def test_preco_minimo_igual_custo_por_unidade(
        self,
        ingredientes_simples: list[ItemIngredienteCalculo],
        config_padrao: ConfiguracaoCustoCalculo,
    ) -> None:
        resultado = calcular_custo_total(
            ingredientes=ingredientes_simples,
            config=config_padrao,
            tempo_ativo_horas=Decimal("1"),
            tempo_total_horas=Decimal("1"),
            valor_hora=Decimal("20"),
            rendimento=Decimal("10"),
        )
        assert resultado.preco_minimo == resultado.custo_por_unidade

    def test_rendimento_zero(
        self,
        ingredientes_simples: list[ItemIngredienteCalculo],
        config_padrao: ConfiguracaoCustoCalculo,
    ) -> None:
        resultado = calcular_custo_total(
            ingredientes=ingredientes_simples,
            config=config_padrao,
            tempo_ativo_horas=Decimal("1"),
            tempo_total_horas=Decimal("1"),
            valor_hora=Decimal("20"),
            rendimento=Decimal("0"),
        )
        assert resultado.custo_por_unidade == Decimal("0")


# ---------------------------------------------------------------------------
# calcular_preco_recomendado
# ---------------------------------------------------------------------------


class TestCalcularPrecoRecomendado:
    def test_margem_30_porcento(self) -> None:
        # 10 / (1 - 0.30) = 14.29
        resultado = calcular_preco_recomendado(Decimal("10"), Decimal("0.30"))
        assert resultado == Decimal("14.29")

    def test_margem_50_porcento(self) -> None:
        # 10 / (1 - 0.50) = 20.00
        resultado = calcular_preco_recomendado(Decimal("10"), Decimal("0.50"))
        assert resultado == Decimal("20.00")

    def test_margem_zero(self) -> None:
        resultado = calcular_preco_recomendado(Decimal("10"), Decimal("0"))
        assert resultado == Decimal("10.00")

    def test_custo_zero(self) -> None:
        resultado = calcular_preco_recomendado(Decimal("0"), Decimal("0.30"))
        assert resultado == Decimal("0")

    def test_margem_cem_porcento_levanta_erro(self) -> None:
        with pytest.raises(ValueError, match="Margem deve ser menor que 100%"):
            calcular_preco_recomendado(Decimal("10"), Decimal("1"))

    def test_margem_negativa_levanta_erro(self) -> None:
        with pytest.raises(ValueError, match="Margem não pode ser negativa"):
            calcular_preco_recomendado(Decimal("10"), Decimal("-0.10"))


# ---------------------------------------------------------------------------
# calcular_lucro_estimado
# ---------------------------------------------------------------------------


class TestCalcularLucroEstimado:
    def test_lucro_positivo(self) -> None:
        assert calcular_lucro_estimado(Decimal("25"), Decimal("10")) == Decimal("15.00")

    def test_lucro_zero(self) -> None:
        assert calcular_lucro_estimado(Decimal("10"), Decimal("10")) == Decimal("0.00")

    def test_prejuizo(self) -> None:
        assert calcular_lucro_estimado(Decimal("8"), Decimal("10")) == Decimal("-2.00")


# ---------------------------------------------------------------------------
# calcular_margem_real
# ---------------------------------------------------------------------------


class TestCalcularMargemReal:
    def test_margem_50_porcento(self) -> None:
        # (20 - 10) / 20 = 0.50
        assert calcular_margem_real(Decimal("20"), Decimal("10")) == Decimal("0.5000")

    def test_preco_zero(self) -> None:
        assert calcular_margem_real(Decimal("0"), Decimal("10")) == Decimal("0")

    def test_sem_lucro(self) -> None:
        assert calcular_margem_real(Decimal("10"), Decimal("10")) == Decimal("0.0000")


# ---------------------------------------------------------------------------
# calcular_custo_medio_novo
# ---------------------------------------------------------------------------


class TestCalcularCustoMedioNovo:
    def test_basico(self) -> None:
        # Estoque: 100 kg a R$ 4/kg
        # Compra: 50 kg a R$ 5/kg
        # (100×4 + 50×5) / 150 = 650/150 = 4.3333
        resultado = calcular_custo_medio_novo(
            estoque_atual=Decimal("100"),
            custo_medio_atual=Decimal("4"),
            quantidade_nova=Decimal("50"),
            preco_novo=Decimal("5"),
        )
        assert resultado == Decimal("4.3333")

    def test_estoque_zerado(self) -> None:
        # Primeiro lote: custo médio = preço da compra
        resultado = calcular_custo_medio_novo(
            estoque_atual=Decimal("0"),
            custo_medio_atual=Decimal("0"),
            quantidade_nova=Decimal("10"),
            preco_novo=Decimal("3.50"),
        )
        assert resultado == Decimal("3.5000")

    def test_precos_iguais(self) -> None:
        resultado = calcular_custo_medio_novo(
            estoque_atual=Decimal("50"),
            custo_medio_atual=Decimal("4"),
            quantidade_nova=Decimal("50"),
            preco_novo=Decimal("4"),
        )
        assert resultado == Decimal("4.0000")

    def test_total_zero(self) -> None:
        # Não deveria acontecer, mas não pode dividir por zero
        resultado = calcular_custo_medio_novo(
            estoque_atual=Decimal("0"),
            custo_medio_atual=Decimal("0"),
            quantidade_nova=Decimal("0"),
            preco_novo=Decimal("5"),
        )
        assert resultado == Decimal("0")


# ---------------------------------------------------------------------------
# minutos_para_horas
# ---------------------------------------------------------------------------


class TestMinutosParaHoras:
    def test_60_minutos(self) -> None:
        assert minutos_para_horas(60) == Decimal("1")

    def test_30_minutos(self) -> None:
        assert minutos_para_horas(30) == Decimal("0.5")

    def test_90_minutos(self) -> None:
        assert minutos_para_horas(90) == Decimal("1.5")

    def test_zero_minutos(self) -> None:
        assert minutos_para_horas(0) == Decimal("0")
