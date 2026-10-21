"""Brazilian numeric presentation; never used for persistence or calculations."""

from decimal import ROUND_HALF_UP, Decimal, localcontext


def quantity_br(value: Decimal | str | int) -> str:
    number = Decimal(value)
    with localcontext() as context:
        context.prec = max(28, len(number.as_tuple().digits) + abs(number.adjusted()) + 4)
        rounded = number.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if not rounded:
        return "0"
    return format(rounded, "f").rstrip("0").rstrip(".").replace(".", ",")
