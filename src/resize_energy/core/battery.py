"""Hourly model of a battery next to a photovoltaic and/or wind plant (self-consumption).

Rule: the energy produced serves the load first; the surplus charges the battery (within
its power and its free capacity) and the rest is exported; when the load is higher than the
production the battery discharges (within its power and the energy it holds) and the rest is
imported from the grid. Pure calculation, no GUI.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from resize_energy.core.hydrogen import MONTH_OF_HOUR

HOURS = 8760
LOAD_KINDS: dict[str, str] = {
    "residential": "Home: morning and evening peaks, more in winter",
    "commercial": "Office or shop: weekdays 8-18, low at night and at weekends",
    "industrial": "Industry: nearly flat, three shifts, a little less at weekends",
    "flat": "Flat: the same power every hour",
}


def load_profile(annual_kwh: float, kind: str = "residential", seed: int = 3) -> tuple[float, ...]:
    """Hourly load [kW] with the typical shape of ``kind`` and a yearly total of ``annual_kwh``."""
    if annual_kwh <= 0:
        raise ValueError("the yearly demand must be > 0")
    if kind not in LOAD_KINDS:
        raise ValueError(f"unknown load type {kind!r}")
    rng = random.Random(seed)
    shape: list[float] = []
    for day in range(365):
        weekend = day % 7 in (5, 6)
        winter = 1.0 + 0.15 * math.cos(2.0 * math.pi * (day - 15) / 365.0)
        for hour in range(24):
            if kind == "residential":
                morning = 0.55 * math.exp(-((hour - 7.5) / 1.6) ** 2)
                evening = 1.0 * math.exp(-((hour - 20.0) / 2.2) ** 2)
                midday = 0.25 * math.exp(-((hour - 13.0) / 2.5) ** 2) * (1.6 if weekend else 1.0)
                value = (0.30 + morning + evening + midday) * winter
            elif kind == "commercial":
                working = (not weekend) and 8 <= hour < 18
                value = (1.0 if working else 0.2 if not weekend else 0.25) * (
                    1.0 + 0.5 * (winter - 1.0))
            elif kind == "industrial":
                value = (0.7 if weekend else 1.0) * (1.0 + 0.3 * (winter - 1.0))
            else:
                value = 1.0
            shape.append(value * (1.0 + rng.uniform(-0.05, 0.05)))
    total = sum(shape)
    return tuple(v * annual_kwh / total for v in shape)


@dataclass(frozen=True)
class BatteryRun:
    """One simulated year (energies in kWh)."""

    load_kwh: float
    generation_kwh: float
    direct_kwh: float          # produced and used at the same hour
    charge_kwh: float          # energy sent to the battery (AC side)
    discharge_kwh: float       # energy delivered by the battery (AC side)
    import_kwh: float
    export_kwh: float
    monthly_direct: tuple[float, ...]
    monthly_battery: tuple[float, ...]
    monthly_import: tuple[float, ...]
    soc: tuple[float, ...]     # energy stored at the end of each hour [kWh]
    hourly_import: tuple[float, ...]


def simulate_battery(
    generation_kw: Sequence[float], load_kw: Sequence[float], capacity_kwh: float,
    power_kw: float, eta_roundtrip: float = 0.90, usable_fraction: float = 0.90,
    health: float = 0.90, soc0: float = 0.5,
) -> BatteryRun:
    """Run the year. ``capacity_kwh = 0`` gives the case without battery."""
    if len(generation_kw) != HOURS or len(load_kw) != HOURS:
        raise ValueError("generation and load need 8760 hourly values")
    if capacity_kwh < 0 or power_kw < 0:
        raise ValueError("capacity and power cannot be negative")
    if not 0.0 < eta_roundtrip <= 1.0 or not 0.0 < usable_fraction <= 1.0:
        raise ValueError("efficiency and usable fraction must be in (0, 1]")
    if not 0.0 < health <= 1.0 or not 0.0 <= soc0 <= 1.0:
        raise ValueError("health must be in (0, 1] and the initial charge in [0, 1]")
    eta = math.sqrt(eta_roundtrip)            # the same loss when charging and discharging
    room = capacity_kwh * usable_fraction * health   # energy the battery can really hold
    e = room * soc0
    direct = charge = discharge = imp = exp = 0.0
    m_direct = [0.0] * 12
    m_batt = [0.0] * 12
    m_imp = [0.0] * 12
    soc: list[float] = []
    h_imp: list[float] = []
    for t in range(HOURS):
        g, d = generation_kw[t], load_kw[t]
        m = MONTH_OF_HOUR[t]
        used = min(g, d)
        direct += used
        m_direct[m] += used
        net = g - d
        imported = 0.0
        if net > 0.0:
            c_in = min(net, power_kw, (room - e) / eta) if room > 0 else 0.0
            c_in = max(c_in, 0.0)
            e += c_in * eta
            charge += c_in
            exp += net - c_in
        else:
            need = -net
            out = min(need, power_kw, e * eta) if room > 0 else 0.0
            out = max(out, 0.0)
            e -= out / eta
            discharge += out
            m_batt[m] += out
            imported = need - out
            imp += imported
            m_imp[m] += imported
        soc.append(e)
        h_imp.append(imported)
    return BatteryRun(
        load_kwh=float(sum(load_kw)), generation_kwh=float(sum(generation_kw)), direct_kwh=direct,
        charge_kwh=charge, discharge_kwh=discharge, import_kwh=imp, export_kwh=exp,
        monthly_direct=tuple(m_direct), monthly_battery=tuple(m_batt),
        monthly_import=tuple(m_imp), soc=tuple(soc), hourly_import=tuple(h_imp),
    )


def self_sufficiency(run: BatteryRun) -> float:
    """Share of the load met without the grid."""
    return 1.0 - run.import_kwh / run.load_kwh if run.load_kwh > 0 else 0.0


def self_consumption(run: BatteryRun) -> float:
    """Share of the production used on site (directly or through the battery)."""
    if run.generation_kwh <= 0:
        return 0.0
    return (run.direct_kwh + run.charge_kwh) / run.generation_kwh
