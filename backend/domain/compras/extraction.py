"""Contrato de extração e conferência financeira, independente do fornecedor."""

from dataclasses import dataclass, field, replace
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
    marca: str | None = None
    fabricante: str | None = None
    variante: str | None = None
    conteudo_embalagem: Decimal | None = None
    unidade_conteudo: str | None = None
    codigo_loja: str | None = None
    gtin: str | None = None
    desconto_item: Decimal | None = None
    campos_pendentes: list[str] = field(default_factory=list)


@dataclass
class ResultadoOCR:
    itens: list[ItemOCR]
    total: Decimal | float | None
    estabelecimento: str | None
    data: str | None
    fonte: str = "gemma3"
    confianca: float | None = None
    avisos: list[str] = field(default_factory=list)
    cnpj: str | None = None
    identidade_nota: str | None = None


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
        discount = (
            Decimal(str(item.desconto_item)) if item.desconto_item is not None else Decimal(0)
        )
        if not discount.is_finite() or discount < 0:
            raise ValidationError("Desconto inválido no cupom. Confira os valores.")
        if abs(q * unit - discount - total) > Decimal("0.02"):
            raise ValidationError(
                "Quantidade, preço e total de um item não conferem. Envie outra foto ou use ITEM."
            )
        items.append(
            replace(
                item,
                descricao=item.descricao.strip(),
                quantidade=q,
                unidade=item.unidade.strip(),
                preco_unitario=unit,
                preco_total=total,
                desconto_item=discount if item.desconto_item is not None else None,
            )
        )
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
    return replace(result, itens=items, total=receipt_total, avisos=list(dict.fromkeys(warnings)))


def receipt_from_mapping(data: dict, source: str) -> ResultadoOCR:
    try:
        items = [
            ItemOCR(
                item["descricao"],
                item["quantidade"],
                item["unidade"],
                item["preco_unitario"],
                item["preco_total"],
                **{
                    key: item.get(key)
                    for key in (
                        "marca",
                        "fabricante",
                        "variante",
                        "conteudo_embalagem",
                        "unidade_conteudo",
                        "codigo_loja",
                        "gtin",
                        "desconto_item",
                    )
                },
            )
            for item in data["itens"]
        ]
        return validate_receipt(
            ResultadoOCR(
                items,
                data["total"],
                data["estabelecimento"],
                data["data"],
                fonte=source,
                cnpj=data.get("cnpj"),
                identidade_nota=data.get("identidade_nota"),
            )
        )
    except (KeyError, TypeError, AttributeError):
        raise ValidationError(
            "Não conseguimos ler esse cupom. Envie outra foto ou use ITEM."
        ) from None
