"""Preliminary design of a green hydrogen plant: PEM electrolyser fed by PV, wind and/or grid.

Two ways in: from a hydrogen demand (the plant is sized for it) or from an existing
renewable plant (the hydrogen it can make is calculated). Hourly profiles decide how many
hours the electrolyser runs. Pure calculation, no GUI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from resize_energy.core import economics as eco
from resize_energy.core import hydrogen as h2
from resize_energy.core.sensitivity import Sensitivity

Mode = Literal["demand", "plant"]
MODES: dict[str, str] = {
    "demand": "From a hydrogen demand: size electrolyser and renewable plant",
    "plant": "From a renewable plant I already have: how much hydrogen can it make",
}


@dataclass(frozen=True)
class HydrogenProfiles:
    """One year of hourly output per kWp (PV) and per kW rated (wind)."""

    pv_unit: tuple[float, ...] | None = None
    wind_unit: tuple[float, ...] | None = None
    source: str = "synthetic"
    prices: tuple[float, ...] | None = None    # euro/kWh, 8760 values (hourly grid price)


@dataclass(frozen=True)
class HydrogenInputs:
    mode: Mode = "demand"
    use_pv: bool = True
    use_wind: bool = False
    use_grid: bool = False
    # --- demand mode ---
    h2_demand_kg_per_year: float = 100_000.0
    pv_kwp_per_kw_el: float = 1.5          # renewable kW per kW of electrolyser
    wind_kw_per_kw_el: float = 1.2
    # --- plant mode ---
    pv_kwp: float = 0.0
    wind_kw: float = 0.0
    electrolyser_kw: float = 0.0
    # --- electrolyser and storage ---
    kwh_per_kg_stack: float = 55.0         # system consumption at nominal load, without compression
    min_load: float = 0.10
    outlet_bar: float = 30.0
    storage_bar: float = 350.0
    storage_days: float = 3.0
    water_l_per_kg: float = 10.0
    grid_hours_cap: float = 4000.0         # max grid energy, in full-load hours of the electrolyser
    # --- deeper models (all off by default: the simple model of the first version) ---
    part_load_model: bool = False          # efficiency depends on the load
    aux_share: float = 0.06                # auxiliaries, fraction of nominal power
    stack_gain: float = 0.12               # stack efficiency gain at very low load
    degradation_per_1000h: float = 0.0     # extra consumption per 1000 operating hours (0.002 = 0.2 %)
    storage_mode: str = "days"             # "days" of autonomy, or "hourly" from the production
    cheapest_hours_first: bool = False     # buy grid electricity in the cheapest hours
    # --- costs (euro) ---
    electrolyser_capex_per_kw: float = 1800.0
    electrolyser_om_fraction: float = 0.03   # of CAPEX per year
    stack_hours: float = 60_000.0
    stack_cost_fraction: float = 0.40        # of the electrolyser CAPEX
    storage_capex_per_kg: float = 600.0
    water_price_per_m3: float = 3.0
    pv_capex_per_kwp: float = 1000.0
    pv_om_per_kwp: float = 15.0
    wind_capex_per_kw: float = 1500.0
    wind_om_per_kw: float = 45.0
    res_life_years: float = 25.0
    electrolyser_life_years: float = 20.0
    discount_rate: float = 0.05
    grid_price_per_kwh: float = 0.12
    # --- emissions (kg CO2 per kWh, and per kg of hydrogen) ---
    grid_ef: float = 0.25
    pv_ef: float = 0.045
    wind_ef: float = 0.011
    grey_h2_kg_co2_per_kg: float = 9.0


@dataclass(frozen=True)
class HydrogenDesign:
    electrolyser_kw: float
    pv_kwp: float
    wind_kw: float
    hydrogen_kg: float
    hydrogen_kg_per_day: float
    electricity_kwh: float
    res_available_kwh: float
    res_used_kwh: float
    curtailed_kwh: float
    grid_kwh: float
    res_utilisation: float
    grid_share: float
    full_load_hours: float
    hours_on: int
    kwh_per_kg_total: float
    compression_kwh_per_kg: float
    efficiency_lhv: float
    water_m3: float
    oxygen_t: float
    storage_kg: float
    storage_m3: float
    stack_life_years: float
    cost_electrolyser: float      # euro per year
    cost_stack: float
    cost_storage: float
    cost_res: float
    cost_grid: float
    cost_water: float
    lcoh: float                   # euro per kg
    co2_kg_per_kg: float
    co2_saved_t_per_year: float
    profile_source: str
    monthly_res_kwh: tuple[float, ...] = ()
    monthly_grid_kwh: tuple[float, ...] = ()
    hydrogen_kg_year1: float = 0.0
    kg_by_year: tuple[float, ...] = ()
    nominal_kwh_per_kg_total: float = 0.0       # at nominal load, new stack
    load_hist_kwh: tuple[float, ...] = ()
    tank_level_kg: tuple[float, ...] = ()       # daily level of the hourly storage (365 values)
    storage_mode: str = "days"
    mean_grid_price: float = 0.0                # euro/kWh actually paid
    flat_grid_price: float = 0.0                # what the same energy would cost at the mean price
    sensitivity: Sensitivity | None = None


def _check(inp: HydrogenInputs, prof: HydrogenProfiles) -> None:
    if not (inp.use_pv or inp.use_wind or inp.use_grid):
        raise ValueError("choose at least one electricity source")
    if inp.use_pv and not prof.pv_unit:
        raise ValueError("a PV profile is needed when PV is a source")
    if inp.use_wind and not prof.wind_unit:
        raise ValueError("a wind profile is needed when wind is a source")
    if inp.mode == "demand" and inp.h2_demand_kg_per_year <= 0:
        raise ValueError("the hydrogen demand must be > 0")
    if inp.mode == "plant":
        if inp.electrolyser_kw <= 0:
            raise ValueError("the electrolyser power must be > 0")
        if inp.use_pv and inp.pv_kwp <= 0 or inp.use_wind and inp.wind_kw <= 0:
            raise ValueError("enter the size of each renewable source you selected")
    if inp.kwh_per_kg_stack <= 0 or inp.stack_hours <= 0 or inp.storage_days < 0:
        raise ValueError("consumption and stack life must be > 0 and storage days >= 0")
    if inp.storage_bar < inp.outlet_bar or inp.outlet_bar <= 0:
        raise ValueError("storage pressure cannot be below the electrolyser outlet pressure")
    if inp.use_grid and inp.grid_hours_cap <= 0:
        raise ValueError("the grid limit must be > 0 hours when the grid is a source")
    if not 0 <= inp.discount_rate < 1:
        raise ValueError("discount rate must be in [0, 1)")
    if inp.storage_mode not in ("days", "hourly"):
        raise ValueError("storage_mode must be 'days' or 'hourly'")
    if not 0 <= inp.aux_share < 0.5 or not 0 <= inp.stack_gain < 0.5:
        raise ValueError("auxiliary share and stack gain must be between 0 and 50 %")
    if inp.degradation_per_1000h < 0 or inp.degradation_per_1000h > 0.02:
        raise ValueError("degradation must be between 0 and 2 % per 1000 hours")
    if prof.prices is not None and len(prof.prices) != h2.HOURS:
        raise ValueError("hourly prices need 8760 values")
    if inp.mode == "demand" and inp.use_pv and inp.pv_kwp_per_kw_el <= 0:
        raise ValueError("PV per kW of electrolyser must be > 0")
    if inp.mode == "demand" and inp.use_wind and inp.wind_kw_per_kw_el <= 0:
        raise ValueError("wind per kW of electrolyser must be > 0")


def size_hydrogen_plant(inp: HydrogenInputs, prof: HydrogenProfiles) -> HydrogenDesign:
    """Run the year and size or evaluate the plant."""
    _check(inp, prof)
    compression = h2.compression_kwh_per_kg(inp.outlet_bar, max(inp.storage_bar, inp.outlet_bar))
    kwh_total = inp.kwh_per_kg_stack + compression

    def run(p_el: float, p_pv: float, p_wind: float) -> h2.DispatchResult:
        return h2.simulate_dispatch(
            prof.pv_unit if inp.use_pv else None, prof.wind_unit if inp.use_wind else None,
            p_pv, p_wind, p_el, inp.min_load, kwh_total, inp.use_grid, inp.grid_hours_cap,
            compression_kwh_per_kg=compression, part_load=inp.part_load_model,
            aux_share=inp.aux_share, stack_gain=inp.stack_gain,
            degradation_per_1000h=inp.degradation_per_1000h, stack_hours=inp.stack_hours,
            life_years=inp.electrolyser_life_years, grid_prices=prof.prices,
            cheapest_hours_first=inp.cheapest_hours_first)

    if inp.mode == "demand":
        # The dispatch is linear in size: simulate 1 kW of electrolyser, then scale.
        unit = run(1.0, inp.pv_kwp_per_kw_el if inp.use_pv else 0.0,
                   inp.wind_kw_per_kw_el if inp.use_wind else 0.0)
        if unit.hydrogen_kg <= 0:
            raise ValueError("with these sources the electrolyser never reaches its minimum load")
        p_el = inp.h2_demand_kg_per_year / unit.hydrogen_kg
        p_pv = inp.pv_kwp_per_kw_el * p_el if inp.use_pv else 0.0
        p_wind = inp.wind_kw_per_kw_el * p_el if inp.use_wind else 0.0
    else:
        p_el = inp.electrolyser_kw
        p_pv = inp.pv_kwp if inp.use_pv else 0.0
        p_wind = inp.wind_kw if inp.use_wind else 0.0
    r = run(p_el, p_pv, p_wind)
    kg = r.hydrogen_kg
    if kg <= 0:
        raise ValueError("with these sizes the electrolyser never reaches its minimum load")

    flh = r.electricity_kwh / p_el
    per_day = kg / 365.0
    tank_level: tuple[float, ...] = ()
    if inp.storage_mode == "hourly":
        # constant offtake equal to the mean production; the tank is the swing of the balance
        mean = sum(r.hourly_kg) / len(r.hourly_kg)
        level, lo, hi = 0.0, 0.0, 0.0
        cum: list[float] = []
        for made in r.hourly_kg:
            level += made - mean
            cum.append(level)
            lo, hi = min(lo, level), max(hi, level)
        storage_kg = hi - lo
        daily = [cum[min(len(cum) - 1, d * 24 + 23)] - lo for d in range(365)]
        tank_level = tuple(daily)
    else:
        storage_kg = per_day * inp.storage_days
    rate = inp.discount_rate
    crf_el = eco.capital_recovery_factor(rate, inp.electrolyser_life_years)
    crf_res = eco.capital_recovery_factor(rate, inp.res_life_years)
    capex_el = p_el * inp.electrolyser_capex_per_kw
    cost_el = capex_el * (crf_el + inp.electrolyser_om_fraction)
    cost_stack = capex_el * inp.stack_cost_fraction * flh / inp.stack_hours
    cost_storage = storage_kg * inp.storage_capex_per_kg * crf_el
    cost_res = (p_pv * (inp.pv_capex_per_kwp * crf_res + inp.pv_om_per_kwp)
                + p_wind * (inp.wind_capex_per_kw * crf_res + inp.wind_om_per_kw))
    cost_grid = r.grid_cost_eur if prof.prices is not None else r.grid_kwh * inp.grid_price_per_kwh
    water_m3 = kg * inp.water_l_per_kg / 1000.0
    cost_water = water_m3 * inp.water_price_per_m3
    total = cost_el + cost_stack + cost_storage + cost_res + cost_grid + cost_water
    co2 = (r.grid_kwh * inp.grid_ef + r.pv_used_kwh * inp.pv_ef
           + r.wind_used_kwh * inp.wind_ef) / kg
    return HydrogenDesign(
        electrolyser_kw=p_el, pv_kwp=p_pv, wind_kw=p_wind, hydrogen_kg=kg,
        hydrogen_kg_per_day=per_day, electricity_kwh=r.electricity_kwh,
        res_available_kwh=r.res_available_kwh, res_used_kwh=r.res_used_kwh,
        curtailed_kwh=r.res_available_kwh - r.res_used_kwh, grid_kwh=r.grid_kwh,
        res_utilisation=(r.res_used_kwh / r.res_available_kwh if r.res_available_kwh > 0
                         else 0.0),
        grid_share=r.grid_kwh / r.electricity_kwh, full_load_hours=flh, hours_on=r.hours_on,
        kwh_per_kg_total=r.electricity_kwh / kg, compression_kwh_per_kg=compression,
        efficiency_lhv=h2.system_efficiency_lhv(r.electricity_kwh / kg), water_m3=water_m3,
        oxygen_t=kg * h2.OXYGEN_KG_PER_KG / 1000.0, storage_kg=storage_kg,
        storage_m3=h2.storage_volume_m3(storage_kg, inp.storage_bar),
        stack_life_years=inp.stack_hours / flh,
        cost_electrolyser=cost_el, cost_stack=cost_stack, cost_storage=cost_storage,
        cost_res=cost_res, cost_grid=cost_grid, cost_water=cost_water, lcoh=total / kg,
        co2_kg_per_kg=co2, co2_saved_t_per_year=(inp.grey_h2_kg_co2_per_kg - co2) * kg / 1000.0,
        profile_source=prof.source, monthly_res_kwh=r.monthly_res_kwh,
        monthly_grid_kwh=r.monthly_grid_kwh, hydrogen_kg_year1=r.hydrogen_kg_year1,
        kg_by_year=r.kg_by_year, nominal_kwh_per_kg_total=kwh_total,
        load_hist_kwh=r.load_hist_kwh, tank_level_kg=tank_level, storage_mode=inp.storage_mode,
        mean_grid_price=(cost_grid / r.grid_kwh if r.grid_kwh > 0 else 0.0),
        flat_grid_price=(sum(prof.prices) / len(prof.prices) if prof.prices else
                         inp.grid_price_per_kwh),
    )


def hydrogen_sensitivity(inp: HydrogenInputs, prof: HydrogenProfiles):
    """Cost of the hydrogen (LCOH) when each input moves by +/- 20 %."""
    from dataclasses import replace

    from resize_energy.core.sensitivity import Parameter, one_at_a_time

    def evaluate(f: dict[str, float]) -> float:
        i = replace(
            inp,
            electrolyser_capex_per_kw=inp.electrolyser_capex_per_kw * f.get("el", 1.0),
            pv_capex_per_kwp=inp.pv_capex_per_kwp * f.get("pv", 1.0),
            wind_capex_per_kw=inp.wind_capex_per_kw * f.get("wind", 1.0),
            grid_price_per_kwh=inp.grid_price_per_kwh * f.get("grid", 1.0),
            discount_rate=inp.discount_rate * f.get("rate", 1.0),
            kwh_per_kg_stack=inp.kwh_per_kg_stack * f.get("kwh", 1.0),
            stack_hours=inp.stack_hours * f.get("stack", 1.0),
            storage_capex_per_kg=inp.storage_capex_per_kg * f.get("tank", 1.0),
        )
        return size_hydrogen_plant(i, prof).lcoh

    params = [Parameter("el", "Electrolyser cost per kW"),
              Parameter("rate", "Discount rate"),
              Parameter("kwh", "Electricity per kg of hydrogen"),
              Parameter("stack", "Stack life"),
              Parameter("tank", "Storage cost per kg")]
    if inp.use_pv:
        params.append(Parameter("pv", "PV cost per kWp"))
    if inp.use_wind:
        params.append(Parameter("wind", "Wind cost per kW"))
    if inp.use_grid:
        params.append(Parameter("grid", "Grid electricity price"))
    return one_at_a_time(evaluate, params, "Cost of hydrogen (LCOH)", "euro/kg")
