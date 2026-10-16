"""Escolhas restritas ao catálogo do tenant; decisões nunca autorizam estoque."""

from dataclasses import dataclass
from typing import Protocol

from domain.compras.matching import (
    LIMIAR_MATCH,
    IngredienteRef,
    Sugestao,
    normalizar_unidade,
    score_similaridade,
    sugerir_tipo,
)


@dataclass(frozen=True)
class CatalogChoice:
    ingrediente_id: str | None
    score: float


class CatalogDecisionProvider(Protocol):
    async def choose(self, description: str, candidates: list[IngredienteRef]) -> CatalogChoice: ...


class LocalCatalogDecision:
    async def choose(self, description: str, candidates: list[IngredienteRef]) -> CatalogChoice:
        ranked = sorted(
            ((score_similaridade(description, item.nome), item.id) for item in candidates),
            reverse=True,
        )
        if not ranked or ranked[0][0] < LIMIAR_MATCH:
            return CatalogChoice(None, ranked[0][0] if ranked else 0)
        # Empate ou candidatos muito próximos exigem revisão, sem vínculo arbitrário.
        if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.05:
            return CatalogChoice(None, ranked[0][0])
        return CatalogChoice(ranked[0][1], ranked[0][0])


class CatalogMatcher:
    def __init__(self, provider: CatalogDecisionProvider | None = None):
        self.provider = provider or LocalCatalogDecision()

    async def suggest(self, description: str, unit: str, catalog: list[IngredienteRef]) -> Sugestao:
        candidates = sorted(
            catalog, key=lambda item: score_similaridade(description, item.nome), reverse=True
        )[:5]
        choice = await self.provider.choose(description, candidates)
        selected = next((item for item in candidates if item.id == choice.ingrediente_id), None)
        # Um fornecedor externo não pode selecionar IDs fora das opções enviadas.
        score = choice.score if 0 <= choice.score <= 1 else 0
        if selected is not None and score >= LIMIAR_MATCH:
            return Sugestao(selected.id, selected.nome, score, selected.tipo, selected.unidade)
        return Sugestao(None, None, score, sugerir_tipo(description), normalizar_unidade(unit))
