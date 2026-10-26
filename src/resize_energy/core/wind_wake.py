"""Wake losses of a wind farm with the Jensen (Park) model and a wind rose.

Pure calculation, no GUI. Turbines stand on a grid of rows perpendicular to the prevailing
wind; every wind direction sector and every wind speed is evaluated, the deficits of the
upwind turbines are combined by root-sum-square and the power curve gives the energy.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from resize_energy.core import wind

SECTORS = 12


def rose_weights(prevailing_deg: float, concentration: float, sectors: int = SECTORS) -> tuple[float, ...]:
    """Share of the time the wind comes from each sector (centres 0, 30, 60 ... degrees).

    ``concentration`` 0 gives a uniform rose; 1-2 is a typical site with a clear prevailing
    direction (von Mises shape)."""
    if concentration < 0:
        raise ValueError("concentration cannot be negative")
    raw = [math.exp(concentration * math.cos(math.radians(i * 360.0 / sectors - prevailing_deg)))
           for i in range(sectors)]
    total = sum(raw)
    return tuple(r / total for r in raw)


def grid_layout(n: int, per_row: int, crosswind_d: float, downwind_d: float, diameter_m: float,
                stagger: bool = True, prevailing_deg: float = 270.0) -> list[tuple[float, float]]:
    """East/north positions in metres of ``n`` turbines in rows of ``per_row``.

    Rows stand across the prevailing wind (which comes from ``prevailing_deg``), spaced
    ``downwind_d`` rotor diameters along it; ``crosswind_d`` is the spacing inside a row."""
    if n < 1 or per_row < 1:
        raise ValueError("turbines and turbines per row must be >= 1")
    pts = []
    for i in range(n):
        row, col = divmod(i, per_row)
        offset = 0.5 * crosswind_d * diameter_m if stagger and row % 2 == 1 else 0.0
        u = row * downwind_d * diameter_m
        w = col * crosswind_d * diameter_m + offset
        th = math.radians(prevailing_deg)
        pts.append((u * -math.sin(th) + w * math.cos(th), u * -math.cos(th) - w * math.sin(th)))
    return pts


def _overlap_fraction(r_wake: float, r_rotor: float, d: float) -> float:
    """Share of the rotor disc inside the wake cone (two circles at distance d)."""
    if d >= r_wake + r_rotor:
        return 0.0
    if d <= abs(r_wake - r_rotor):
        return 1.0 if r_wake >= r_rotor else (r_wake / r_rotor) ** 2
    a = (r_wake**2 * math.acos((d * d + r_wake**2 - r_rotor**2) / (2 * d * r_wake))
         + r_rotor**2 * math.acos((d * d + r_rotor**2 - r_wake**2) / (2 * d * r_rotor))
         - 0.5 * math.sqrt((-d + r_wake + r_rotor) * (d + r_wake - r_rotor)
                           * (d - r_wake + r_rotor) * (d + r_wake + r_rotor)))
    return a / (math.pi * r_rotor**2)


def thrust_coefficient(v: float, cut_in: float, rated: float, cut_out: float) -> float:
    """A generic thrust curve: 0.8 below rated speed, falling as 1/v^3 above it."""
    if v < cut_in or v >= cut_out:
        return 0.0
    if v <= rated:
        return 0.8
    return max(0.05, 0.8 * (rated / v) ** 3)


@dataclass(frozen=True)
class WakeResult:
    array_efficiency: float                 # energy with wakes / energy without
    turbine_efficiency: tuple[float, ...]   # per turbine, same order as the layout
    sector_efficiency: tuple[float, ...]    # per wind-direction sector
    sector_weights: tuple[float, ...]
    positions: tuple[tuple[float, float], ...]

    @property
    def wake_loss(self) -> float:
        return max(0.0, 1.0 - self.array_efficiency)


def wake_efficiency(
    positions: list[tuple[float, float]], power_kw: Callable[[float], float],
    diameter_m: float, hub_mean_ms: float, k_weibull: float, cut_in: float, rated: float,
    cut_out: float, decay: float, weights: tuple[float, ...],
    speed_factors: tuple[float, ...] | None = None,
) -> WakeResult:
    """Array efficiency of a layout for a wind rose and a Weibull wind-speed distribution.

    ``speed_factors`` (one per sector) scale the mean speed of each direction; without them
    every direction has the same speed distribution."""
    if not 0.01 <= decay <= 0.15:
        raise ValueError("wake decay constant must be between 0.01 and 0.15")
    if speed_factors is not None and len(speed_factors) != len(weights):
        raise ValueError("one speed factor per sector is needed")
    n = len(positions)
    speeds = [float(v) for v in range(int(math.ceil(cut_in)), int(cut_out))]

    def distribution(mean: float) -> list[float]:
        scale = wind.weibull_scale_from_mean(mean, k_weibull)
        return [wind.weibull_cdf(v + 0.5, k_weibull, scale)
                - wind.weibull_cdf(v - 0.5, k_weibull, scale) for v in speeds]

    probs_all = distribution(hub_mean_ms)
    r0 = diameter_m / 2.0
    sectors = len(weights)
    e_wake = [0.0] * n
    e_free = 0.0
    sector_eff: list[float] = []
    for s, wgt in enumerate(weights):
        if speed_factors is None:
            probs = probs_all
        elif speed_factors[s] > 0:
            probs = distribution(hub_mean_ms * speed_factors[s])
        else:
            probs = [0.0] * len(speeds)
        theta = math.radians(s * 360.0 / sectors)          # wind comes FROM theta
        dx, dy = -math.sin(theta), -math.cos(theta)         # direction of travel
        us = [x * dx + y * dy for x, y in positions]
        ws = [x * math.cos(theta) - y * math.sin(theta) for x, y in positions]
        order = sorted(range(n), key=lambda i: us[i])
        sec_wake = sec_free = 0.0
        for v, pv in zip(speeds, probs, strict=True):
            speed_at = [v] * n
            for jj, j in enumerate(order):
                total_sq = 0.0
                for i in order[:jj]:
                    x = us[j] - us[i]
                    if x <= 1e-6:
                        continue
                    ct_i = thrust_coefficient(speed_at[i], cut_in, rated, cut_out)
                    base_i = 1.0 - math.sqrt(max(0.0, 1.0 - ct_i))
                    r_w = r0 + decay * x
                    frac = _overlap_fraction(r_w, r0, abs(ws[j] - ws[i]))
                    if frac > 0.0:
                        total_sq += (base_i * (r0 / r_w) ** 2 * frac) ** 2
                speed_at[j] = v * (1.0 - math.sqrt(total_sq))
            p_free = power_kw(v)
            for i in range(n):
                e = pv * power_kw(speed_at[i])
                e_wake[i] += wgt * e
                sec_wake += pv * power_kw(speed_at[i])
            e_free += wgt * pv * p_free * n
            sec_free += pv * p_free * n
        sector_eff.append(sec_wake / sec_free if sec_free > 0 else 1.0)
    free_each = e_free / n if n else 0.0
    return WakeResult(
        array_efficiency=(sum(e_wake) / e_free) if e_free > 0 else 1.0,
        turbine_efficiency=tuple(e / free_each if free_each > 0 else 1.0 for e in e_wake),
        sector_efficiency=tuple(sector_eff), sector_weights=weights,
        positions=tuple(positions),
    )
