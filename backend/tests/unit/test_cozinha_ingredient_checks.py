import json

import pytest

from domain.cozinha.service import build_projection, resume_completion, update_ingredient_checks


def projection() -> dict:
    return build_projection({
        "recipe_id": "recipe", "version": "v1", "name": "Bolo",
        "yield_quantity": "1", "yield_unit": "un", "warnings": [], "sections": [],
        "ingredients": [{"name": "Farinha", "quantity": "0.5", "unit": "kg"}],
    })


def test_checks_are_reversible_idempotent_and_independent_of_steps() -> None:
    original = projection()
    checked = update_ingredient_checks(original, "ingredient-0", True)
    assert checked["checked_ingredient_ids"] == ["ingredient-0"]
    assert checked["completed_block_ids"] == original["completed_block_ids"] == []
    assert original["checked_ingredient_ids"] == []
    assert update_ingredient_checks(checked, "ingredient-0", True) == checked
    assert update_ingredient_checks(checked, "ingredient-0", False)["checked_ingredient_ids"] == []


def test_recovery_is_scoped_to_recipe_version_and_session() -> None:
    checked = json.loads(json.dumps(update_ingredient_checks(projection(), "ingredient-0", True)))
    restored = resume_completion(checked, projection())
    assert restored["checked_ingredient_ids"] == ["ingredient-0"]
    assert restored["session_id"] == checked["session_id"]
    for changes in [{"recipe_id": "other"}, {"recipe_version": "v2"}]:
        fresh = resume_completion(checked, {**projection(), **changes})
        assert fresh["checked_ingredient_ids"] == []
        assert fresh["session_id"] != checked["session_id"]


def test_legacy_sessions_can_check_ingredients_without_new_ids() -> None:
    legacy = projection()
    del legacy["ingredients"][0]["id"]
    del legacy["checked_ingredient_ids"]
    assert update_ingredient_checks(legacy, "ingredient-0", True)["checked_ingredient_ids"] == ["ingredient-0"]


@pytest.mark.parametrize("item_id,state", [("ingredient-1", True), ("step-one", True), (None, True), ("ingredient-0", None)])
def test_rejects_invalid_ingredient_commands(item_id: str | None, state: bool | None) -> None:
    with pytest.raises(ValueError):
        update_ingredient_checks(projection(), item_id, state)
