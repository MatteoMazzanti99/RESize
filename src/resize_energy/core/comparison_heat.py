"""Comparison of the technologies that deliver HEAT, sized for the same heat demand.

Biomass boiler, geothermal doublet with a heat network, solar thermal collectors and a
ground-source heat pump (borehole field) are compared with the heat of a gas boiler. Every plant
covers the same share of the same yearly heat demand; running costs (fuel, pumps, heat-pump
electricity) are counted in the yearly cost, so the LCOH is the cost of one kWh of useful heat.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from resize_energy.core import biomass as bm
from resize_energy.core.bhe_design import BheInputs, size_bhe_field
from resize_energy.core.biomass_design import (
    default_efficiencies,
    size_biomass_plant,
)
from resize_energy.core.comparison import (
    HEAT_TECHS,
    ComparisonInputs,
    ComparisonResult,
    TechResult,
    _best,
    _tech,
)
from resize_energy.core.geothermal_design import GeothermalInputs, size_geothermal_plant
from resize_energy.core.solar_thermal import WATER_KWH_PER_L_K
from resize_energy.core.solar_thermal_design import (
    SolarThermalInputs,
    collector_of,
    size_solar_thermal,
)

SOLAR_KW_PER_M2 = 0.7          # nominal thermal power of one m2 of collector (1000 W/m2 x ~0.7)

HEAT_NAMES = {"biomass": "Biomass boiler", "geothermal": "Geothermal heat (doublet)",
              "solar": "Solar thermal", "bhe": "Ground-source heat pump"}


@dataclass(frozen=True)
class HeatCosts:
    """Heat prices and the costs that the single-technology wizards do not carry."""

    gas_heat_eur_per_kwh: float = 0.09          # useful heat from a gas boiler (the reference)
    gas_boiler_efficiency: float = 0.90
    gas_kg_co2_per_kwh_fuel: float = 0.202
    boiler_capex_eur_per_kw: float = 400.0      # biomass boiler, silo and flue
    boiler_om_fraction: float = 0.04            # of the CAPEX per year
    boiler_life_years: float = 20.0
    wood_eur_per_t: float = 120.0               # as received
    boiler_lifecycle_g_per_kwh: float = 25.0    # supply chain, per kWh of heat
    heat_pump_capex_eur_per_kw: float = 700.0   # the heat pump itself, per kW of heat
    heat_pump_life_years: float = 20.0
    geo_life_years: float = 30.0
    solar_lifecycle_g_per_kwh: float = 25.0


@dataclass(frozen=True)
class HeatInputs:
    """The common heat demand and the per-technology templates."""

    annual_heat_kwh: float = 2_000_000.0
    peak_kw: float = 1_000.0
    coverage: float = 0.80
    costs: HeatCosts = field(default_factory=HeatCosts)
    supply_temp_c: float = 55.0                  # delivery temperature (the solar collectors)
    ground_temp_c: float = 12.0                  # mean ambient / undisturbed ground (solar, heat pump)
    solar: SolarThermalInputs = field(default_factory=SolarThermalInputs)
    bhe: BheInputs = field(default_factory=BheInputs)
    geothermal: GeothermalInputs = field(
        default_factory=lambda: GeothermalInputs(pathway="heat", reservoir_temp_c=90.0,
                                                 flow_per_well_kg_s=50.0))


def scaled_heat(h: HeatInputs, factor: float) -> HeatInputs:
    """The heat inputs with every capital cost multiplied by ``factor`` (for the sensitivity)."""
    hc = h.costs
    return replace(
        h,
        costs=replace(hc, boiler_capex_eur_per_kw=hc.boiler_capex_eur_per_kw * factor,
                      heat_pump_capex_eur_per_kw=hc.heat_pump_capex_eur_per_kw * factor),
        geothermal=replace(h.geothermal, drilling_eur_per_m=h.geothermal.drilling_eur_per_m * factor,
                           surface_eur_per_kw_th=h.geothermal.surface_eur_per_kw_th * factor),
        bhe=replace(h.bhe, drilling_eur_per_m=h.bhe.drilling_eur_per_m * factor),
        solar=replace(h.solar, collector_cost_per_m2=collector_of(h.solar).cost_per_m2 * factor,
                      store_cost_per_litre=h.solar.store_cost_per_litre * factor,
                      fixed_cost=h.solar.fixed_cost * factor))


def _check(inp: ComparisonInputs, h: HeatInputs) -> None:
    if len(inp.techs) < 2:
        raise ValueError("choose at least two technologies that deliver heat")
    if any(t not in HEAT_TECHS for t in inp.techs) or len(set(inp.techs)) != len(inp.techs):
        raise ValueError("unknown or repeated heat technology")
    if h.annual_heat_kwh <= 0 or h.peak_kw <= 0:
        raise ValueError("the heat demand and the peak power must be > 0")
    if h.annual_heat_kwh > h.peak_kw * bm.HOURS_PER_YEAR:
        raise ValueError("the peak heat load is too low for the annual demand "
                         f"(it would need {h.annual_heat_kwh / bm.HOURS_PER_YEAR:,.0f} kW or more)")
    if not 0.0 < h.coverage <= 1.0:
        raise ValueError("the share of the heat to cover must be in (0, 1]")
    if h.costs.gas_heat_eur_per_kwh <= 0:
        raise ValueError("the reference heat price must be > 0")
    if not 0 <= inp.costs.discount_rate < 1:
        raise ValueError("discount rate must be in [0, 1)")


def _heat_tech(key: str, kw: float, heat: float, demand: float, capex: float, running: float,
               life: float, own_ef_kg_per_kwh: float, inp: ComparisonInputs, h: HeatInputs,
               ) -> TechResult:
    c, hc = inp.costs, h.costs
    ref_ef = hc.gas_kg_co2_per_kwh_fuel / hc.gas_boiler_efficiency
    t = _tech(key, kw, heat, demand, capex, running, life, own_ef_kg_per_kwh, c,
              product="heat", ref_price=hc.gas_heat_eur_per_kwh, export_price=0.0, ref_ef=ref_ef)
    return replace(t, name=HEAT_NAMES[key])


def compare_heat(inp: ComparisonInputs) -> ComparisonResult:
    """Size the chosen heat plants for the same demand; LCOH, payback, NPV and CO2.

    The solar field is sized on a flat (hot-water type) load and the other plants on the load
    duration curve; the cost of the electricity of the pumps and of the heat pump is a running
    cost. Heat is valued at the gas-boiler heat price.
    """
    h = inp.heat
    if h is None:
        raise ValueError("the heat comparison needs the heat demand")
    _check(inp, h)
    c, hc = inp.costs, h.costs
    demand = h.annual_heat_kwh
    load_factor = demand / (h.peak_kw * bm.HOURS_PER_YEAR)
    results: list[TechResult] = []
    notes: list[str] = []
    designs: dict[str, object] = {}

    def run(key: str, build) -> None:
        try:
            results.append(build())
        except ValueError as exc:
            notes.append(f"{HEAT_NAMES[key]} left out: {exc}")

    def biomass() -> TechResult:
        eta_th, _ = default_efficiencies("boiler")
        bd = size_biomass_plant(replace(
            inp.biomass, pathway="boiler", eta_th=eta_th, eta_el=0.0,
            annual_heat_demand_kwh=demand, peak_heat_kw=h.peak_kw, coverage=h.coverage,
            annual_electricity_demand_kwh=0.0))
        designs["biomass"] = bd
        kw = bd.thermal_power_kw
        capex = kw * hc.boiler_capex_eur_per_kw
        running = capex * hc.boiler_om_fraction + bd.mass_t_per_year * hc.wood_eur_per_t
        return _heat_tech("biomass", kw, bd.heat_useful_kwh, demand, capex, running,
                          hc.boiler_life_years, hc.boiler_lifecycle_g_per_kwh / 1000.0, inp, h)

    def geothermal() -> TechResult:
        geo = size_geothermal_plant(replace(
            h.geothermal, pathway="heat", annual_heat_demand_kwh=demand,
            peak_heat_kw=h.peak_kw, coverage=h.coverage, grid_ef=c.grid_kg_co2_per_kwh,
            life_years=hc.geo_life_years, discount_rate=c.discount_rate,
            heat_price_eur_per_kwh=hc.gas_heat_eur_per_kwh,
            retail_price=c.retail_price_eur_per_kwh, export_price=c.export_price_eur_per_kwh,
            reference_heat_efficiency=hc.gas_boiler_efficiency,
            reference_heat_ef=hc.gas_kg_co2_per_kwh_fuel))
        designs["geothermal"] = geo
        pump_kwh = geo.pumps_kw * geo.full_load_hours
        running = geo.om_per_year + pump_kwh * c.retail_price_eur_per_kwh
        own = pump_kwh * c.grid_kg_co2_per_kwh / geo.heat_kwh
        return _heat_tech("geothermal", geo.heat_per_pair_kw * geo.wells_pairs, geo.heat_kwh,
                          demand, geo.capex, running, hc.geo_life_years, own, inp, h)

    def solar() -> TechResult:
        litres = demand / (365.0 * WATER_KWH_PER_L_K * max(1.0, h.supply_temp_c - h.ground_temp_c))
        st = size_solar_thermal(replace(
            h.solar, dhw_litres_per_day=litres, t_use_c=h.supply_temp_c,
            cooling_kwh_per_year=0.0, latitude_deg=inp.latitude_deg,
            irradiation_kwh_m2=inp.annual_irradiation_kwh_m2, t_mean_c=h.ground_temp_c,
            mode="target", target_fraction=h.coverage, discount_rate=c.discount_rate,
            heat_price=hc.gas_heat_eur_per_kwh, grid_ef_kg_per_kwh=c.grid_kg_co2_per_kwh),
            with_sweep=False, with_sensitivity=False)
        designs["solar"] = st
        return _heat_tech("solar", st.area_m2 * SOLAR_KW_PER_M2, st.solar_useful_kwh, demand,
                          st.capex, st.om_per_year, h.solar.life_years,
                          hc.solar_lifecycle_g_per_kwh / 1000.0, inp, h)

    def ground_source() -> TechResult:
        ratio = bm.power_ratio_for_coverage(h.coverage, load_factor)
        heat = h.coverage * demand
        b = h.bhe
        d = size_bhe_field(replace(
            b, heating_kwh_per_year=heat, heating_peak_kw=ratio * h.peak_kw,
            cooling_kwh_per_year=0.0, cooling_peak_kw=0.0, ground_temp_c=h.ground_temp_c,
            life_years=hc.heat_pump_life_years, discount_rate=c.discount_rate))
        designs["bhe"] = d
        hp_kw = ratio * h.peak_kw
        elec_kwh = heat / b.cop_seasonal
        capex = d.capex + hp_kw * hc.heat_pump_capex_eur_per_kw
        running = d.om_per_year + elec_kwh * c.retail_price_eur_per_kwh
        return _heat_tech("bhe", hp_kw, heat, demand, capex, running, hc.heat_pump_life_years,
                          elec_kwh * c.grid_kg_co2_per_kwh / heat, inp, h)

    for key, build in (("biomass", biomass), ("geothermal", geothermal), ("solar", solar),
                       ("bhe", ground_source)):
        if key in inp.techs:
            run(key, build)
    if len(results) < 2:
        raise ValueError("fewer than two heat technologies can serve this demand. "
                         + " ".join(notes))

    techs = tuple(results)
    return ComparisonResult(
        techs=techs,
        lowest_lcoe=_best(techs, lambda t: t.lcoe_eur_per_kwh),
        fastest_payback=_best(techs, lambda t: t.payback_years),
        highest_npv=_best(techs, lambda t: t.npv_eur, lowest=False),
        most_co2=_best(techs, lambda t: t.co2_avoided_t_per_year, lowest=False),
        biomass_design=designs.get("biomass"), geothermal_design=designs.get("geothermal"),
        solar_design=designs.get("solar"), bhe_design=designs.get("bhe"), notes=tuple(notes),
    )
