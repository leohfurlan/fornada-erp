"""Preserve field locations when a schema rule compares multiple fields."""

from pydantic import ValidationError


def field_error(path: tuple[str | int, ...], message: str) -> ValidationError:
    return ValidationError.from_exception_data(
        "Preenchimento",
        [
            {
                "type": "value_error",
                "loc": path,
                "input": None,
                "ctx": {"error": ValueError(message)},
            }
        ],
    )
