"""Digit translation for locales with native numeral systems."""

from __future__ import annotations

DIGIT_MAP_LENGTH = 10


def valid_digit_map(value: object) -> tuple[str, ...] | None:
    """Return the digit map as a tuple when it maps all ten digits."""
    if isinstance(value, (list, tuple)) and len(value) == DIGIT_MAP_LENGTH:
        return tuple(str(digit) for digit in value)
    return None


def translate_digits(text: str, digit_map: tuple[str, ...] | None) -> str:
    """Replace Western digits in ``text`` using ``digit_map`` when present."""
    if digit_map is None:
        return text
    return "".join(digit_map[int(ch)] if ch.isdigit() else ch for ch in text)
