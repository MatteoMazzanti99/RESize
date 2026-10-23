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
    gap = [p_el_kw - u for u in used] if use_grid else [0.0] * HOURS
    potential = sum(gap)
    scale = min(1.0, grid_hours_cap * p_el_kw / potential) if potential > 0 else 0.0
    res_used = grid = 0.0
    pv_used = wind_used = 0.0
    hours_on = 0
    for t in range(HOURS):
        g = scale * gap[t]
        total = used[t] + g
        if total < p_min or total <= 0:
            continue
        hours_on += 1
        res_used += used[t]
        grid += g
        if res[t] > 0:
            share = used[t] / res[t]
            pv_used += pv_w[t] * share
            wind_used += wd_w[t] * share
    electricity = res_used + grid
    return DispatchResult(
        res_available_kwh=sum(res), res_used_kwh=res_used, grid_kwh=grid,
        electricity_kwh=electricity, hydrogen_kg=electricity / kwh_per_kg, hours_on=hours_on,
        pv_used_kwh=pv_used, wind_used_kwh=wind_used,
    )
