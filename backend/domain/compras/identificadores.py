"""Validação e normalização conservadora dos identificadores comerciais."""

import re
import unicodedata
from decimal import Decimal

from domain.exceptions import ValidationError


def validar_gtin(value: str | None) -> str | None:
    """Valida código universal explicitamente informado, sem inferir sua natureza."""
    if value is None:
        return None
    if not value.isdigit() or len(value) not in (8, 12, 13, 14) or len(set(value)) == 1:
        raise ValueError("Informe um GTIN/EAN válido, sem espaços.")
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(value[:-1])))
    if (10 - total % 10) % 10 != int(value[-1]):
        raise ValueError("O dígito verificador do GTIN/EAN não confere.")
    return value


def validar_cnpj(value: str | None) -> str | None:
    """Valida CNPJ numérico informado pela usuária."""
    if value is None:
        return None
    digits = re.sub(r"[./\-\s]", "", value)
    if not digits.isdigit() or len(digits) != 14 or len(set(digits)) == 1:
        raise ValueError("Informe um CNPJ válido.")
    for size, weights in (
        (12, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
        (13, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
    ):
        remainder = sum(int(d) * w for d, w in zip(digits[:size], weights, strict=True)) % 11
        if int(digits[size]) != (0 if remainder < 2 else 11 - remainder):
            raise ValueError("O dígito verificador do CNPJ não confere.")
    return digits


def normalizar_descricao(texto: str) -> str:
    """Preserva números, variante e separador decimal ao remover ruído de grafia."""
    texto = "".join(
        c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c)
    )
    texto = re.sub(r"(?<=\d),(?=\d)", ".", texto)
    texto = re.sub(r"(\d)\s*(kg|mg|ml|g|l)\b", r"\1 \2", texto)
    texto = re.sub(r"[^a-z0-9.\s]", " ", texto)
    texto = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", texto)
    return " ".join(texto.split())


def variante_texto(texto: str) -> str | None:
    """Reconhece somente variantes explícitas, sem classificar texto genérico."""
    texto = normalizar_descricao(texto)
    if re.search(r"\bbranc[oa]\b", texto):
        return "branco"
    if "meio amarg" in texto:
        return "meio amargo"
    if "ao leite" in texto:
        return "ao leite"
    if re.search(r"\bamarg[oa]\b", texto):
        return "amargo"
    return None


def validar_evidencia(
    descricao: str, variante: str | None, conteudo: Decimal, unidade: str
) -> None:
    """Bloqueia contradição explícita com variante ou conteúdo confirmado."""
    lida, aprovada = variante_texto(descricao), variante_texto(variante or "")
    if lida and aprovada and lida != aprovada:
        raise ValidationError("A variante do cupom difere do produto. Confira o vínculo.")
    measures = re.findall(r"(\d+(?:[.,]\d+)?)\s*(kg|mg|ml|g|l)\b", descricao.lower())
    factors = {
        "g": ("peso", Decimal("1")),
        "mg": ("peso", Decimal("0.001")),
        "kg": ("peso", Decimal("1000")),
        "ml": ("volume", Decimal("1")),
        "l": ("volume", Decimal("1000")),
    }
    if unidade in factors:
        dimension, factor = factors[unidade]
        for number, unit in measures:
            if (
                factors[unit][0] != dimension
                or Decimal(number.replace(",", ".")) * factors[unit][1] != conteudo * factor
            ):
                raise ValidationError(
                    "A embalagem do cupom difere do produto. Escolha a embalagem correta."
                )
