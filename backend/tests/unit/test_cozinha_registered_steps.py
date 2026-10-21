from types import SimpleNamespace

import pytest

from domain.cozinha.service import build_projection, update_completion
from domain.cozinha.speech import projection_speech_parts


def recipe() -> dict:
    return {
        "recipe_id": "cake",
        "version": "v1",
        "name": "Bolo",
        "yield_quantity": "1",
        "yield_unit": "un",
        "ingredients": [],
        "warnings": [],
        "sections": [
            {"title": "Modo de preparo", "text": "1. Texto de leitura\n2. Outra instrução"},
            {"title": "Montagem 1", "text": "Sirva em uma travessa."},
        ],
        "steps": [
            {
                "id": "registered-b",
                "name": "Fornear",
                "duration_minutes": 30,
                "work_type": "direta",
                "order": 1,
            },
            {
                "id": "registered-a",
                "name": "Organizar bancada",
                "duration_minutes": 5,
                "work_type": "indireta",
                "order": 0,
            },
        ],
    }


def test_checklist_uses_registered_steps_and_stable_identifiers() -> None:
    projection = build_projection(recipe())
    steps = [block for block in projection["blocks"] if block.get("checkable")]
    assert [(block["id"], block["title"]) for block in steps] == [
        ("step-registered-a", "Organizar bancada"),
        ("step-registered-b", "Fornear"),
    ]
    assert "30 min" in steps[1]["markdown"]
    assert len([b for b in projection["blocks"] if b["section"] == "preparation"]) == 1
    assert "Texto de leitura" in " ".join(projection_speech_parts(projection, "preparation", 0))


def test_text_without_registered_steps_has_no_checklist() -> None:
    data = recipe()
    data["steps"] = []
    projection = build_projection(data)
    assert not any(block.get("checkable") for block in projection["blocks"])
    for block in projection["blocks"]:
        with pytest.raises(ValueError):
            update_completion(projection, block["id"], True)


def test_alexa_reads_preparation_text_without_announcing_checklist_position() -> None:
    from api.routers.alexa import _speak_current_part

    projection = build_projection(recipe())
    station = SimpleNamespace(
        projection=projection, secao="preparation", bloco_indice=0, parte_fala_indice=0
    )
    spoken = _speak_current_part(station)
    assert "Texto de leitura" in spoken
    assert "etapa 1 de" not in spoken
