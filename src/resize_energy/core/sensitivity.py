"""One-at-a-time sensitivity analysis: change an input by a few percent, watch the result.

Pure calculation, no GUI. ``evaluate`` receives a dict {key: factor} (1.0 = the value you
chose, 0.8 = 20 % less) and returns the number to follow (a cost, a net present value...).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

STEPS: tuple[float, ...] = (-0.20, -0.10, 0.0, 0.10, 0.20)


@dataclass(frozen=True)
class Parameter:
    key: str
    label: str


@dataclass(frozen=True)
class Curve:
    label: str
    values: tuple[float, ...]       # the result at each step

    @property
    def swing(self) -> float:
        """Difference between the highest and the lowest result."""
        return max(self.values) - min(self.values)


@dataclass(frozen=True)
class Sensitivity:
    metric: str                     # e.g. "Cost of hydrogen"
    unit: str                       # e.g. "euro/kg"
    base: float
    steps: tuple[float, ...]
    curves: tuple[Curve, ...]       # sorted: the most influential first
    decimals: int = 2

    def most_influential(self) -> Curve:
        return self.curves[0]

    def relative_swing(self, curve: Curve) -> float:
        """Half of the swing as a share of the base (the effect of a +/- step)."""
        return curve.swing / 2.0 / abs(self.base) if self.base else 0.0


def one_at_a_time(
    evaluate: Callable[[dict[str, float]], float], parameters: Sequence[Parameter],
    metric: str, unit: str, steps: Sequence[float] = STEPS, decimals: int = 2,
) -> Sensitivity:
    """Vary each parameter alone through ``steps`` (fractions: -0.2 = 20 % less)."""
    if not parameters:
        raise ValueError("give at least one parameter")
    if 0.0 not in steps:
        raise ValueError("the steps must include 0 (the base case)")
    if any(s <= -1.0 for s in steps):
        raise ValueError("a step of -100 % or less makes no sense")
    base = evaluate({})
    curves = []
    for p in parameters:
        values = tuple(base if s == 0.0 else evaluate({p.key: 1.0 + s}) for s in steps)
        curves.append(Curve(p.label, values))
    curves.sort(key=lambda c: c.swing, reverse=True)
    return Sensitivity(metric, unit, base, tuple(steps), tuple(curves), decimals)
