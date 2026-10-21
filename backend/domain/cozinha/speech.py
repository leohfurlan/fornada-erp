"""Safe, deterministic speech chunks for recipe content shown in the kitchen."""

import html
import re
from collections.abc import Iterable

MAX_SPEECH_UNITS = 1200
_MARKDOWN_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_ACTIVE_HTML = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_HTML_TAG = re.compile(r"<[^>]*>")
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_MARKDOWN_PREFIX = re.compile(r"^\s*(?:#{1,6}\s*|>\s*|[-*+]\s+|\d+[.)]\s+)", re.MULTILINE)
_MARKDOWN_MARKS = re.compile(r"(?:\*\*|__|~~|`|\*|_)")


def _units(value: str) -> int:
    return len(value.encode("utf-16-le", errors="replace")) // 2


def plain_text(markdown: str) -> str:
    """Remove active-looking markup and URLs while retaining readable labels and text."""
    value = _MARKDOWN_LINK.sub(r"\1", markdown)
    value = html.unescape(value)
    value = _ACTIVE_HTML.sub(" ", value)
    value = _HTML_TAG.sub(" ", value)
    value = _URL.sub(" ", value)
    value = _MARKDOWN_PREFIX.sub("", value)
    value = _MARKDOWN_MARKS.sub("", value)
    return re.sub(r"\s+", " ", value).strip()


def _bounded_words(text: str, max_units: int) -> tuple[list[str], bool]:
    words = text.split()
    chunks: list[str] = []
    current = ""
    omitted_long_token = False
    for word in words:
        if _units(word) > max_units:
            if current:
                chunks.append(current)
                current = ""
            omitted_long_token = True
            continue
        candidate = f"{current} {word}".strip()
        if current and _units(candidate) > max_units:
            chunks.append(current)
            current = word
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks, omitted_long_token


def chunk_speech(
    items: Iterable[str], *, max_units: int = MAX_SPEECH_UNITS, atomic_items: bool = False
) -> list[str]:
    """Pack complete lines into bounded parts and never silently truncate long text."""
    parts: list[str] = []
    current = ""
    omitted_long_token = False
    for raw_item in items:
        cleaned = plain_text(raw_item)
        if not cleaned:
            continue
        if _units(cleaned) <= max_units:
            candidates = [cleaned]
        else:
            candidates, omitted = _bounded_words(cleaned, max_units)
            omitted_long_token = omitted_long_token or omitted
            if atomic_items and omitted:
                continue
        for candidate in candidates:
            combined = f"{current}; {candidate}" if current else candidate
            if current and _units(combined) > max_units:
                parts.append(current)
                current = candidate
            else:
                current = combined
    if current:
        parts.append(current)
    if omitted_long_token:
        notice = "Há um trecho longo demais para leitura por voz; consulte-o na tela."
        if parts and _units(f"{parts[-1]} {notice}") <= max_units:
            parts[-1] = f"{parts[-1]} {notice}"
        else:
            parts.append(notice)
    return parts


def ingredient_speech_parts(ingredients: list[dict]) -> list[str]:
    items = []
    for ingredient in ingredients:
        name = str(ingredient.get("name") or "").strip()
        quantity = str(ingredient.get("quantity") or "").strip()
        unit = str(ingredient.get("unit") or "").strip()
        if name:
            amount = " ".join(value for value in (quantity, unit) if value)
            items.append(f"{name}: {amount}" if amount else name)
    return chunk_speech(items, atomic_items=True)


def projection_speech_parts(projection: dict, section: str, block_index: int) -> list[str]:
    if section == "ingredients":
        return ingredient_speech_parts(projection.get("ingredients", []))
    blocks = [block for block in projection.get("blocks", []) if block.get("section") == section]
    if not blocks:
        return []
    current = blocks[min(max(block_index, 0), len(blocks) - 1)]
    return chunk_speech([current.get("markdown", "")])
