"""Preliminary design of a battery for a photovoltaic and/or wind plant (self-consumption).

Three ways to size: a capacity you choose, the smallest battery that reaches a target
self-sufficiency, or the battery with the best net present value. A sweep over many
capacities is always returned: it is the picture that shows why bigger is not always better.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from resize_energy.core import battery as bat
from resize_energy.core import economics as eco

Mode = Literal["given", "target", "optimal"]
MODES: dict[str, str] = {
    "given": "I choose the capacity: show me what it does",
    "target": "Find the smallest battery that reaches a target self-sufficiency",
    "optimal": "Find the battery with the best economic result",
}


@dataclass(frozen=True)
class BatteryProfiles:
    """One year of hourly output per kWp (PV) and per kW rated (wind)."""

    pv_unit: tuple[float, ...] | None = None
    wind_unit: tuple[float, ...] | None = None
    source: str = "synthetic"


@dataclass(frozen=True)
class BatteryInputs:
    # --- load and plant ---
    annual_demand_kwh: float = 6000.0
    load_kind: str = "residential"
    use_pv: bool = True
    use_wind: bool = False
    pv_kwp: float = 5.0
    wind_kw: float = 0.0
    # --- how to size ---
    mode: Mode = "given"
    capacity_kwh: float = 8.0
    target_self_sufficiency: float = 0.70
    # --- battery ---
    c_rate: float = 0.5                  # kW of power per kWh of capacity
    eta_roundtrip: float = 0.90
    usable_fraction: float = 0.90        # depth of discharge
    health: float = 0.90                 # average state of health over the life
    cycle_life: float = 6000.0           # equivalent full cycles before 80 % of the capacity
    calendar_life_years: float = 15.0
    # --- costs and prices ---
    capex_per_kwh: float = 550.0
    capex_per_kw: float = 100.0
    om_fraction: float = 0.015           # of the CAPEX per year
    retail_price: float = 0.25           # euro/kWh bought from the grid
    export_price: float = 0.08           # euro/kWh sold to the grid
    discount_rate: float = 0.05
    grid_ef: float = 0.25                # kg CO2 per kWh of the grid


@dataclass(frozen=True)
class SweepPoint:
    capacity_kwh: float
    self_sufficiency: float
    self_consumption: float
    savings_per_year: float
    npv: float
    cycles: float


@dataclass(frozen=True)
class BatteryDesign:
    capacity_kwh: float
    usable_kwh: float
    power_kw: float
    daily_load_kwh: float
    load_kwh: float
    generation_kwh: float
    direct_kwh: float
    battery_kwh: float                  # delivered by the battery
    import_kwh: float
    export_kwh: float
    import_without_kwh: float
    export_without_kwh: float
    self_sufficiency: float
    self_sufficiency_without: float
    self_consumption: float
    self_consumption_without: float
    loss_kwh: float                     # lost in the battery (round trip)
    cycles_per_year: float
    life_years: float
    life_limit: str                     # "cycles" or "calendar"
    capex: float
    om_per_year: float
    savings_per_year: float
    net_benefit_per_year: float
    payback_years: float
    npv: float
    lcos: float                         # euro per kWh delivered by the battery
    co2_avoided_t_per_year: float
    sweep: tuple[SweepPoint, ...]
    monthly_direct: tuple[float, ...]
    monthly_battery: tuple[float, ...]
    monthly_import: tuple[float, ...]
    summer_week: tuple[tuple[float, ...], ...]   # load, generation, soc, import (168 h each)
    winter_week: tuple[tuple[float, ...], ...]
    profile_source: str


SWEEP_FACTORS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)   # x the average daily load
FINE_FACTORS = tuple(i * 0.125 for i in range(0, 49))              # 0 .. 6 days


def _check(inp: BatteryInputs, prof: BatteryProfiles) -> None:
    if not (inp.use_pv or inp.use_wind):
        raise ValueError("choose PV, wind or both: a battery needs a plant to store from")
    if inp.use_pv and (not prof.pv_unit or inp.pv_kwp <= 0):
        raise ValueError("enter the PV power (kWp) of the plant")
    if inp.use_wind and (not prof.wind_unit or inp.wind_kw <= 0):
        raise ValueError("enter the wind power (kW) of the plant")
    if inp.annual_demand_kwh <= 0:
        raise ValueError("the yearly demand must be > 0")
    if inp.mode == "given" and inp.capacity_kwh < 0:
        raise ValueError("the capacity cannot be negative")
    if inp.mode == "target" and not 0.0 < inp.target_self_sufficiency < 1.0:
        raise ValueError("the target self-sufficiency must be between 0 and 100 %")
    if inp.c_rate <= 0 or inp.cycle_life <= 0 or inp.calendar_life_years <= 0:
        raise ValueError("C-rate, cycle life and calendar life must be > 0")
    if not 0 <= inp.discount_rate < 1:
        raise ValueError("the discount rate must be in [0, 1)")
    if inp.retail_price <= 0 or inp.capex_per_kwh < 0 or inp.capex_per_kw < 0:
        raise ValueError("prices must be positive")
    if inp.export_price < 0 or inp.om_fraction < 0:
        raise ValueError("export price and O&M cannot be negative")


def _generation(inp: BatteryInputs, prof: BatteryProfiles) -> list[float]:
    gen = [0.0] * bat.HOURS
    if inp.use_pv and prof.pv_unit:
        gen = [g + inp.pv_kwp * u for g, u in zip(gen, prof.pv_unit, strict=True)]
    if inp.use_wind and prof.wind_unit:
        gen = [g + inp.wind_kw * u for g, u in zip(gen, prof.wind_unit, strict=True)]
    return gen


def _economics(inp: BatteryInputs, capacity: float, power: float, run: bat.BatteryRun,
               base: bat.BatteryRun) -> tuple[float, float, float, float, float, float, str]:
    """capex, O&M, savings, life [years], cycles per year, NPV, limiting factor."""
    usable = capacity * inp.usable_fraction
    cycles = run.discharge_kwh / usable if usable > 0 else 0.0
    life_cycles = inp.cycle_life / cycles if cycles > 0 else float("inf")
    life = min(inp.calendar_life_years, life_cycles)
    limit = "cycles" if life_cycles < inp.calendar_life_years else "calendar"
    capex = capacity * inp.capex_per_kwh + power * inp.capex_per_kw
    om = capex * inp.om_fraction
    savings = ((base.import_kwh - run.import_kwh) * inp.retail_price
               - (base.export_kwh - run.export_kwh) * inp.export_price)
    npv = eco.npv(capex, savings - om, inp.discount_rate, life) if capacity > 0 else 0.0
    return capex, om, savings, life, cycles, npv, limit


def _point(inp: BatteryInputs, gen, load, base, capacity: float) -> SweepPoint:
    power = capacity * inp.c_rate
    run = bat.simulate_battery(gen, load, capacity, power, inp.eta_roundtrip,
                               inp.usable_fraction, inp.health)
    _, _, savings, _, cycles, npv, _ = _economics(inp, capacity, power, run, base)
    return SweepPoint(capacity, bat.self_sufficiency(run), bat.self_consumption(run),
                      savings, npv, cycles)


def _week(run: bat.BatteryRun, gen, load, first_day: int) -> tuple[tuple[float, ...], ...]:
    a, b = first_day * 24, first_day * 24 + 168
    return (tuple(load[a:b]), tuple(gen[a:b]), run.soc[a:b], run.hourly_import[a:b])


def size_battery(inp: BatteryInputs, prof: BatteryProfiles) -> BatteryDesign:
    """Choose the capacity (by mode), simulate the year with and without it, and price it."""
    _check(inp, prof)
    load = bat.load_profile(inp.annual_demand_kwh, inp.load_kind)
    gen = _generation(inp, prof)
    daily = inp.annual_demand_kwh / 365.0
    base = bat.simulate_battery(gen, load, 0.0, 0.0)
    sweep = tuple(_point(inp, gen, load, base, f * daily) for f in SWEEP_FACTORS)

    if inp.mode == "given":
        capacity = inp.capacity_kwh
    elif inp.mode == "target":
        points = [_point(inp, gen, load, base, f * daily) for f in FINE_FACTORS]
        hit = next((p for p in points if p.self_sufficiency >= inp.target_self_sufficiency),
                   None)
        if hit is None:
            best = max(p.self_sufficiency for p in points)
            raise ValueError(
                f"with this plant even a very large battery reaches only {best:.0%} "
                f"self-sufficiency: lower the target to {best:.0%} or less, or enlarge the plant")
        capacity = hit.capacity_kwh
    else:
        points = [_point(inp, gen, load, base, f * daily) for f in FINE_FACTORS[1:]]
        capacity = max(points, key=lambda p: p.npv).capacity_kwh

    power = capacity * inp.c_rate
    run = bat.simulate_battery(gen, load, capacity, power, inp.eta_roundtrip,
                               inp.usable_fraction, inp.health)
    capex, om, savings, life, cycles, npv, limit = _economics(inp, capacity, power, run, base)
    net = savings - om
    delivered = run.discharge_kwh
    lcos = ((capex * eco.capital_recovery_factor(inp.discount_rate, life) + om) / delivered
            if delivered > 0 and capacity > 0 else 0.0)
    return BatteryDesign(
        capacity_kwh=capacity, usable_kwh=capacity * inp.usable_fraction, power_kw=power,
        daily_load_kwh=daily, load_kwh=run.load_kwh, generation_kwh=run.generation_kwh,
        direct_kwh=run.direct_kwh, battery_kwh=delivered, import_kwh=run.import_kwh,
        export_kwh=run.export_kwh, import_without_kwh=base.import_kwh,
        export_without_kwh=base.export_kwh,
        self_sufficiency=bat.self_sufficiency(run),
        self_sufficiency_without=bat.self_sufficiency(base),
        self_consumption=bat.self_consumption(run),
        self_consumption_without=bat.self_consumption(base),
        loss_kwh=run.charge_kwh - delivered, cycles_per_year=cycles, life_years=life,
        life_limit=limit, capex=capex, om_per_year=om, savings_per_year=savings,
        net_benefit_per_year=net, payback_years=eco.simple_payback_years(capex, net),
        npv=npv, lcos=lcos,
        co2_avoided_t_per_year=(base.import_kwh - run.import_kwh) * inp.grid_ef / 1000.0,
        sweep=sweep, monthly_direct=run.monthly_direct, monthly_battery=run.monthly_battery,
        monthly_import=run.monthly_import,
        summer_week=_week(run, gen, load, 172), winter_week=_week(run, gen, load, 5),
        profile_source=prof.source,
    )
