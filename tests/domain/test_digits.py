"""Domain digit translation tests."""

from __future__ import annotations

from fancyclock.domain.digits import (
    DIGIT_MAP_LENGTH,
    translate_digits,
    valid_digit_map,
)

ARABIC_DIGITS = ("٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩")


def test_valid_digit_map_accepts_ten_entries() -> None:
    assert valid_digit_map(list(ARABIC_DIGITS)) == ARABIC_DIGITS
    assert valid_digit_map(ARABIC_DIGITS) == ARABIC_DIGITS


def test_valid_digit_map_rejects_wrong_shapes() -> None:
    assert valid_digit_map(None) is None
    assert valid_digit_map("0123456789") is None
    assert valid_digit_map(list(ARABIC_DIGITS)[: DIGIT_MAP_LENGTH - 1]) is None


def test_translate_digits_maps_digits_and_keeps_other_chars() -> None:
    assert translate_digits("12:03", ARABIC_DIGITS) == "١٢:٠٣"


def test_translate_digits_without_map_returns_input() -> None:
    assert translate_digits("12:03", None) == "12:03"
