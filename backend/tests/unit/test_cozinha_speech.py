from domain.cozinha.speech import (
    MAX_SPEECH_UNITS,
    ingredient_speech_parts,
    plain_text,
    projection_speech_parts,
)


def test_ingredient_parts_keep_registered_quantities_and_units() -> None:
    parts = ingredient_speech_parts(
        [
            {"name": "Farinha", "quantity": "250", "unit": "g"},
            {"name": "Leite", "quantity": "1,5", "unit": "xícara"},
        ]
    )

    assert parts == ["Farinha: 250 g; Leite: 1,5 xícara"]


def test_ingredient_list_splits_only_between_complete_items() -> None:
    ingredients = [
        {"name": f"Ingrediente {index} " + ("a" * 200), "quantity": "1", "unit": "g"}
        for index in range(8)
    ]

    parts = ingredient_speech_parts(ingredients)

    assert len(parts) > 1
    assert all(len(part.encode("utf-16-le")) // 2 <= MAX_SPEECH_UNITS for part in parts)
    assert all(f"Ingrediente {index}" in " ".join(parts) for index in range(8))


def test_markdown_links_urls_and_markup_become_plain_text() -> None:
    text = plain_text(
        "**Misture** [a massa](https://example.com)\n<speak>sem comandos</speak> www.example.com"
    )

    assert text == "Misture a massa sem comandos"
    assert "http" not in text
    assert "<" not in text


def test_long_content_is_chunked_and_unreadable_tokens_are_announced() -> None:
    parts = ingredient_speech_parts(
        [
            {"name": "A" * (MAX_SPEECH_UNITS + 5), "quantity": "1", "unit": "g"},
            {"name": "Açúcar", "quantity": "100", "unit": "g"},
        ]
    )

    assert len(parts) == 1
    assert "Açúcar: 100 g" in parts[0]
    assert "trecho longo demais" in parts[0]


def test_projection_uses_only_the_selected_preparation_block() -> None:
    projection = {
        "ingredients": [],
        "blocks": [
            {"section": "preparation", "markdown": "Misture os ingredientes."},
            {"section": "preparation", "markdown": "Leve ao forno."},
        ],
    }

    assert projection_speech_parts(projection, "preparation", 1) == ["Leve ao forno."]
