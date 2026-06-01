"""
Motor de cálculo de custos e precificação do Fornada.

Todas as funções são puras (sem I/O) para garantir testabilidade e confiabilidade.
Usa Decimal em todo lugar para evitar erros de ponto flutuante em valores monetários.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class ItemIngredienteCalculo:
    """Ingrediente com quantidade e custo médio já resolvidos."""

    nome: str
    quantidade: Decimal
    custo_medio_por_unidade: Decimal


@dataclass(frozen=True)
class ConfiguracaoCustoCalculo:
    """Parâmetros de custo operacional e hora trabalhada."""

    custo_operacional_mensal: Decimal
    horas_mensais: Decimal

    @property
    def custo_por_hora(self) -> Decimal:
        if self.horas_mensais <= 0:
            return Decimal("0")
        return (self.custo_operacional_mensal / self.horas_mensais).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )


@dataclass(frozen=True)
class CustoDetalhado:
    """Resultado completo do cálculo de custo de uma receita."""

    custo_ingredientes: Decimal
    custo_embalagem: Decimal
    custo_operacional: Decimal
    custo_mao_obra_direta: Decimal
    rendimento: Decimal

    @property
    def custo_total(self) -> Decimal:
        return (
            self.custo_ingredientes
            + self.custo_embalagem
            + self.custo_operacional
            + self.custo_mao_obra_direta
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def custo_por_unidade(self) -> Decimal:
        if self.rendimento <= 0:
            return Decimal("0")
        return (self.custo_total / self.rendimento).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def preco_minimo(self) -> Decimal:
        return self.custo_por_unidade


def calcular_custo_ingredientes(ingredientes: list[ItemIngredienteCalculo]) -> Decimal:
    """Soma o custo de todos os ingredientes da receita."""
    total = sum(
        (item.quantidade * item.custo_medio_por_unidade for item in ingredientes),
        Decimal("0"),
    )
    return total.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def calcular_custo_operacional(
    config: ConfiguracaoCustoCalculo,
    tempo_total_horas: Decimal,
) -> Decimal:
    """
    Calcula o custo operacional rateado para o tempo total da receita.
    Custo Op por Receita = Custo Op/hora × Tempo Total em Horas
    """
    resultado = config.custo_por_hora * tempo_total_horas
    return resultado.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_custo_mao_obra(
    tempo_ativo_horas: Decimal,
    valor_hora: Decimal,
) -> Decimal:
    """
    Custo MO = Tempo Ativo em Horas × Valor/Hora configurado.
    Usa apenas tempo ativo (direta), não passivo (forno ligado, aguardando etc).
    """
    resultado = tempo_ativo_horas * valor_hora
    return resultado.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_custo_total(
    ingredientes: list[ItemIngredienteCalculo],
    config: ConfiguracaoCustoCalculo,
    tempo_ativo_horas: Decimal,
    tempo_total_horas: Decimal,
    valor_hora: Decimal,
    rendimento: Decimal,
    embalagens: list[ItemIngredienteCalculo] | None = None,
) -> CustoDetalhado:
    """
    Calcula o custo completo de uma receita.

    Args:
        ingredientes: Itens do tipo "ingrediente" com quantidades e custo médio
        embalagens: Itens do tipo "embalagem" (caixinha, sacola, lacre etc.)
        config: Configurações de custo operacional do tenant
        tempo_ativo_horas: Horas de trabalho direto (mão de obra direta)
        tempo_total_horas: Tempo total da receita (usado para custo operacional)
        valor_hora: Valor/hora configurado pela confeiteira
        rendimento: Quantidade de unidades produzidas pela receita
    """
    custo_ingredientes = calcular_custo_ingredientes(ingredientes)
    custo_embalagem = calcular_custo_ingredientes(embalagens or [])
    custo_operacional = calcular_custo_operacional(config, tempo_total_horas)
    custo_mao_obra = calcular_custo_mao_obra(tempo_ativo_horas, valor_hora)

    return CustoDetalhado(
        custo_ingredientes=custo_ingredientes,
        custo_embalagem=custo_embalagem,
        custo_operacional=custo_operacional,
        custo_mao_obra_direta=custo_mao_obra,
        rendimento=rendimento,
    )


def calcular_custo_por_hora_produzida(
    custo_total: Decimal, tempo_ativo_horas: Decimal
) -> Decimal | None:
    """
    Custo/hora produzida = Custo Total / Tempo Ativo em Horas.

    Mostra o "custo por hora de trabalho" da receita — útil para comparar receitas
    e identificar quais consomem muito tempo em relação ao retorno.

    Retorna None quando não há tempo ativo (não dá pra calcular taxa horária).
    """
    if tempo_ativo_horas <= 0:
        return None
    return (custo_total / tempo_ativo_horas).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def calcular_lucro_por_minuto(
    lucro_por_unidade: Decimal,
    rendimento: Decimal,
    tempo_ativo_minutos: int,
) -> Decimal | None:
    """
    Lucro por minuto de produção = (Lucro por Unidade × Rendimento) / Tempo Ativo (min).

    Métrica do PRD §1: ajuda a usuária a entender o retorno em R$/min do tempo
    ativo investido — comparável entre receitas com tempos e rendimentos diferentes.

    Retorna None quando não há tempo ativo.
    """
    if tempo_ativo_minutos <= 0:
        return None
    lucro_total = lucro_por_unidade * rendimento
    return (lucro_total / Decimal(tempo_ativo_minutos)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def calcular_preco_recomendado(custo_por_unidade: Decimal, margem: Decimal) -> Decimal:
    """
    Preço Recomendado = Custo por Unidade / (1 - Margem Desejada)
    Margem deve ser decimal: 0.30 para 30%.
    """
    if margem >= Decimal("1"):
        raise ValueError("Margem deve ser menor que 100%")
    if margem < Decimal("0"):
        raise ValueError("Margem não pode ser negativa")
    if custo_por_unidade <= 0:
        return Decimal("0")

    preco = custo_por_unidade / (Decimal("1") - margem)
    return preco.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_lucro_estimado(preco_venda: Decimal, custo_por_unidade: Decimal) -> Decimal:
    """Lucro por unidade vendida."""
    return (preco_venda - custo_por_unidade).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_margem_real(preco_venda: Decimal, custo_por_unidade: Decimal) -> Decimal:
    """Margem real em decimal (0.30 = 30%)."""
    if preco_venda <= 0:
        return Decimal("0")
    margem = (preco_venda - custo_por_unidade) / preco_venda
    return margem.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def calcular_custo_medio_novo(
    estoque_atual: Decimal,
    custo_medio_atual: Decimal,
    quantidade_nova: Decimal,
    preco_novo: Decimal,
) -> Decimal:
    """
    Custo Médio Novo = (Estoque Atual × Custo Médio Atual + Qtd Nova × Preço Novo)
                      / (Estoque Atual + Qtd Nova)

    Usado ao registrar uma nova compra de ingrediente.
    """
    total_atual = estoque_atual + quantidade_nova
    if total_atual <= 0:
        return Decimal("0")

    novo_custo = (
        estoque_atual * custo_medio_atual + quantidade_nova * preco_novo
    ) / total_atual
    return novo_custo.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def minutos_para_horas(minutos: int) -> Decimal:
    """Converte minutos inteiros para horas Decimal."""
    return Decimal(str(minutos)) / Decimal("60")
