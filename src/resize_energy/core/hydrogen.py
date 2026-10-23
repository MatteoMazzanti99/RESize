"""Building blocks of green hydrogen sizing: energy content, compression, storage, dispatch.

Pure functions, no GUI. Energies in kWh, masses in kg, pressures in bar.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

H2_LHV_KWH_PER_KG = 33.33
H2_HHV_KWH_PER_KG = 39.41
WATER_STOICHIOMETRIC_KG_PER_KG = 8.94   # 18.015 / 2.016 for H2O -> H2
OXYGEN_KG_PER_KG = 7.94                 # by-product
H2_GAS_CONSTANT_J_PER_KG_K = 4124.0     # R / M for hydrogen
HOURS = 8760


def system_efficiency_lhv(kwh_per_kg: float) -> float:
    """Electricity-to-hydrogen efficiency on the lower heating value."""
    if kwh_per_kg <= 0:
        raise ValueError("specific consumption must be > 0")
    return H2_LHV_KWH_PER_KG / kwh_per_kg


def compression_kwh_per_kg(p_in_bar: float, p_out_bar: float, temperature_k: float = 298.0,
                           isothermal_efficiency: float = 0.60) -> float:
    """Work to compress hydrogen: isothermal work R T ln(p2/p1) divided by the efficiency."""
    if p_in_bar <= 0 or p_out_bar < p_in_bar:
        raise ValueError("outlet pressure must be >= inlet pressure > 0")
    if not 0 < isothermal_efficiency <= 1:
        raise ValueError("isothermal efficiency must be in (0, 1]")
    work_j = H2_GAS_CONSTANT_J_PER_KG_K * temperature_k * math.log(p_out_bar / p_in_bar)
    return work_j / 3.6e6 / isothermal_efficiency


def hydrogen_density_kg_m3(pressure_bar: float, temperature_k: float = 288.0) -> float:
    """Density with a simple real-gas correction Z = 1 + 0.0006 p (within about 5 % to 700 bar)."""
    if pressure_bar <= 0:
        raise ValueError("pressure must be > 0")
    z = 1.0 + 0.0006 * pressure_bar
    return pressure_bar * 1e5 / (z * H2_GAS_CONSTANT_J_PER_KG_K * temperature_k)


def storage_volume_m3(mass_kg: float, pressure_bar: float) -> float:
    """Geometric volume of the tanks needed to hold ``mass_kg`` at ``pressure_bar``."""
    return mass_kg / hydrogen_density_kg_m3(pressure_bar)


def part_load_factor(load: float, aux_share: float = 0.06, stack_gain: float = 0.12) -> float:
    """Specific consumption at ``load`` (0-1 of nominal) relative to nominal load.

    The stack is a little more efficient at part load (lower current density, gain
    ``stack_gain`` when the load goes to zero) but the auxiliaries (pumps, cooling, power
    electronics) draw a fixed power ``aux_share`` of nominal, so per kilogram they weigh 1/load.
    The factor is 1 at nominal load.
    """
    if load <= 0:
        raise ValueError("load must be > 0")
    x = min(load, 1.0)
    return (1.0 - aux_share) * (1.0 - stack_gain * (1.0 - x)) + aux_share / x


def ageing_factor(operating_hours: float, degradation_per_1000h: float) -> float:
    """Specific consumption of an aged stack relative to a new one (linear voltage drift)."""
    return 1.0 + degradation_per_1000h * operating_hours / 1000.0


def synthetic_price_profile(mean_eur_per_kwh: float, seed: int = 5) -> tuple[float, ...]:
    """An invented hourly electricity price with the typical shape, mean = ``mean``.

    Evening peak, cheap nights, a dip at midday in summer (solar), dearer winters and noise.
    """
    import random

    rng = random.Random(seed)
    raw: list[float] = []
    for day in range(365):
        winter = 1.0 + 0.25 * math.cos(2.0 * math.pi * (day - 15) / 365.0)
        summer = 1.0 - winter + 1.0   # 0.75 .. 1.25 mirror of winter, 1 + 0.25 cos shifted
        weekend = 0.88 if day % 7 in (5, 6) else 1.0
        for hour in range(24):
            shape = (0.85 + 0.35 * math.exp(-((hour - 19.5) / 2.0) ** 2)
                     + 0.18 * math.exp(-((hour - 8.0) / 1.8) ** 2)
                     - 0.30 * summer * math.exp(-((hour - 13.0) / 2.5) ** 2) * 0.8)
            raw.append(max(0.05, shape * winter * weekend * (1.0 + rng.gauss(0.0, 0.08))))
    avg = sum(raw) / len(raw)
    return tuple(mean_eur_per_kwh * v / avg for v in raw)


@dataclass(frozen=True)
class DispatchResult:
    res_available_kwh: float     # renewable energy that the plant could produce
    res_used_kwh: float          # ... and that the electrolyser really used
    grid_kwh: float
    electricity_kwh: float       # used by the electrolyser system (renewable + grid)
    hydrogen_kg: float
    hours_on: int
    pv_used_kwh: float
    wind_used_kwh: float
    monthly_res_kwh: tuple[float, ...] = ()    # renewable energy used, per month
    monthly_grid_kwh: tuple[float, ...] = ()   # grid energy used, per month
    hydrogen_kg_year1: float = 0.0             # first year, new stack
    kg_by_year: tuple[float, ...] = ()         # every year of the electrolyser life (ageing)
    hourly_kg: tuple[float, ...] = ()          # hydrogen made in each hour of year 1
    grid_cost_eur: float = 0.0                 # with hourly prices when given, else 0
    load_hist_kwh: tuple[float, ...] = ()      # electricity used by load class (10 classes)


_MONTH_START_H = tuple(d * 24 for d in (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334))


def _month_of_hour() -> list[int]:
    out: list[int] = []
    for m in range(12):
        end = _MONTH_START_H[m + 1] if m < 11 else HOURS
        out += [m] * (end - _MONTH_START_H[m])
    return out


_MONTH_OF = _month_of_hour()
MONTH_OF_HOUR = _MONTH_OF   # month index (0..11) of each hour of the year


def simulate_dispatch(
    pv_unit: Sequence[float] | None,
    wind_unit: Sequence[float] | None,
    p_pv_kwp: float,
    p_wind_kw: float,
    p_el_kw: float,
    min_load: float,
    kwh_per_kg: float,
    use_grid: bool,
    grid_hours_cap: float,
    *,
    compression_kwh_per_kg: float = 0.0,
    part_load: bool = False,
    aux_share: float = 0.06,
    stack_gain: float = 0.12,
    degradation_per_1000h: float = 0.0,
    stack_hours: float = 60_000.0,
    life_years: float = 1.0,
    grid_prices: Sequence[float] | None = None,
    cheapest_hours_first: bool = False,
) -> DispatchResult:
    """Run the electrolyser for a year, hour by hour.

    Renewable power goes first, up to the nominal power; below the minimum load the
    electrolyser stays off. With the grid enabled, the gap to nominal power is filled in
    every hour in the same proportion, so that the total grid energy does not exceed
    ``grid_hours_cap`` equivalent full-load hours.
    """
    if p_el_kw <= 0:
        raise ValueError("electrolyser power must be > 0")
    if not 0.0 <= min_load < 1.0:
        raise ValueError("minimum load must be in [0, 1)")
    pv_w = [0.0] * HOURS if not pv_unit or p_pv_kwp <= 0 else [p_pv_kwp * x for x in pv_unit]
    wd_w = [0.0] * HOURS if not wind_unit or p_wind_kw <= 0 else [p_wind_kw * x for x in wind_unit]
    if len(pv_w) != HOURS or len(wd_w) != HOURS:
        raise ValueError("profiles must have 8760 values")
    p_min = min_load * p_el_kw
    res = [a + b for a, b in zip(pv_w, wd_w, strict=True)]
    used = [min(r, p_el_kw) for r in res]
    if grid_prices is not None and len(grid_prices) != HOURS:
        raise ValueError("hourly prices need 8760 values")
    gap = [p_el_kw - u for u in used] if use_grid else [0.0] * HOURS
    potential = sum(gap)
    budget = grid_hours_cap * p_el_kw
    grid_hour = [0.0] * HOURS
    if potential > 0:
        if cheapest_hours_first and grid_prices is not None:
            left = budget
            for t in sorted(range(HOURS), key=lambda i: grid_prices[i]):
                take = min(gap[t], left)
                if take <= 0:
                    if left <= 0:
                        break
                    continue
                grid_hour[t] = take
                left -= take
        else:
            scale = min(1.0, budget / potential)
            grid_hour = [scale * g for g in gap]
    res_used = grid = 0.0
    pv_used = wind_used = 0.0
    hours_on = 0
    m_res = [0.0] * 12
    m_grid = [0.0] * 12
    hourly_kg = [0.0] * HOURS
    hist = [0.0] * 10
    grid_cost = 0.0
    stack_kwh = max(kwh_per_kg - compression_kwh_per_kg, 1e-9)
    for t in range(HOURS):
        g = grid_hour[t]
        total = used[t] + g
        if total < p_min or total <= 0:
            continue
        hours_on += 1
        res_used += used[t]
        grid += g
        if grid_prices is not None:
            grid_cost += g * grid_prices[t]
        m_res[_MONTH_OF[t]] += used[t]
        m_grid[_MONTH_OF[t]] += g
        x = total / p_el_kw
        hist[min(9, int(x * 10))] += total
        if part_load:
            hourly_kg[t] = total / (stack_kwh * part_load_factor(x, aux_share, stack_gain)
                                    + compression_kwh_per_kg)
        else:
            hourly_kg[t] = total / kwh_per_kg
        if res[t] > 0:
            share = used[t] / res[t]
            pv_used += pv_w[t] * share
            wind_used += wd_w[t] * share
    electricity = res_used + grid
    kg1 = sum(hourly_kg)
    # ageing: the stack drifts with the hours it has run; a new one is fitted after stack_hours
    years = max(1, round(life_years))
    stack_frac = stack_kwh / kwh_per_kg
    by_year: list[float] = []
    for y in range(years):
        age = (y + 0.5) * hours_on
        age = age % stack_hours if stack_hours > 0 else age
        by_year.append(kg1 / (1.0 + degradation_per_1000h * age / 1000.0 * stack_frac))
    kg_avg = sum(by_year) / len(by_year)
    return DispatchResult(
        res_available_kwh=sum(res), res_used_kwh=res_used, grid_kwh=grid,
        electricity_kwh=electricity, hydrogen_kg=kg_avg, hours_on=hours_on,
        pv_used_kwh=pv_used, wind_used_kwh=wind_used,
        monthly_res_kwh=tuple(m_res), monthly_grid_kwh=tuple(m_grid),
        hydrogen_kg_year1=kg1, kg_by_year=tuple(by_year), hourly_kg=tuple(hourly_kg),
        grid_cost_eur=grid_cost, load_hist_kwh=tuple(hist),
    )
