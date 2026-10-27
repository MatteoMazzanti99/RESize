"""Side-by-side comparison of two to four technologies sized for the same energy target.

Photovoltaic, wind, biogas CHP, run-of-river hydropower and geothermal power deliver electricity (compared with the grid); green hydrogen
delivers hydrogen (compared with hydrogen from natural gas, on its lower heating value).
Every plant is sized for the same yearly energy and share to cover.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from resize_energy.core import economics as eco
from resize_energy.core import hydrogen as h2
from resize_energy.core import profiles as prof
from resize_energy.core import pv, wind
from resize_energy.core.biomass_design import (
    BiomassDesign,
    BiomassInputs,
    default_efficiencies,
    size_biomass_plant,
)
from resize_energy.core.geothermal_design import (
    GeothermalDesign,
    GeothermalInputs,
    size_geothermal_plant,
)
from resize_energy.core.hydro_design import HydroDesign, HydroInputs, size_hydro_plant
from resize_energy.core.hydrogen_design import (
    HydrogenDesign,
    HydrogenInputs,
    HydrogenProfiles,
    size_hydrogen_plant,
)
from resize_energy.core.wind_design import WindDesign, WindInputs, size_wind_plant

if TYPE_CHECKING:
    from resize_energy.core.comparison_heat import HeatInputs

TECHS = ("pv", "wind", "biomass", "hydrogen", "hydro", "geothermal")
TECH_NAMES = {"pv": "Photovoltaic", "wind": "Wind", "biomass": "Biomass (biogas CHP)",
              "hydrogen": "Green hydrogen", "hydro": "Hydropower (run-of-river)",
              "geothermal": "Geothermal power", "solar": "Solar thermal",
              "bhe": "Ground-source heat pump"}

# What each technology can deliver to the comparison (see core/comparison_heat.py for the heat).
ELECTRICITY_TECHS = TECHS
HEAT_TECHS = ("biomass", "geothermal", "solar", "bhe")
ALL_TECHS = TECHS + ("solar", "bhe")
CARRIERS = ("electricity", "heat", "both")


def possible_carriers(techs: tuple[str, ...]) -> tuple[str, ...]:
    """The comparisons the chosen technologies allow: a carrier needs at least two of them
    that can deliver it, and "both" needs the two carriers at once."""
    el = sum(t in ELECTRICITY_TECHS for t in techs) >= 2
    heat = sum(t in HEAT_TECHS for t in techs) >= 2
    out = (("electricity",) if el else ()) + (("heat",) if heat else ())
    return out + (("both",) if el and heat else ())


@dataclass(frozen=True)
class CostAssumptions:
    """Prices and costs. The defaults are round placeholders: replace them with local quotes."""

    pv_capex_eur_per_kwp: float = 1000.0
    pv_om_eur_per_kwp_year: float = 15.0
    pv_lifetime_years: float = 30.0
    pv_lifecycle_g_per_kwh: float = 45.0
    wind_capex_eur_per_kw: float = 1500.0
    wind_om_eur_per_kw_year: float = 45.0
    wind_lifetime_years: float = 25.0
    wind_lifecycle_g_per_kwh: float = 11.0
    discount_rate: float = 0.05
    retail_price_eur_per_kwh: float = 0.15
    export_price_eur_per_kwh: float = 0.07
    grid_kg_co2_per_kwh: float = 0.25
    # biogas CHP (digester, engine, grid connection)
    bio_capex_eur_per_kwe: float = 4500.0
    bio_om_eur_per_kwe_year: float = 250.0
    bio_feedstock_eur_per_t: float = 25.0
    bio_lifetime_years: float = 20.0
    bio_lifecycle_g_per_kwh: float = 100.0
    # green hydrogen (the renewable plant uses the PV and wind costs above)
    h2_electrolyser_capex_eur_per_kw: float = 1000.0
    h2_reference_price_eur_per_kg: float = 3.5      # hydrogen from natural gas
    h2_reference_kg_co2_per_kg: float = 9.0
    # run-of-river hydropower and geothermal power plant (wells included)
    hydro_capex_eur_per_kw: float = 6600.0
    hydro_om_eur_per_kw_year: float = 165.0
    hydro_lifetime_years: float = 40.0
    hydro_lifecycle_g_per_kwh: float = 24.0
    geo_capex_eur_per_kw: float = 6300.0
    geo_om_eur_per_kw_year: float = 190.0
    geo_lifetime_years: float = 30.0
    geo_lifecycle_g_per_kwh: float = 38.0


@dataclass(frozen=True)
class ComparisonInputs:
    """Same site and demand for all technologies (demand and coverage live in ``wind``)."""

    annual_irradiation_kwh_m2: float
    performance_ratio: float
    wind: WindInputs
    costs: CostAssumptions = field(default_factory=CostAssumptions)
    techs: tuple[str, ...] = ("pv", "wind")
    latitude_deg: float = 45.0
    biomass: BiomassInputs = field(default_factory=lambda: BiomassInputs(pathway="biogas"))
    h2_use_pv: bool = True
    h2_use_wind: bool = False
    hourly_weather: prof.HourlyWeather | None = None   # real hourly year for the hydrogen plant
    hydro: HydroInputs = field(default_factory=HydroInputs)   # river and penstock; costs below
    geothermal: GeothermalInputs = field(
        default_factory=lambda: GeothermalInputs(
            pathway="power", reservoir_temp_c=140.0, flow_per_well_kg_s=80.0))
    carrier: str = "electricity"          # "electricity" or "heat" (one comparison at a time)
    heat: HeatInputs | None = None        # the heat demand and plants, when carrier == "heat"

    @property
    def annual_demand_kwh(self) -> float:
        if self.carrier == "heat" and self.heat is not None:
            return self.heat.annual_heat_kwh
        return self.wind.annual_demand_kwh

    @property
    def coverage(self) -> float:
        if self.carrier == "heat" and self.heat is not None:
            return self.heat.coverage
        return self.wind.coverage


@dataclass(frozen=True)
class TechResult:
    """Technical, economic and carbon figures of one technology."""

    name: str
    installed_kw: float
    energy_kwh: float
    coverage: float
    full_load_hours: float
    capex_eur: float
    om_eur_per_year: float
    lifetime_years: float
    lcoe_eur_per_kwh: float
    savings_eur_per_year: float
    net_benefit_eur_per_year: float
    payback_years: float
    discounted_payback_years: float
    npv_eur: float
    co2_avoided_t_per_year: float
    co2_avoided_lifetime_t: float
    key: str = ""
    product: str = "electricity"           # "electricity" or "hydrogen"
    reference_price_eur_per_kwh: float = 0.0
    co2_reference_kg_per_kwh: float = 0.0   # what the product replaces
    co2_own_kg_per_kwh: float = 0.0         # life cycle of this plant


@dataclass(frozen=True)
class ComparisonResult:
    techs: tuple[TechResult, ...]
    lowest_lcoe: str
    fastest_payback: str
    highest_npv: str
    most_co2: str
    wind_design: WindDesign | None = None
    biomass_design: BiomassDesign | None = None
    hydrogen_design: HydrogenDesign | None = None
    hydro_design: HydroDesign | None = None
    geothermal_design: GeothermalDesign | None = None
    sensitivity: dict[str, dict[str, tuple[float, ...]]] | None = None
    notes: tuple[str, ...] = ()          # technologies left out, and why
    bhe_design: object | None = None
    solar_design: object | None = None

    def get(self, key: str) -> TechResult | None:
        return next((t for t in self.techs if t.key == key), None)

    @property
    def pv(self) -> TechResult | None:
        return self.get("pv")

    @property
    def wind(self) -> TechResult | None:
        return self.get("wind")

    @property
    def biomass(self) -> TechResult | None:
        return self.get("biomass")

    @property
    def hydrogen(self) -> TechResult | None:
        return self.get("hydrogen")

    @property
    def hydro(self) -> TechResult | None:
        return self.get("hydro")

    @property
    def geothermal(self) -> TechResult | None:
        return self.get("geothermal")


def _tech(key: str, kw: float, energy: float, demand: float, capex: float, om: float,
          life: float, own_ef: float, c: CostAssumptions, *, product: str = "electricity",
          ref_price: float | None = None, export_price: float | None = None,
          ref_ef: float | None = None, lcoe: float | None = None) -> TechResult:
    ref_price = c.retail_price_eur_per_kwh if ref_price is None else ref_price
    export_price = c.export_price_eur_per_kwh if export_price is None else export_price
    ref_ef = c.grid_kg_co2_per_kwh if ref_ef is None else ref_ef
    savings = eco.annual_savings(energy, demand, ref_price, export_price)
    net = savings - om
    co2 = energy * (ref_ef - own_ef) / 1000.0
    return TechResult(
        name=TECH_NAMES[key], installed_kw=kw, energy_kwh=energy, coverage=energy / demand,
        full_load_hours=energy / kw, capex_eur=capex, om_eur_per_year=om, lifetime_years=life,
        lcoe_eur_per_kwh=(eco.lcoe(capex, om, energy, c.discount_rate, life)
                          if lcoe is None else lcoe),
        savings_eur_per_year=savings, net_benefit_eur_per_year=net,
        payback_years=eco.simple_payback_years(capex, net),
        discounted_payback_years=eco.discounted_payback_years(capex, net, c.discount_rate),
        npv_eur=eco.npv(capex, net, c.discount_rate, life),
        co2_avoided_t_per_year=co2, co2_avoided_lifetime_t=co2 * life,
        key=key, product=product, reference_price_eur_per_kwh=ref_price,
        co2_reference_kg_per_kwh=ref_ef, co2_own_kg_per_kwh=own_ef,
    )


def _best(techs: tuple[TechResult, ...], value, lowest: bool = True) -> str:
    ranked = sorted(techs, key=value, reverse=not lowest)
    first = value(ranked[0])
    if len(ranked) > 1:
        second = value(ranked[1])
        if math.isclose(first, second, rel_tol=1e-9) or (math.isinf(first) and math.isinf(second)):
            return "tie"
    return ranked[0].name


def _check_inputs(inp: ComparisonInputs) -> None:
    c = inp.costs
    if not 0 <= c.discount_rate < 1:
        raise ValueError("discount rate must be in [0, 1)")
    if len(inp.techs) < 2:
        raise ValueError("choose at least two technologies to compare")
    if any(t not in TECHS for t in inp.techs) or len(set(inp.techs)) != len(inp.techs):
        raise ValueError("unknown or repeated technology")
    needs = {
        "pv": ("PV CAPEX", c.pv_capex_eur_per_kwp), "wind": ("wind CAPEX", c.wind_capex_eur_per_kw),
        "biomass": ("biomass CAPEX", c.bio_capex_eur_per_kwe),
        "hydrogen": ("electrolyser CAPEX", c.h2_electrolyser_capex_eur_per_kw),
        "hydro": ("hydropower CAPEX", c.hydro_capex_eur_per_kw),
        "geothermal": ("geothermal CAPEX", c.geo_capex_eur_per_kw),
    }
    for key in inp.techs:
        label, value = needs[key]
        if value <= 0:
            raise ValueError(f"{label} must be > 0")
    if c.retail_price_eur_per_kwh <= 0:
        raise ValueError("retail price must be > 0")
    if inp.annual_irradiation_kwh_m2 <= 0 or not 0 < inp.performance_ratio <= 1:
        raise ValueError("irradiation must be > 0 and performance ratio in (0, 1]")
    if "hydrogen" in inp.techs:
        if not (inp.h2_use_pv or inp.h2_use_wind):
            raise ValueError("choose PV, wind or both as the electricity source of the hydrogen")
        if c.h2_reference_price_eur_per_kg <= 0:
            raise ValueError("the reference hydrogen price must be > 0")


def _size_hydrogen(inp: ComparisonInputs, target_kwh: float) -> tuple[HydrogenDesign, HydrogenInputs]:
    c, w = inp.costs, inp.wind
    hin = HydrogenInputs(
        mode="demand", use_pv=inp.h2_use_pv, use_wind=inp.h2_use_wind, use_grid=False,
        h2_demand_kg_per_year=target_kwh / h2.H2_LHV_KWH_PER_KG,
        electrolyser_capex_per_kw=c.h2_electrolyser_capex_eur_per_kw,
        pv_capex_per_kwp=c.pv_capex_eur_per_kwp, pv_om_per_kwp=c.pv_om_eur_per_kwp_year,
        wind_capex_per_kw=c.wind_capex_eur_per_kw, wind_om_per_kw=c.wind_om_eur_per_kw_year,
        res_life_years=c.pv_lifetime_years, discount_rate=c.discount_rate,
        pv_ef=c.pv_lifecycle_g_per_kwh / 1000.0, wind_ef=c.wind_lifecycle_g_per_kwh / 1000.0,
        grid_ef=c.grid_kg_co2_per_kwh, grey_h2_kg_co2_per_kg=c.h2_reference_kg_co2_per_kg)
    pv_unit = wind_unit = None
    weather = inp.hourly_weather
    v50 = wind.shear_power_law(w.mean_speed_ref_ms, w.ref_height_m, 50.0, w.shear_alpha)
    if inp.h2_use_pv:
        specific = inp.annual_irradiation_kwh_m2 * inp.performance_ratio
        pv_unit = (prof.pv_profile_from_ghi(weather.ghi_w_m2, specific) if weather else
                   prof.synthetic_pv_profile(inp.latitude_deg, specific))
    if inp.h2_use_wind:
        rho = wind.air_density(w.elevation_m, w.temperature_c)
        series = weather.wind50_ms if weather else prof.synthetic_wind_series(v50, w.weibull_k)
        wind_unit = prof.turbine_unit_profile(
            series, v50, w.turbine.hub_height_m, w.shear_alpha, w.turbine, rho,
            w.availability * (1.0 - w.other_losses))
    design = size_hydrogen_plant(
        hin, HydrogenProfiles(pv_unit, wind_unit, "NASA POWER" if weather else "synthetic"))
    return design, hin


def compare_technologies(inp: ComparisonInputs) -> ComparisonResult:
    """Size the selected plants for the same energy target; LCOE, payback, NPV and CO2.

    The PV array is sized exactly on the target (no inverter or string limits); the wind plant
    uses a whole number of turbines, so it can overshoot; biogas and hydrogen are sized by
    their own modules. Biogas heat is not credited (conservative).
    """
    if inp.carrier == "heat":
        from resize_energy.core.comparison_heat import compare_heat
        return compare_heat(inp)
    _check_inputs(inp)
    c = inp.costs
    demand = inp.annual_demand_kwh
    target = demand * inp.coverage
    results: list[TechResult] = []
    wd = bd = hd = hyd = geo = None

    if "pv" in inp.techs:
        kwp = pv.required_peak_power_kwp(demand, inp.annual_irradiation_kwh_m2,
                                         inp.performance_ratio, inp.coverage)
        energy = kwp * inp.annual_irradiation_kwh_m2 * inp.performance_ratio
        results.append(_tech("pv", kwp, energy, demand, kwp * c.pv_capex_eur_per_kwp,
                             kwp * c.pv_om_eur_per_kwp_year, c.pv_lifetime_years,
                             c.pv_lifecycle_g_per_kwh / 1000.0, c))
    if "wind" in inp.techs:
        wd = size_wind_plant(inp.wind)
        kw = wd.installed_power_kw
        results.append(_tech("wind", kw, wd.annual_energy_kwh, demand,
                             kw * c.wind_capex_eur_per_kw, kw * c.wind_om_eur_per_kw_year,
                             c.wind_lifetime_years, c.wind_lifecycle_g_per_kwh / 1000.0, c))
    if "biomass" in inp.techs:
        th, el = default_efficiencies("biogas")
        b = inp.biomass
        bin_ = replace(b, pathway="biogas", eta_th=th, eta_el=el,
                       annual_electricity_demand_kwh=demand, coverage=inp.coverage)
        bd = size_biomass_plant(bin_)
        kwe = bd.electric_power_kw
        om = kwe * c.bio_om_eur_per_kwe_year + (
            bd.substrate_mass_a_t + bd.substrate_mass_b_t) * c.bio_feedstock_eur_per_t
        results.append(_tech("biomass", kwe, bd.electricity_net_kwh, demand,
                             kwe * c.bio_capex_eur_per_kwe, om, c.bio_lifetime_years,
                             c.bio_lifecycle_g_per_kwh / 1000.0, c))
    if "hydrogen" in inp.techs:
        hd, hin = _size_hydrogen(inp, target)
        energy = hd.hydrogen_kg * h2.H2_LHV_KWH_PER_KG
        el_capex = hd.electrolyser_kw * hin.electrolyser_capex_per_kw
        capex = (el_capex + hd.storage_kg * hin.storage_capex_per_kg
                 + hd.pv_kwp * hin.pv_capex_per_kwp + hd.wind_kw * hin.wind_capex_per_kw)
        running = (el_capex * hin.electrolyser_om_fraction + hd.cost_stack + hd.cost_water
                   + hd.pv_kwp * hin.pv_om_per_kwp + hd.wind_kw * hin.wind_om_per_kw)
        ref_price = c.h2_reference_price_eur_per_kg / h2.H2_LHV_KWH_PER_KG
        results.append(_tech(
            "hydrogen", hd.electrolyser_kw, energy, energy, capex, running, c.pv_lifetime_years,
            hd.co2_kg_per_kg / h2.H2_LHV_KWH_PER_KG, c, product="hydrogen",
            ref_price=ref_price, export_price=ref_price,
            ref_ef=c.h2_reference_kg_co2_per_kg / h2.H2_LHV_KWH_PER_KG,
            lcoe=hd.lcoh / h2.H2_LHV_KWH_PER_KG))
        results[-1] = replace(results[-1], coverage=energy / demand)

    if "hydro" in inp.techs:
        hyd = size_hydro_plant(replace(
            inp.hydro, annual_demand_kwh=demand, grid_ef=c.grid_kg_co2_per_kwh,
            lifecycle_g_per_kwh=c.hydro_lifecycle_g_per_kwh, capex_per_kw=c.hydro_capex_eur_per_kw,
            om_fraction=c.hydro_om_eur_per_kw_year / c.hydro_capex_eur_per_kw,
            life_years=c.hydro_lifetime_years, discount_rate=c.discount_rate,
            retail_price=c.retail_price_eur_per_kwh, export_price=c.export_price_eur_per_kwh))
        results.append(_tech("hydro", hyd.rated_kw, hyd.energy_kwh, demand, hyd.capex,
                             hyd.om_per_year, c.hydro_lifetime_years,
                             c.hydro_lifecycle_g_per_kwh / 1000.0, c))
    if "geothermal" in inp.techs:
        geo = size_geothermal_plant(replace(
            inp.geothermal, pathway="power", annual_electricity_demand_kwh=demand,
            coverage=inp.coverage, grid_ef=c.grid_kg_co2_per_kwh,
            lifecycle_g_per_kwh=c.geo_lifecycle_g_per_kwh, capex_per_kw_el=c.geo_capex_eur_per_kw,
            om_fraction=c.geo_om_eur_per_kw_year / c.geo_capex_eur_per_kw,
            life_years=c.geo_lifetime_years, discount_rate=c.discount_rate,
            retail_price=c.retail_price_eur_per_kwh, export_price=c.export_price_eur_per_kwh))
        results.append(_tech("geothermal", geo.net_kw, geo.electricity_kwh, demand, geo.capex,
                             geo.om_per_year, c.geo_lifetime_years,
                             c.geo_lifecycle_g_per_kwh / 1000.0, c))

    techs = tuple(results)
    return ComparisonResult(
        techs=techs,
        lowest_lcoe=_best(techs, lambda t: t.lcoe_eur_per_kwh),
        fastest_payback=_best(techs, lambda t: t.payback_years),
        highest_npv=_best(techs, lambda t: t.npv_eur, lowest=False),
        most_co2=_best(techs, lambda t: t.co2_avoided_t_per_year, lowest=False),
        wind_design=wd, biomass_design=bd, hydrogen_design=hd, hydro_design=hyd,
        geothermal_design=geo,
    )



def comparison_sensitivity(inp: ComparisonInputs):
    """LCOE of every technology when ALL capital costs, or the discount rate, or the energy
    target move by +/- 20 %: does the ranking survive?"""
    from resize_energy.core.sensitivity import STEPS

    def scaled(f_capex: float, f_rate: float) -> ComparisonInputs:
        c = inp.costs
        costs = replace(
            c, pv_capex_eur_per_kwp=c.pv_capex_eur_per_kwp * f_capex,
            wind_capex_eur_per_kw=c.wind_capex_eur_per_kw * f_capex,
            bio_capex_eur_per_kwe=c.bio_capex_eur_per_kwe * f_capex,
            h2_electrolyser_capex_eur_per_kw=c.h2_electrolyser_capex_eur_per_kw * f_capex,
            hydro_capex_eur_per_kw=c.hydro_capex_eur_per_kw * f_capex,
            geo_capex_eur_per_kw=c.geo_capex_eur_per_kw * f_capex,
            discount_rate=c.discount_rate * f_rate)
        if inp.carrier == "heat" and inp.heat is not None:
            from resize_energy.core.comparison_heat import scaled_heat
            return replace(inp, costs=costs, heat=scaled_heat(inp.heat, f_capex))
        return replace(inp, costs=costs)

    out: dict[str, dict[str, tuple[float, ...]]] = {"capex": {}, "rate": {}}
    for s in STEPS:
        for name, args in (("capex", (1.0 + s, 1.0)), ("rate", (1.0, 1.0 + s))):
            res = compare_technologies(scaled(*args))
            for t in res.techs:
                out[name].setdefault(t.key, ())
                out[name][t.key] += (t.lcoe_eur_per_kwh,)
    return out


def ranking_changes(sens: dict[str, dict[str, tuple[float, ...]]]) -> list[str]:
    """Scenarios ('capital costs', 'discount rate') in which the order by LCOE differs from
    the base case within the +/- 20 % range."""
    names = {"capex": "capital costs", "rate": "the discount rate"}
    out = []
    for key, data in sens.items():
        if len(data) < 2:
            continue
        mid = len(next(iter(data.values()))) // 2
        base = sorted(data, key=lambda t: data[t][mid])
        for idx in (0, -1):
            if sorted(data, key=lambda t: data[t][idx]) != base:
                out.append(names.get(key, key))
                break
    return out
