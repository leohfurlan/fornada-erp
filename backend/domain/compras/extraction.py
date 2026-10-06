"""Contrato de extração e conferência financeira, independente do fornecedor."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Protocol

from domain.exceptions import ValidationError


@dataclass
class ItemOCR:
    descricao: str
    quantidade: Decimal | float | None
    unidade: str | None
    preco_unitario: Decimal | float | None
    preco_total: Decimal | float | None


@dataclass
class ResultadoOCR:
    itens: list[ItemOCR]
    total: Decimal | float | None
    estabelecimento: str | None
    data: str | None
    fonte: str = "gemma3"
    confianca: float | None = None
    avisos: list[str] = field(default_factory=list)


class ReceiptExtractor(Protocol):
    async def processar_imagem(
        self, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> ResultadoOCR: ...


def decimal_value(value: object) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValidationError("Há valores ilegíveis no cupom. Envie outra foto ou use ITEM.")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError(
            "O cupom contém valores inválidos. Envie outra foto ou use ITEM."
        ) from None
    if not number.is_finite() or number <= 0 or number > Decimal("1000000000"):
        raise ValidationError("O cupom contém valores inválidos. Envie outra foto ou use ITEM.")
    return number


def validate_receipt(result: ResultadoOCR) -> ResultadoOCR:
    if not result.itens or len(result.itens) > 100:
        raise ValidationError("Não conseguimos extrair os itens. Envie outra foto ou use ITEM.")
    items = []
    for item in result.itens:
        if not isinstance(item.descricao, str) or not item.descricao.strip():
            raise ValidationError("Há descrições ilegíveis no cupom. Envie outra foto ou use ITEM.")
        if not isinstance(item.unidade, str) or not item.unidade.strip():
            raise ValidationError("Há unidades ilegíveis no cupom. Envie outra foto ou use ITEM.")
        q, unit, total = map(
            decimal_value, (item.quantidade, item.preco_unitario, item.preco_total)
        )
        if abs(q * unit - total) > Decimal("0.02"):
            raise ValidationError(
                "Quantidade, preço e total de um item não conferem. Envie outra foto ou use ITEM."
            )
        items.append(ItemOCR(item.descricao.strip(), q, item.unidade.strip(), unit, total))
    receipt_total = decimal_value(result.total) if result.total is not None else None
    warnings = list(result.avisos)
    if receipt_total is None:
        warnings.append(
            "Total do cupom não identificado; confira todos os itens antes de confirmar."
        )
    elif abs(sum((item.preco_total for item in items), Decimal(0)) - receipt_total) > Decimal(
        "0.02"
    ):
        warnings.append(
            "A soma dos itens difere do total do cupom. "
            "Confira descontos, acréscimos e itens faltantes."
        )
    return ResultadoOCR(
        items,
        receipt_total,
        result.estabelecimento,
        result.data,
        result.fonte,
        result.confianca,
        list(dict.fromkeys(warnings)),
    )


def receipt_from_mapping(data: dict, source: str) -> ResultadoOCR:
    try:
        items = [
            ItemOCR(
                item["descricao"],
                item["quantidade"],
                item["unidade"],
                item["preco_unitario"],
                item["preco_total"],
            )
            for item in data["itens"]
        ]
        return validate_receipt(
            ResultadoOCR(items, data["total"], data["estabelecimento"], data["data"], fonte=source)
        )
    except (KeyError, TypeError, AttributeError):
        raise ValidationError(
            "Não conseguimos ler esse cupom. Envie outra foto ou use ITEM."
        ) from None
