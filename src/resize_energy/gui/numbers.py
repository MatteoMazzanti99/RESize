"""Tolerant number parsing for the GUI (no Qt imports, so it is unit-tested)."""

from __future__ import annotations

import math


def parse_number(text: str) -> float:
    """Parse a number typed by a user, accepting both ``45.07`` and ``45,07``.

    Rules: spaces are ignored; if both separators appear, the last one is the decimal
    separator and the other one a thousands separator ("1.500,5" and "1,500.5" are 1500.5);
    a single separator kind is read as decimal, unless it is repeated ("1.500.000" is a
    thousands grouping). Raises ValueError with a readable message otherwise.
    """
    s = text.strip().replace(" ", "").replace(" ", "")
    if not s:
        raise ValueError("enter a number")
    if "," in s and "." in s:
        decimal = "," if s.rfind(",") > s.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        s = s.replace(thousands, "").replace(decimal, ".")
    elif s.count(",") > 1:
        s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        value = float(s)
    except ValueError:
        raise ValueError(f"'{text.strip()}' is not a number") from None
    if not math.isfinite(value):
        raise ValueError(f"'{text.strip()}' is not a valid number")
    return value


def parse_in_range(text: str, lo: float, hi: float) -> float:
    """Parse and check that the value lies in [lo, hi]."""
    value = parse_number(text)
    if not lo <= value <= hi:
        raise ValueError(f"{value:g} is outside the allowed range {lo:g} to {hi:g}")
    return value


def format_number(value: float, decimals: int = 2) -> str:
    """Compact text for a value: no trailing zeros, always a decimal point."""
    text = f"{value:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
