"""Agrupamento determinístico de linhas iguais, sem inferir dados ausentes."""

from decimal import ROUND_HALF_UP, Decimal

from domain.compras.comercial_schemas import ItemObservado
from domain.compras.identificadores import normalizar_descricao


def _conferido(item: ItemObservado) -> bool:
    numbers = (item.quantidade, item.preco_unitario, item.preco_total)
    if not item.unidade or not item.unidade.strip() or any(
        v is None or not v.is_finite() for v in numbers
    ):
        return False
    if not (0 < item.quantidade <= 10**9 and 0 < item.preco_unitario <= 10**9):
        return False
    desconto = item.desconto_item if item.desconto_item is not None else Decimal(0)
    if not desconto.is_finite() or not 0 <= desconto <= 10**9 or not 0 <= item.preco_total <= 10**9:
        return False
    return (item.quantidade * item.preco_unitario - desconto).quantize(
        Decimal(".01"), rounding=ROUND_HALF_UP
    ) == item.preco_total


def agrupar_observacoes(items: list[ItemObservado]) -> list[ItemObservado]:
    result: list[ItemObservado] = []
    positions: dict[tuple, int] = {}
    for original in items:
        item = original.model_copy(
            update={
                "linhas_origem": list(original.linhas_origem or [original.indice]),
            }
        )
        fields = item.model_dump(
            exclude={
                "indice",
                "linhas_origem",
                "quantidade",
                "preco_total",
                "desconto_item",
            }
        )
        fields["descricao"] = normalizar_descricao(item.descricao)
        key = tuple(
            (name, " ".join(value.split()).casefold() if isinstance(value, str) else value)
            for name, value in fields.items()
        )
        safe = _conferido(item) and all(
            not isinstance(value, Decimal) or value.is_finite() for value in fields.values()
        )
        position = positions.get(key) if safe else None
        if position is not None:
            previous = result[position]
            combined = previous.model_copy(
                update={
                    "quantidade": previous.quantidade + item.quantidade,
                    "preco_total": previous.preco_total + item.preco_total,
                    "desconto_item": (previous.desconto_item or Decimal(0))
                    + (item.desconto_item or Decimal(0)),
                    "linhas_origem": [*previous.linhas_origem, *item.linhas_origem],
                }
            )
            # Não ajustar preços ou centavos para forçar agrupamento.
            if _conferido(combined):
                result[position] = combined
                continue
        if safe:
            positions[key] = len(result)
        result.append(item)
    return [item.model_copy(update={"indice": index}) for index, item in enumerate(result)]
