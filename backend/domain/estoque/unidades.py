"""Conversões específicas do ingrediente, sempre para sua unidade principal."""
from decimal import Decimal
from collections.abc import Sequence
from typing import Any
from domain.exceptions import ValidationError
from domain.receitas.composicao import converter_quantidade


def normalizar_unidade(unidade: str) -> str:
    """Normaliza apenas grafia/espaçamento, sem inferir medidas culinárias."""
    return " ".join(unidade.lower().strip().split())


def converter_para_principal(quantidade: Decimal, origem: str, principal: str, alternativas: Sequence[dict[str, Any]] | None = None) -> Decimal:
    """Converte por fator confirmado ou por equivalência métrica exata."""
    origem, principal = normalizar_unidade(origem), normalizar_unidade(principal)
    for alternativa in alternativas or []:
        if normalizar_unidade(alternativa["unidade"]) == origem:
            return quantidade * Decimal(str(alternativa["fator"]))
    try:
        return converter_quantidade(quantidade, origem, principal)
    except ValidationError:
        raise ValidationError(f"Cadastre a conversão de {origem} para {principal} neste ingrediente.") from None
