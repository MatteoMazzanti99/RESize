"""Pure parts of the restyle: key-number formatting and the colour themes."""

from resize_energy.gui import theme
from resize_energy.gui.kpi_format import ease_out, format_value


def test_ease_out_runs_from_zero_to_one():
    assert ease_out(-1) == 0.0 and ease_out(2) == 1.0
    assert 0.0 < ease_out(0.3) < 1.0
    assert ease_out(0.5) > 0.5


def test_format_value_never_shows_negative_zero():
    assert format_value(12345.6, 0) == "12,346"
    assert format_value(0.056, 3) == "0.056"
    assert format_value(-0.0001, 2) == "0.00"


def _luminance(hex_color: str) -> float:
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_both_themes_are_readable():
    try:
        for name in theme.THEMES:
            theme.use_theme(name)
            c = theme.COLORS
            assert _contrast(c["text"], c["bg"]) >= 7
            assert _contrast(c["muted"], c["surface"]) >= 4.5
            assert _contrast(c["accent_text"], c["accent"]) >= 4.5
    finally:
        theme.use_theme("light")
