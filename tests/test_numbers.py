import pytest

from resize_energy.gui.numbers import format_number, parse_in_range, parse_number


@pytest.mark.parametrize("text, expected", [
    ("45.07", 45.07),
    ("45,07", 45.07),
    (" 1500 ", 1500.0),
    ("-10", -10.0),
    ("1.500,5", 1500.5),
    ("1,500.5", 1500.5),
    ("1.500.000", 1500000.0),
    ("1,500,000", 1500000.0),
    ("0,8", 0.8),
    ("1 234,5", 1234.5),
])
def test_parse_number_accepts_point_and_comma(text, expected):
    assert parse_number(text) == pytest.approx(expected)


@pytest.mark.parametrize("bad", ["", "   ", "abc", "1.2.3a", "nan", "inf", "12 kWh"])
def test_parse_number_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_number(bad)


def test_parse_in_range():
    assert parse_in_range("30", 0, 90) == pytest.approx(30.0)
    with pytest.raises(ValueError) as info:
        parse_in_range("120", 0, 90)
    assert "outside the allowed range" in str(info.value)


def test_format_number():
    assert format_number(45.07, 4) == "45.07"
    assert format_number(1500.0, 0) == "1500"
    assert format_number(0.8, 2) == "0.8"
    assert format_number(-10.0, 0) == "-10"
