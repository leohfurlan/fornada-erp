"""Canonical names for recipes and commercial products; editorial text is untouched."""

import re
import unicodedata

EMOJI_PATTERN = (
    "[\U0001f000-\U0001faff\u2600-\u27bf\u2194-\u2199\u21a9-\u21aa"
    "\u231a-\u231b\u2328\u23cf\u23e9-\u23f3\u23f8-\u23fa\u24c2"
    "\u25aa-\u25ab\u25b6\u25c0\u25fb-\u25fe\u2934-\u2935"
    "\u2b05-\u2b07\u2b1b-\u2b1c\u2b50\u2b55\u3030\u303d\u3297\u3299"
    "\u00a9\u00ae\u203c\u2049\u2122\u2139\ufe0e\ufe0f\u20e3]"
)
_emoji = re.compile(EMOJI_PATTERN)


def nome_cadastro(value: str) -> str:
    """Reject emoji/invisible controls and persist the NFC uppercase name."""
    if not isinstance(value, str):
        raise ValueError("Informe o nome.")
    value = unicodedata.normalize("NFC", value)
    if _emoji.search(value):
        raise ValueError("O nome não pode conter emojis.")
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise ValueError("O nome não pode conter quebras de linha ou caracteres invisíveis.")
    value = " ".join(value.split()).upper()
    if not 1 <= len(value) <= 200:
        raise ValueError("Informe um nome de 1 a 200 caracteres.")
    return value


def padronizar_nome_existente(value: str) -> str:
    """Remove emoji in a reviewed legacy cleanup, preserving the remaining name."""
    value = _emoji.sub("", unicodedata.normalize("NFC", value))
    value = "".join(c for c in value if not unicodedata.category(c).startswith("C"))
    return nome_cadastro(value)
