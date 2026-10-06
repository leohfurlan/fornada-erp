"""Unidades e dependências da composição, sem conversões massa/volume implícitas."""
from decimal import Decimal

from domain.exceptions import ValidationError

_UNIDADES = {
    "g": ("massa", Decimal("1")), "kg": ("massa", Decimal("1000")),
    "mg": ("massa", Decimal("0.001")),
    "ml": ("volume", Decimal("1")), "l": ("volume", Decimal("1000")),
    "un": ("contagem", Decimal("1")), "unidade": ("contagem", Decimal("1")),
    "unidades": ("contagem", Decimal("1")),
    "dz": ("contagem", Decimal("12")),
}


def converter_quantidade(quantidade: Decimal, origem: str, destino: str) -> Decimal:
    """Converte somente unidades da mesma dimensão, mantendo precisão decimal."""
    if origem.lower() == destino.lower():
        return quantidade
    a, b = _UNIDADES.get(origem.lower()), _UNIDADES.get(destino.lower())
    if a is None or b is None or a[0] != b[0]:
        raise ValidationError(f"Unidades incompatíveis: {origem} e {destino}. Confira o rendimento ou cadastro do componente.")
    return quantidade * a[1] / b[1]
