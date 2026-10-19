"""Deterministic kitchen projections and recipe block navigation."""

import re
from typing import Any
from uuid import UUID, uuid4

from domain.receitas.central_snapshot import snapshot


def preparation_blocks(markdown: str | None) -> list[dict[str, str]]:
    if not markdown or not markdown.strip():
        return []
    return [
        {
            "id": "preparation-text",
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
    blocks: list[dict[str, Any]] = []
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
    for step in sorted(data.get("steps", []), key=lambda step: (step["order"], step["id"])):
        duration = step.get("duration_minutes")
        description = (
            f"Duração: {duration} min" if duration is not None else "Tempo ainda não informado."
        )
        work_type = {"direta": "direta", "indireta": "indireta"}.get(step.get("work_type"))
        if work_type:
            description += f"\nMão de obra {work_type}."
        blocks.append(
            {
                "id": f"step-{step['id']}",
                "section": "steps",
                "title": step["name"],
                "markdown": description,
                "checkable": True,
            }
        )
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
        "session_id": str(uuid4()),
        "completed_block_ids": [],
        "recipe_id": data["recipe_id"],
        "recipe_version": data["version"],
        "name": data["name"],
        "yield_quantity": data["yield_quantity"],
        "yield_unit": data["yield_unit"],
        "ingredients": ingredients,
        "blocks": blocks,
        "warnings": data["warnings"],
    }


def resume_completion(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    """Keep the current session when touch or voice reopens an unchanged recipe."""
    if previous and all(
        previous.get(key) == current[key] for key in ("recipe_id", "recipe_version")
    ):
        return {
            **current,
            "session_id": previous.get("session_id") or current["session_id"],
            "completed_block_ids": [
                bid
                for bid in previous.get("completed_block_ids", [])
                if any(b["id"] == bid and b.get("checkable") is True for b in current["blocks"])
            ],
        }
    return current


def update_completion(
    projection: dict[str, Any], block_id: str | None = None, completed: bool | None = None
) -> dict[str, Any]:
    """Return a new JSON value so SQLAlchemy persists the session checklist.

    Explicit desired state makes retries safe. A reset starts a fresh preparation
    session; recipe projections are invalidated on edits because IDs are positional.
    """
    if block_id is None:
        return {**projection, "session_id": str(uuid4()), "completed_block_ids": []}
    valid = {b["id"] for b in projection["blocks"] if b.get("checkable") is True}
    if block_id not in valid or completed is None:
        raise ValueError("Escolha uma etapa válida do preparo.")
    ids = set(projection.get("completed_block_ids", [])) & valid
    if completed:
        ids.add(block_id)
    else:
        ids.discard(block_id)
    return {
        **projection,
        "session_id": projection.get("session_id") or str(uuid4()),
        "completed_block_ids": sorted(ids),
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
    data = await snapshot(db, tenant_id, recipe_id, include_steps=True)
    return build_projection(data) if data else None


def active_block_index(projection: dict[str, Any] | None, section: str, current: int) -> int:
    if projection is None:
        return 0
    blocks = [block for block in projection["blocks"] if block["section"] == section]
    return min(max(current, 0), max(len(blocks) - 1, 0))
