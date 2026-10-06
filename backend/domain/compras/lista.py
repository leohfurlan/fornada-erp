"""
Lista inteligente de compras (PRD §7) — parte pura/calculável.

Regra MVP: sugere recompra quando o saldo de um ingrediente atinge ou fica
abaixo do estoque mínimo configurado. A quantidade sugerida repõe até o dobro
do mínimo (uma folga de segurança), e o custo estimado usa o custo médio atual.
"""

from decimal import ROUND_HALF_UP, Decimal

# Multiplicador do estoque mínimo usado como alvo de reposição. Repor só até o
# mínimo deixaria o item imediatamente "baixo" de novo; 2× dá uma folga.
FATOR_REPOSICAO = Decimal("2")


def calcular_sugestao_reposicao(
    saldo: Decimal,
    estoque_minimo: Decimal,
    custo_medio: Decimal,
) -> tuple[Decimal, Decimal] | None:
    """
    Calcula a sugestão de recompra de um ingrediente.

    Retorna (quantidade_sugerida, custo_estimado) quando há necessidade de
    reposição, ou None quando o ingrediente não precisa ser comprado agora.

    Só sugere para ingredientes com estoque mínimo definido (> 0): sem mínimo
    não há referência para saber quanto comprar.
    """
    if estoque_minimo <= 0:
        return None
    if saldo > estoque_minimo:
        return None

    alvo = estoque_minimo * FATOR_REPOSICAO
    quantidade = (alvo - saldo).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if quantidade <= 0:
        return None

    custo_estimado = (quantidade * custo_medio).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return quantidade, custo_estimado
