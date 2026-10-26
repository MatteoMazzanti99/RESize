"""Preliminary design of a hydrothermal geothermal plant: heat (doublet) or electricity.

Both pathways are sized on a demand: the heat pathway on the heat load-duration curve (like the
biomass boiler), the power pathway on the electricity demand. Wells are taken as identical, in
pairs (one production and one injection well). Pure calculation, no GUI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from resize_energy.core import biomass as bm
from resize_energy.core import economics as eco
from resize_energy.core import geothermal as geo

PATHWAYS: dict[str, str] = {
    "heat": "Direct heat: geothermal doublet and heat network",
    "power": "Electricity: binary or flash power plant",
}
PLANTS: dict[str, str] = {
    "auto": "Chosen from the temperature",
    "binary": "Binary (organic Rankine cycle)",
    "flash": "Single flash",
}
FLASH_FROM_C = 180.0       # the plant is a flash one from this brine temperature (auto)


@dataclass(frozen=True)
class GeothermalInputs:
    pathway: str = "heat"
    reservoir_temp_c: float = 90.0
    flow_per_well_kg_s: float = 50.0
    ambient_temp_c: float = 12.0
    gradient_k_per_km: float = 30.0
    pump_pressure_bar: float = 20.0        # production pump plus reinjection, per well pair
    pump_efficiency: float = 0.65
    availability: float = 0.95
    # --- heat ---
    annual_heat_demand_kwh: float = 30_000_000.0
    peak_heat_kw: float = 12_000.0
    coverage: float = 0.80
    return_temp_c: float = 45.0
    exchanger_efficiency: float = 0.95     # heat exchanger and network losses
    # --- power ---
    annual_electricity_demand_kwh: float = 15_000_000.0
    reinjection_temp_c: float = 70.0
    plant: str = "auto"
    flash_utilization: float = 0.31        # power / brine exergy of a 200 degC single-flash plant
    flash_parasitic: float = 0.05          # of the gross power
    operating_hours: float = 7900.0
    # --- emissions ---
    reference_heat_efficiency: float = 0.90
    reference_heat_ef: float = 0.202       # natural gas, kg CO2/kWh of fuel
    grid_ef: float = 0.25
    lifecycle_g_per_kwh: float = 38.0      # geothermal electricity, median of the IPCC AR5 range
    # --- costs ---
    drilling_eur_per_m: float = 1500.0     # one well, all included
    surface_eur_per_kw_th: float = 250.0   # heat exchangers, pumps, connection to the network
    capex_per_kw_el: float = 6300.0        # plant and wells, per kW of net power
    om_fraction: float = 0.03              # of the CAPEX per year
    life_years: float = 30.0
    discount_rate: float = 0.05
    heat_price_eur_per_kwh: float = 0.08   # value of the heat you replace
    retail_price: float = 0.20
    export_price: float = 0.10


@dataclass(frozen=True)
class GeothermalDesign:
    pathway: str
    plant: str                             # "heat", "binary" or "flash"
    wells_pairs: int                       # production wells (= injection wells)
    depth_m: float
    flow_total_kg_s: float
    thermal_power_kw: float = 0.0          # heat taken from the brine (all wells)
    heat_per_pair_kw: float = 0.0          # useful heat of one pair (heat pathway)
    heat_kwh: float = 0.0                  # useful heat delivered per year
    coverage: float = 0.0                  # of the heat or electricity demand
    power_ratio: float = 0.0               # plant power / peak heat load
    load_factor: float = 0.0
    efficiency: float = 0.0                # cycle efficiency (binary) or utilization (flash)
    exergy_kj_per_kg: float = 0.0
    gross_kw: float = 0.0
    pumps_kw: float = 0.0
    net_kw: float = 0.0                    # net electric power
    electricity_kwh: float = 0.0           # net electricity per year
    spf: float = 0.0                       # heat delivered per unit of pumping electricity
    full_load_hours: float = 0.0
    co2_avoided_t_per_year: float = 0.0
    capex: float = 0.0
    om_per_year: float = 0.0
    lcoe: float = 0.0                      # euro per kWh of heat or electricity
    savings_per_year: float = 0.0
    payback_years: float = 0.0
    npv: float = 0.0


def _check(i: GeothermalInputs) -> None:
    if i.pathway not in PATHWAYS:
        raise ValueError(f"unknown pathway {i.pathway!r}")
    if i.plant not in PLANTS:
        raise ValueError(f"unknown plant {i.plant!r}")
    if i.flow_per_well_kg_s <= 0:
        raise ValueError("the flow per well must be > 0")
    if i.reservoir_temp_c <= i.ambient_temp_c:
        raise ValueError("the reservoir must be warmer than the ambient")
    if not 0.0 < i.coverage <= 1.0:
        raise ValueError("coverage must be in (0, 1]")
    if not 0.0 < i.availability <= 1.0:
        raise ValueError("availability must be in (0, 1]")
    if i.drilling_eur_per_m < 0 or i.om_fraction < 0 or i.life_years <= 0:
        raise ValueError("costs and lifetime must be positive")


def size_geothermal_plant(i: GeothermalInputs) -> GeothermalDesign:
    _check(i)
    return _size_heat(i) if i.pathway == "heat" else _size_power(i)


def _size_heat(i: GeothermalInputs) -> GeothermalDesign:
    q, peak = i.annual_heat_demand_kwh, i.peak_heat_kw
    if q <= 0 or peak <= 0:
        raise ValueError("annual heat demand and peak heat load must be > 0")
    if not 0.0 < i.exchanger_efficiency <= 1.0:
        raise ValueError("exchanger efficiency must be in (0, 1]")
    if i.return_temp_c >= i.reservoir_temp_c:
        raise ValueError("the return temperature must be lower than the production temperature")
    load_factor = q / (peak * bm.HOURS_PER_YEAR)
    if load_factor > 1.0:
        raise ValueError("the peak heat load is too low for the annual demand "
                         f"(it would need {q / bm.HOURS_PER_YEAR:,.0f} kW or more)")
    ratio_target = bm.power_ratio_for_coverage(i.coverage, load_factor)
    p_pair = geo.thermal_power_kw(i.flow_per_well_kg_s, i.reservoir_temp_c,
                                  i.return_temp_c) * i.exchanger_efficiency
    pairs = max(1, math.ceil(ratio_target * peak / p_pair - 1e-9))
    ratio = min(1.0, pairs * p_pair / peak)
    covered = bm.covered_fraction(ratio, load_factor)
    heat = covered * q * i.availability
    depth = geo.well_depth_m(i.reservoir_temp_c, i.ambient_temp_c, i.gradient_k_per_km)
    pump_kw = geo.pump_power_kw(i.flow_per_well_kg_s, i.pump_pressure_bar, i.pump_efficiency)
    full_hours = heat / (pairs * p_pair)
    pump_kwh = pairs * pump_kw * full_hours
    capex = pairs * 2.0 * depth * i.drilling_eur_per_m + pairs * p_pair * i.surface_eur_per_kw_th
    om = capex * i.om_fraction
    pump_cost = pump_kwh * i.retail_price
    crf = eco.capital_recovery_factor(i.discount_rate, i.life_years)
    net_benefit = heat * i.heat_price_eur_per_kwh - pump_cost - om
    co2 = (heat / i.reference_heat_efficiency * i.reference_heat_ef
           - pump_kwh * i.grid_ef) / 1000.0
    return GeothermalDesign(
        pathway="heat", plant="heat", wells_pairs=pairs, depth_m=depth,
        flow_total_kg_s=pairs * i.flow_per_well_kg_s,
        thermal_power_kw=pairs * geo.thermal_power_kw(i.flow_per_well_kg_s, i.reservoir_temp_c,
                                                      i.return_temp_c),
        heat_per_pair_kw=p_pair, heat_kwh=heat, coverage=heat / q, power_ratio=ratio,
        load_factor=load_factor, pumps_kw=pairs * pump_kw,
        spf=heat / pump_kwh if pump_kwh > 0 else 0.0, full_load_hours=full_hours,
        co2_avoided_t_per_year=co2, capex=capex, om_per_year=om,
        lcoe=(capex * crf + om + pump_cost) / heat, savings_per_year=net_benefit + om,
        payback_years=eco.simple_payback_years(capex, net_benefit),
        npv=eco.npv(capex, net_benefit, i.discount_rate, i.life_years))


def plant_type(i: GeothermalInputs) -> str:
    if i.plant != "auto":
        return i.plant
    return "flash" if i.reservoir_temp_c >= FLASH_FROM_C else "binary"


def _size_power(i: GeothermalInputs) -> GeothermalDesign:
    e_dem = i.annual_electricity_demand_kwh
    if e_dem <= 0:
        raise ValueError("the electricity demand must be > 0")
    if i.operating_hours <= 0 or i.operating_hours > geo.HOURS_PER_YEAR:
        raise ValueError("operating hours must be in (0, 8760]")
    kind = plant_type(i)
    m = i.flow_per_well_kg_s
    exergy = geo.brine_exergy_kj_per_kg(i.reservoir_temp_c, i.ambient_temp_c)
    if kind == "binary":
        if i.reinjection_temp_c >= i.reservoir_temp_c:
            raise ValueError("the reinjection temperature must be lower than the production "
                             "temperature")
        eff = geo.binary_cycle_efficiency(i.reservoir_temp_c)
        gross = eff * geo.thermal_power_kw(m, i.reservoir_temp_c, i.reinjection_temp_c)
        plant_own = 0.0
    else:
        if not 0.0 < i.flash_utilization < 1.0 or not 0.0 <= i.flash_parasitic < 1.0:
            raise ValueError("flash utilization must be in (0, 1) and parasitic share in [0, 1)")
        eff = i.flash_utilization
        gross = eff * m * exergy
        plant_own = i.flash_parasitic * gross
    pump = geo.pump_power_kw(m, i.pump_pressure_bar, i.pump_efficiency)
    net_pair = gross - plant_own - pump
    if net_pair <= 0:
        raise ValueError("the pumps use more power than the plant makes: raise the "
                         "temperature or lower the pumping pressure")
    target_kw = i.coverage * e_dem / i.operating_hours
    pairs = max(1, math.ceil(target_kw / net_pair - 1e-9))
    net = pairs * net_pair
    energy = net * i.operating_hours
    depth = geo.well_depth_m(i.reservoir_temp_c, i.ambient_temp_c, i.gradient_k_per_km)
    capex = net * i.capex_per_kw_el
    om = capex * i.om_fraction
    savings = eco.annual_savings(energy, e_dem, i.retail_price, i.export_price)
    net_benefit = savings - om
    return GeothermalDesign(
        pathway="power", plant=kind, wells_pairs=pairs, depth_m=depth,
        flow_total_kg_s=pairs * m,
        thermal_power_kw=pairs * geo.thermal_power_kw(m, i.reservoir_temp_c,
                                                      min(i.reinjection_temp_c, i.reservoir_temp_c)),
        coverage=energy / e_dem, efficiency=eff, exergy_kj_per_kg=exergy,
        gross_kw=pairs * gross, pumps_kw=pairs * pump, net_kw=net, electricity_kwh=energy,
        full_load_hours=i.operating_hours,
        co2_avoided_t_per_year=eco.co2_avoided_kg_per_year(energy, i.grid_ef,
                                                           i.lifecycle_g_per_kwh) / 1000.0,
        capex=capex, om_per_year=om, lcoe=eco.lcoe(capex, om, energy, i.discount_rate, i.life_years),
        savings_per_year=savings, payback_years=eco.simple_payback_years(capex, net_benefit),
        npv=eco.npv(capex, net_benefit, i.discount_rate, i.life_years))
