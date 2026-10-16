from decimal import Decimal

import pytest

from domain.number_format import quantity_br


@pytest.mark.parametrize("value,expected", [
    ("120.0000", "120"), ("4.0000", "4"), ("1.0100", "1,01"),
    ("0.1250", "0,125"), ("1.23456", "1,235"), ("-0.00001", "0"),
])
def test_quantity_presentation(value, expected):
    original = Decimal(value)
    assert quantity_br(original) == expected
    assert str(original) == value
