"""The comparison as a series of rounds: one metric per round, one bar per technology.

Scores are 0..1 and only decide how long a bar is; the winner of a round is the technology
with the best real value. No overall verdict is made: which metric matters is up to you.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from resize_energy.core.comparison import ComparisonResult


@dataclass(frozen=True)
class Entry:
    key: str
    name: str
    value: float
    text: str
    score: float      # 0..1, bar length


@dataclass(frozen=True)
class Round:
    title: str
    hint: str
    entries: tuple[Entry, ...]
    winner: str | None   # name, or None for a tie


def _scores(values: list[float], lower_is_better: bool) -> list[float]:
    finite = [v for v in values if math.isfinite(v)]
    if not finite:
        return [0.0] * len(values)
    if lower_is_better:
        best = min(finite)
        return [0.0 if not math.isfinite(v) else (1.0 if v <= 0 else max(0.03, best / v))
                for v in values]
    top = max(finite)
    return [max(0.0, v) / top if top > 0 else 0.0 for v in values]


def _winner(names: list[str], values: list[float], lower_is_better: bool) -> str | None:
    ranked = sorted(range(len(values)), key=lambda i: values[i], reverse=not lower_is_better)
    first = values[ranked[0]]
    if not math.isfinite(first):
        return None
    if len(ranked) > 1:
        second = values[ranked[1]]
        if math.isclose(first, second, rel_tol=1e-9):
            return None
    return names[ranked[0]]


def _money(v: float) -> str:
    return f"{v / 1e6:,.1f} M euro" if abs(v) >= 1e6 else f"{v:,.0f} euro"


def versus_rounds(r: ComparisonResult) -> list[Round]:
    """Four rounds: cost of energy, payback, net present value, CO2 avoided."""
    techs = r.techs
    names = [t.name for t in techs]
    specs = (
        ("Cost of one kWh", "lowest wins", True, [t.lcoe_eur_per_kwh for t in techs],
         lambda v: f"{v:.3f} euro/kWh"),
        ("Payback time", "shortest wins", True, [t.payback_years for t in techs],
         lambda v: f"{v:.1f} years" if math.isfinite(v) else "never"),
        ("Net present value", "highest wins", False, [t.npv_eur for t in techs], _money),
        ("CO2 avoided", "most wins", False, [t.co2_avoided_t_per_year for t in techs],
         lambda v: f"{v:,.0f} t per year"),
    )
    rounds = []
    for title, hint, lower, values, fmt in specs:
        scores = _scores(values, lower)
        entries = tuple(Entry(t.key, t.name, v, fmt(v), s)
                        for t, v, s in zip(techs, values, scores, strict=True))
        rounds.append(Round(title, hint, entries, _winner(names, values, lower)))
    return rounds


def rounds_won(rounds: list[Round]) -> dict[str, int]:
    """How many rounds each technology won (every technology is listed, ties count for none)."""
    wins = {e.name: 0 for e in rounds[0].entries} if rounds else {}
    for rd in rounds:
        if rd.winner is not None:
            wins[rd.winner] += 1
    return wins
