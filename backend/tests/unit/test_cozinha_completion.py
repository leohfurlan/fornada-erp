import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from domain.cozinha.service import build_projection, resume_completion, update_completion


def projection(recipe_id: str = "recipe-a") -> dict[str, Any]:
    return build_projection(
        {
            "recipe_id": recipe_id,
            "version": "v1",
            "name": "Bolo",
            "yield_quantity": "1",
            "yield_unit": "un",
            "ingredients": [],
            "sections": [{"title": "Modo de preparo", "text": "1. Misture\n2. Asse"}],
            "steps": [
                {
                    "id": "one",
                    "name": "Misturar",
                    "duration_minutes": 5,
                    "work_type": "direta",
                    "order": 0,
                },
                {
                    "id": "two",
                    "name": "Assar",
                    "duration_minutes": 30,
                    "work_type": "direta",
                    "order": 1,
                },
            ],
            "warnings": [],
        }
    )


def test_completion_is_reversible_out_of_order_and_idempotent() -> None:
    original = projection()
    result = update_completion(original, "step-two", True)
    assert result["completed_block_ids"] == ["step-two"]
    assert original["completed_block_ids"] == []
    assert update_completion(result, "step-two", True) == result
    result = update_completion(result, "step-one", True)
    assert len(result["completed_block_ids"]) == 2
    result = update_completion(result, "step-two", False)
    assert result["completed_block_ids"] == ["step-one"]


def test_json_recovery_preserves_session_and_reset_is_isolated() -> None:
    first = projection()
    other_recipe, other_session = projection("recipe-b"), projection()
    completed = update_completion(first, "step-one", True)
    restored = json.loads(json.dumps(completed))
    assert restored == completed
    assert restored["session_id"] == first["session_id"]
    reset = update_completion(restored)
    assert reset["session_id"] != first["session_id"]
    assert reset["completed_block_ids"] == []
    assert reset["blocks"] == first["blocks"]
    assert other_recipe["completed_block_ids"] == other_session["completed_block_ids"] == []
    assert len({first["session_id"], other_session["session_id"], reset["session_id"]}) == 3


def test_legacy_projection_gains_a_session_without_recipe_changes() -> None:
    legacy = projection()
    del legacy["session_id"]
    del legacy["completed_block_ids"]
    result = update_completion(legacy, "step-one", True)
    assert result["session_id"]
    assert result["completed_block_ids"] == ["step-one"]
    assert result["blocks"] == legacy["blocks"]


def test_reopening_recipe_resumes_only_the_same_recipe_and_version() -> None:
    first = update_completion(projection(), "step-one", True)
    resumed = resume_completion(first, projection())
    assert resumed["session_id"] == first["session_id"]
    assert resumed["completed_block_ids"] == ["step-one"]
    changed = {**projection(), "recipe_version": "v2"}
    assert resume_completion(first, changed)["completed_block_ids"] == []
    assert resume_completion(first, projection("recipe-b"))["completed_block_ids"] == []


async def test_alexa_reopening_keeps_the_checklist(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.routers import alexa

    completed = update_completion(projection(), "step-one", True)
    station = SimpleNamespace(projection=completed, revisao=1)
    monkeypatch.setattr(alexa, "recipe_projection", AsyncMock(return_value=projection()))
    await alexa._open_recipe(None, SimpleNamespace(tenant_id=uuid4()), station, uuid4(), "Bolo")
    assert station.projection["session_id"] == completed["session_id"]
    assert station.projection["completed_block_ids"] == ["step-one"]


@pytest.mark.parametrize(
    "block_id,completed", [("missing", True), ("ingredients-1", True), ("step-one", None)]
)
def test_rejects_invalid_steps(block_id: str, completed: bool | None) -> None:
    with pytest.raises(ValueError):
        update_completion(projection(), block_id, completed)
