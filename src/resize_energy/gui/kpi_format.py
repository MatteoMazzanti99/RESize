"""Pure helpers for the animated key-number tiles (no Qt, so they are testable)."""

from __future__ import annotations


def ease_out(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1.0 - (1.0 - x) ** 3


def format_value(value: float, decimals: int) -> str:
    """12345.6 -> '12,346' (decimals 0) or '0.056' (decimals 3); never '-0'."""
    text = f"{value:,.{decimals}f}"
    return text[1:] if text.startswith("-") and float(text.replace(",", "")) == 0 else text
