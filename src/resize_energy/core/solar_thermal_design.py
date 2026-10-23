"""Preliminary design of a solar thermal plant: hot water and/or adsorption cooling.

Pure calculation, no GUI. The collector area is given by the user or found for a target solar
fraction; the store and the chiller follow from the area and the loads. Economics use the same
textbook annuity model as the rest of RESize (constant prices, no incentives).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from functools import lru_cache

from resize_energy.core import economics as eco
from resize_energy.core import solar_thermal as st
from resize_energy.core.sensitivity import Parameter, Sensitivity, one_at_a_time

AREA_FRACTIONS = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)


@dataclass(frozen=True)
class SolarThermalInputs:
    # --- loads ---
    dhw_litres_per_day: float = 200.0
    t_use_c: float = 55.0
    cooling_kwh_per_year: float = 0.0
    # --- site ---
    latitude_deg: float = 45.0
    irradiation_kwh_m2: float = 1400.0      # on the collector plane
    t_mean_c: float = 12.0
    t_season_amp_c: float = 10.0
    # --- plant ---
    collector: str = "flat"
    eta0: float = 0.0                       # 0 = take the three numbers of the type
    a1: float = 0.0
    a2: float = 0.0
    mode: str = "given"                     # "given" area or "target" solar fraction
    area_m2: float = 4.0
    target_fraction: float = 0.60
    store_l_per_m2: float = 60.0
    loop_loss: float = 0.08
    chiller: str = "adsorption"              # key of st.CHILLERS (the main cooling technology)
    compare_chillers: tuple[str, ...] = ()  # other technologies to evaluate on the same field
    chiller_kw: float = 0.0                 # 0 = size it for the peak hour of the load
    cop_nominal: float = 0.55
    t_drive_min_c: float = 60.0
    t_drive_nominal_c: float = 80.0
    chiller_parasitic: float = 0.03
    # --- costs and prices ---
    collector_cost_per_m2: float = 0.0      # 0 = default of the collector type
    store_cost_per_litre: float = 1.8
    fixed_cost: float = 1500.0              # pump station, controller, piping, labour
    chiller_cost_per_kw: float = 1100.0     # adsorption chiller with heat rejection
    om_fraction: float = 0.015              # of CAPEX per year
    heat_price: float = 0.11                # euro per kWh of heat from the backup boiler
    electricity_price: float = 0.22
    compressor_cop: float = 3.0
    life_years: float = 20.0
    discount_rate: float = 0.05
    heat_ef_kg_per_kwh: float = 0.23        # of the backup heat (gas boiler)
    grid_ef_kg_per_kwh: float = 0.25


@dataclass(frozen=True)
class CoolingOption:
    """One cooling technology evaluated on the same collectors and tank."""

    key: str
    name: str
    is_main: bool
    chiller_kw: float
    cooling_fraction: float
    mean_cop: float
    solar_fraction: float
    hours_below_drive: int
    capex: float
    npv: float
    payback_years: float


@dataclass(frozen=True)
class SolarThermalDesign:
    area_m2: float
    store_litres: float
    chiller_kw: float
    collector: st.CollectorType
    target_reached: bool
    run: st.SolarRun
    collector_cost: float
    store_cost: float
    chiller_cost: float
    fixed_cost: float
    capex: float
    om_per_year: float
    solar_useful_kwh: float                 # heat + cold, in the energy they replace
    savings_per_year: float
    lcoh: float                             # euro per kWh of useful solar energy
    payback_years: float
    npv: float
    co2_avoided_t: float
    yield_kwh_m2: float                     # useful solar energy per m2 of collector
    sweep: tuple[tuple[float, float, float, float], ...] = ()   # area, fraction, kWh/m2, NPV
    sensitivity: Sensitivity | None = None
    inputs_used: SolarThermalInputs | None = None
    cooling_options: tuple[CoolingOption, ...] = ()


def collector_of(i: SolarThermalInputs) -> st.CollectorType:
    base = st.COLLECTORS[i.collector]
    return st.CollectorType(
        base.name, i.eta0 or base.eta0, i.a1 or base.a1, i.a2 if i.eta0 else base.a2,
        i.collector_cost_per_m2 or base.cost_per_m2)


def _validate(i: SolarThermalInputs) -> None:
    if i.collector not in st.COLLECTORS:
        raise ValueError("unknown collector type")
    if i.chiller not in st.CHILLERS or any(k not in st.CHILLERS for k in i.compare_chillers):
        raise ValueError("unknown cooling technology")
    if i.dhw_litres_per_day < 0 or i.cooling_kwh_per_year < 0:
        raise ValueError("the loads cannot be negative")
    if i.dhw_litres_per_day <= 0 and i.cooling_kwh_per_year <= 0:
        raise ValueError("give a hot-water demand, a cooling demand, or both")
    if i.irradiation_kwh_m2 <= 0:
        raise ValueError("the irradiation on the collector must be > 0")
    if not 0 < i.t_use_c <= 90:
        raise ValueError("the hot-water temperature must be between 0 and 90 degC")
    if i.mode == "given" and i.area_m2 <= 0:
        raise ValueError("the collector area must be > 0")
    if i.mode == "target" and not 0 < i.target_fraction < 1:
        raise ValueError("the target solar fraction must be between 0 and 100 %")
    if i.store_l_per_m2 <= 0 or not 0 <= i.loop_loss < 0.5:
        raise ValueError("store volume must be > 0 and loop losses in [0, 50 %)")
    if not 0 < i.cop_nominal < 1.2 or i.t_drive_min_c >= i.t_drive_nominal_c:
        raise ValueError("chiller COP must be in (0, 1.2) and minimum drive below nominal")
    if i.compressor_cop <= 0 or i.heat_price <= 0 or i.electricity_price <= 0:
        raise ValueError("COP and prices must be > 0")
    if i.life_years <= 0 or not 0 <= i.discount_rate < 1:
        raise ValueError("lifetime must be > 0 and the discount rate in [0, 1)")


@lru_cache(maxsize=8)
def _weather(lat: float, irr: float, t_mean: float, amp: float) -> st.Weather:
    return st.synthetic_weather(lat, irr, t_mean, amp)


def _chiller_kw(i: SolarThermalInputs, weather: st.Weather) -> float:
    if i.cooling_kwh_per_year <= 0:
        return 0.0
    if i.chiller_kw > 0:
        return i.chiller_kw
    peak = max(st.cooling_load_profile(weather, i.cooling_kwh_per_year))
    return max(1.0, round(peak, 1))


def _system(i: SolarThermalInputs, area: float, weather: st.Weather) -> st.SolarSystem:
    litres = max(50.0, area * i.store_l_per_m2)
    return st.SolarSystem(
        area_m2=area, collector=collector_of(i), store_litres=litres,
        store_ua_w_k=0.16 * math.sqrt(litres), loop_loss=i.loop_loss,
        dhw_litres_per_day=i.dhw_litres_per_day, t_use_c=i.t_use_c,
        cooling_kwh_per_year=i.cooling_kwh_per_year, chiller_kw_cooling=_chiller_kw(i, weather),
        cop_nominal=i.cop_nominal, t_drive_min_c=i.t_drive_min_c,
        t_drive_nominal_c=i.t_drive_nominal_c, chiller_parasitic=i.chiller_parasitic,
        compressor_cop=i.compressor_cop)


def _simulate(i: SolarThermalInputs, area: float) -> tuple[st.SolarSystem, st.SolarRun]:
    w = _weather(i.latitude_deg, i.irradiation_kwh_m2, i.t_mean_c, i.t_season_amp_c)
    s = _system(i, area, w)
    return s, st.simulate(s, w, i.t_mean_c, i.t_season_amp_c)


def _money(i: SolarThermalInputs, s: st.SolarSystem, run: st.SolarRun) -> dict[str, float]:
    c = s.collector
    cc, sc = s.area_m2 * c.cost_per_m2, s.store_litres * i.store_cost_per_litre
    ch = s.chiller_kw_cooling * i.chiller_cost_per_kw
    capex = cc + sc + ch + i.fixed_cost
    om = capex * i.om_fraction
    cold = run.cooling_solar_kwh
    electricity_saved = cold / i.compressor_cop - cold * s.chiller_parasitic
    savings = run.heat_solar_kwh * i.heat_price + electricity_saved * i.electricity_price
    useful = run.heat_solar_kwh + cold
    net = savings - om
    co2 = (run.heat_solar_kwh * i.heat_ef_kg_per_kwh + electricity_saved * i.grid_ef_kg_per_kwh)
    return dict(
        collector_cost=cc, store_cost=sc, chiller_cost=ch, capex=capex, om=om,
        savings=savings, useful=useful, co2_t=co2 / 1000.0,
        lcoh=(eco.lcoe(capex, om, useful, i.discount_rate, i.life_years) if useful > 0
              else math.inf),
        payback=eco.simple_payback_years(capex, net),
        npv=eco.npv(capex, net, i.discount_rate, i.life_years))


def size_solar_thermal(i: SolarThermalInputs, *, with_sweep: bool = True,
                       with_sensitivity: bool = True) -> SolarThermalDesign:
    _validate(i)
    reached = True
    if i.mode == "target":
        demand_kwh = (i.dhw_litres_per_day * 365 * st.WATER_KWH_PER_L_K * max(1.0, i.t_use_c - i.t_mean_c)
                      + i.cooling_kwh_per_year / i.cop_nominal)
        lo, hi = 0.5, max(2.0, demand_kwh / 150.0)        # up to ~150 kWh per m2 and year
        if _simulate(i, hi)[1].solar_fraction < i.target_fraction:
            area, reached = hi, False
        else:
            for _ in range(14):
                mid = (lo + hi) / 2.0
                if _simulate(i, mid)[1].solar_fraction >= i.target_fraction:
                    hi = mid
                else:
                    lo = mid
            area = round(hi, 1)
    else:
        area = i.area_m2
    s, run = _simulate(i, area)
    m = _money(i, s, run)
    design = SolarThermalDesign(
        area_m2=area, store_litres=s.store_litres, chiller_kw=s.chiller_kw_cooling,
        collector=s.collector, target_reached=reached, run=run,
        collector_cost=m["collector_cost"], store_cost=m["store_cost"],
        chiller_cost=m["chiller_cost"], fixed_cost=i.fixed_cost, capex=m["capex"],
        om_per_year=m["om"], solar_useful_kwh=m["useful"], savings_per_year=m["savings"],
        lcoh=m["lcoh"], payback_years=m["payback"], npv=m["npv"], co2_avoided_t=m["co2_t"],
        yield_kwh_m2=m["useful"] / area if area > 0 else 0.0, inputs_used=i)
    if with_sweep:
        design = replace(design, sweep=area_sweep(i, area))
    if i.cooling_kwh_per_year > 0 and i.compare_chillers:
        design = replace(design, cooling_options=cooling_options(i, area))
    if with_sensitivity:
        design = replace(design, sensitivity=solar_thermal_sensitivity(i, area))
    return design


def chiller_variant(i: SolarThermalInputs, key: str) -> SolarThermalInputs:
    """The same project with the catalogue values of another cooling technology."""
    c = st.CHILLERS[key]
    return replace(i, chiller=key, cop_nominal=c.cop_nominal, t_drive_min_c=c.t_drive_min_c,
                   t_drive_nominal_c=c.t_drive_nominal_c, chiller_parasitic=c.parasitic,
                   chiller_cost_per_kw=c.cost_per_kw, chiller_kw=0.0)


def cooling_options(i: SolarThermalInputs, area: float) -> tuple[CoolingOption, ...]:
    """Main technology (with the user's values) and the others (catalogue values)."""
    keys = [i.chiller] + [k for k in dict.fromkeys(i.compare_chillers) if k != i.chiller]
    out = []
    for key in keys:
        j = i if key == i.chiller else chiller_variant(i, key)
        s, run = _simulate(j, area)
        m = _money(j, s, run)
        cop = run.cooling_solar_kwh / run.chiller_heat_kwh if run.chiller_heat_kwh > 0 else 0.0
        out.append(CoolingOption(
            key, st.CHILLERS[key].name, key == i.chiller, s.chiller_kw_cooling,
            run.cooling_fraction, cop, run.solar_fraction, run.hours_below_drive, m["capex"],
            m["npv"], m["payback"]))
    return tuple(out)


def area_sweep(i: SolarThermalInputs, area: float) -> tuple[tuple[float, float, float, float], ...]:
    """(area, solar fraction, useful kWh per m2, NPV) for areas around the chosen one."""
    rows = []
    for f in AREA_FRACTIONS:
        a = max(0.5, round(area * f, 1))
        s, run = _simulate(i, a)
        m = _money(i, s, run)
        rows.append((a, run.solar_fraction, m["useful"] / a, m["npv"]))
    return tuple(rows)


def solar_thermal_sensitivity(i: SolarThermalInputs, area: float) -> Sensitivity:
    """Net present value when each input moves by +/- 20 %."""
    def evaluate(f: dict[str, float]) -> float:
        j = replace(
            i, irradiation_kwh_m2=i.irradiation_kwh_m2 * f.get("sun", 1.0),
            collector_cost_per_m2=collector_of(i).cost_per_m2 * f.get("capex", 1.0),
            store_cost_per_litre=i.store_cost_per_litre * f.get("capex", 1.0),
            fixed_cost=i.fixed_cost * f.get("capex", 1.0),
            chiller_cost_per_kw=i.chiller_cost_per_kw * f.get("capex", 1.0),
            heat_price=i.heat_price * f.get("heat", 1.0),
            electricity_price=i.electricity_price * f.get("elec", 1.0),
            dhw_litres_per_day=i.dhw_litres_per_day * f.get("load", 1.0),
            cooling_kwh_per_year=i.cooling_kwh_per_year * f.get("load", 1.0),
            discount_rate=i.discount_rate * f.get("rate", 1.0), mode="given", area_m2=area)
        s, run = _simulate(j, area)
        return _money(j, s, run)["npv"]

    params = [Parameter("sun", "Solar irradiation"), Parameter("capex", "Cost of the plant"),
              Parameter("heat", "Price of the heat you replace"),
              Parameter("load", "Hot-water and cooling demand"),
              Parameter("rate", "Discount rate")]
    if i.cooling_kwh_per_year > 0:
        params.insert(3, Parameter("elec", "Price of electricity"))
    return one_at_a_time(evaluate, params, "Net present value", "euro", decimals=0)
