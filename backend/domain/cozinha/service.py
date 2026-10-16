"""Deterministic kitchen projections and recipe block navigation."""

import re
from typing import Any
from uuid import UUID

from domain.receitas.central_snapshot import snapshot

ORDERED_ITEM = re.compile(r"^\s*\d+[.)]\s+(.+?)\s*$")


def preparation_blocks(markdown: str | None) -> list[dict[str, str]]:
    if not markdown or not markdown.strip():
        return []
    lines = [line for line in markdown.splitlines() if line.strip()]
    parsed = [ORDERED_ITEM.fullmatch(line) for line in lines]
    if lines and all(parsed):
        return [
            {
                "id": f"preparation-{index}",
                "section": "preparation",
                "title": f"Etapa {index}",
                "markdown": match.group(1),
            }
            for index, match in enumerate(parsed, start=1)
            if match is not None
        ]
    return [
        {
            "id": "preparation-1",
            "section": "preparation",
            "title": "Modo de preparo",
            "markdown": markdown,
        }
    ]


def build_projection(data: dict[str, Any]) -> dict[str, Any]:
    ingredients = data["ingredients"]
    ingredient_text = "\n".join(
        f"- {item['name']}: {item['quantity']} {item['unit']}" for item in ingredients
    )
    blocks: list[dict[str, str]] = []
    if ingredients:
        blocks.append(
            {
                "id": "ingredients-1",
                "section": "ingredients",
                "title": "Ingredientes",
                "markdown": ingredient_text,
            }
        )
    preparation = next(
        (section["text"] for section in data["sections"] if section["title"] == "Modo de preparo"),
        None,
    )
    blocks.extend(preparation_blocks(preparation))
    for section in data["sections"]:
        match = re.fullmatch(r"Montagem (\d+)", section["title"])
        if match:
            index = int(match.group(1))
            blocks.append(
                {
                    "id": f"assembly-{index}",
                    "section": "assembly",
                    "title": f"Montagem {index}",
                    "markdown": section["text"],
                }
            )
    return {
        "recipe_id": data["recipe_id"],
        "recipe_version": data["version"],
        "name": data["name"],
        "yield_quantity": data["yield_quantity"],
        "yield_unit": data["yield_unit"],
        "ingredients": ingredients,
        "blocks": blocks,
        "warnings": data["warnings"],
    }


def station_view(station) -> dict[str, Any]:
    return {
        "id": str(station.id),
        "name": station.nome,
        "status": station.status,
        "revision": station.revisao,
        "recipe_id": str(station.receita_id) if station.receita_id else None,
        "recipe_version": station.receita_versao,
        "selection": station.resultados_busca,
        "section": station.secao,
        "block_index": station.bloco_indice,
        "speech_part_index": station.parte_fala_indice,
        "delivered_revision": station.delivered_revision,
        "rendered_revision": station.rendered_revision,
        "projection": station.projection,
        "notice": station.aviso,
    }


async def recipe_projection(db, tenant_id: UUID, recipe_id: UUID) -> dict[str, Any] | None:
    data = await snapshot(db, tenant_id, recipe_id)
    return build_projection(data) if data else None


def active_block_index(projection: dict[str, Any] | None, section: str, current: int) -> int:
    if projection is None:
        return 0
    blocks = [block for block in projection["blocks"] if block["section"] == section]
    return min(max(current, 0), max(len(blocks) - 1, 0))
