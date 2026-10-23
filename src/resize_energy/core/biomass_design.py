"""Preliminary design of a biomass plant: solid-fuel boiler / ORC cogeneration, or biogas CHP.

Solid pathways are heat-led (sized on the heat demand and its load-duration curve); the
biogas pathway is electricity-led (sized on the electricity demand), with the heat as a
by-product. Pure calculation, no GUI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from resize_energy.core import biomass as bm
from resize_energy.core.fuel_library import SOLID_FUELS, SUBSTRATES, SolidFuel, Substrate

Pathway = Literal["boiler", "orc", "biogas"]
PATHWAYS: dict[str, str] = {
    "boiler": "Solid biomass boiler (heat only)",
    "orc": "Solid biomass cogeneration (ORC: heat and power)",
    "biogas": "Biogas: digester and CHP engine (power-led, heat as by-product)",
}


@dataclass(frozen=True)
class BiomassInputs:
    """All inputs of the preliminary design (solid and biogas fields share one record)."""

    pathway: Pathway = "boiler"
    annual_heat_demand_kwh: float = 2_000_000.0
    peak_heat_kw: float = 800.0
    annual_electricity_demand_kwh: float = 1_500_000.0
    coverage: float = 0.85                 # share of the driving demand covered by biomass
    # --- solid fuels ---
    fuel: SolidFuel = SOLID_FUELS[0]
    eta_th: float = 0.85                   # useful heat / fuel energy (boiler or ORC)
    eta_el: float = 0.0                    # electricity / fuel energy (ORC 0.15, engine 0.38)
    storage_days: float = 10.0             # fuel autonomy at nominal power
    truck_volume_m3: float = 30.0
    # --- biogas ---
    substrate_a: Substrate = SUBSTRATES[2]
    substrate_b: Substrate = SUBSTRATES[0]
    share_b: float = 0.5                   # mass share of substrate B in the feed
    hrt_days: float = 45.0                 # hydraulic retention time
    operating_hours: float = 8000.0        # CHP full-load hours per year
    parasitic_electricity: float = 0.08    # share of the CHP electricity used by the plant
    digester_heat_share: float = 0.25      # share of the CHP heat used to heat the digester
    # --- emissions (kg CO2 per kWh); biogenic CO2 of the fuel is counted as neutral ---
    reference_heat_efficiency: float = 0.90
    reference_heat_ef: float = 0.202       # natural gas
    grid_ef: float = 0.25
    supply_chain_ef: float = 0.02          # fuel production, chipping, transport, methane slip


@dataclass(frozen=True)
class BiomassDesign:
    """Result of the preliminary design (fields of the other pathway stay at zero)."""

    pathway: str
    driving_demand_kwh: float
    thermal_power_kw: float = 0.0          # useful heat power
    electric_power_kw: float = 0.0          # electric power (gross for biogas)
    heat_useful_kwh: float = 0.0
    heat_credited_kwh: float = 0.0         # heat that really replaces fossil heat
    electricity_net_kwh: float = 0.0
    heat_coverage: float = 0.0
    electricity_coverage: float = 0.0
    fuel_energy_kwh: float = 0.0
    mass_t_per_year: float = 0.0
    co2_avoided_t_per_year: float = 0.0
    full_load_hours: float = 0.0
    # solid
    load_factor: float = 0.0
    power_ratio: float = 0.0
    lhv_as_received_kwh_per_kg: float = 0.0
    ash_t_per_year: float = 0.0
    storage_m3: float = 0.0
    deliveries_per_year: int = 0
    # biogas
    ch4_m3_per_year: float = 0.0
    biogas_m3_per_year: float = 0.0
    ch4_fraction: float = 0.0
    electricity_gross_kwh: float = 0.0
    heat_total_kwh: float = 0.0
    heat_digester_kwh: float = 0.0
    digester_volume_m3: float = 0.0
    working_volume_m3: float = 0.0
    olr_kg_vs_per_m3_day: float = 0.0
    crop_hectares: float = 0.0
    digestate_t_per_year: float = 0.0
    substrate_mass_a_t: float = 0.0
    substrate_mass_b_t: float = 0.0


def _check_common(inp: BiomassInputs) -> None:
    if not 0.0 < inp.coverage <= 1.0:
        raise ValueError("coverage must be in (0, 1]")
    if inp.pathway not in PATHWAYS:
        raise ValueError(f"unknown pathway {inp.pathway!r}")


def size_biomass_plant(inp: BiomassInputs) -> BiomassDesign:
    """Size the plant for the chosen pathway."""
    _check_common(inp)
    if inp.pathway == "biogas":
        return _size_biogas(inp)
    return _size_solid(inp)


def _co2(inp: BiomassInputs, heat_kwh: float, el_kwh: float, fuel_kwh: float) -> float:
    avoided = (heat_kwh / inp.reference_heat_efficiency * inp.reference_heat_ef
               + el_kwh * inp.grid_ef)
    return (avoided - fuel_kwh * inp.supply_chain_ef) / 1000.0


def _size_solid(inp: BiomassInputs) -> BiomassDesign:
    q, peak = inp.annual_heat_demand_kwh, inp.peak_heat_kw
    if q <= 0 or peak <= 0:
        raise ValueError("annual heat demand and peak heat load must be > 0")
    if not 0.0 < inp.eta_th <= 1.0:
        raise ValueError("thermal efficiency must be in (0, 1]")
    if inp.pathway == "orc" and not 0.0 < inp.eta_el < inp.eta_th:
        raise ValueError("for cogeneration the electrical efficiency must be in (0, eta_th)")
    if inp.pathway == "boiler" and inp.eta_el != 0.0:
        raise ValueError("a heat-only boiler has no electrical efficiency")
    if inp.eta_th + inp.eta_el > 1.0:
        raise ValueError("eta_th + eta_el cannot exceed 1")
    if inp.storage_days < 0 or inp.truck_volume_m3 <= 0:
        raise ValueError("storage days must be >= 0 and the truck volume > 0")
    load_factor = q / (peak * bm.HOURS_PER_YEAR)
    if load_factor > 1.0:
        raise ValueError("the peak heat load is too low for the annual demand "
                         f"(it would need {q / bm.HOURS_PER_YEAR:,.0f} kW or more)")
    ratio = bm.power_ratio_for_coverage(inp.coverage, load_factor)
    p_th = ratio * peak
    heat = inp.coverage * q
    fuel_kwh = heat / inp.eta_th
    el_kwh = fuel_kwh * inp.eta_el
    lhv = bm.lhv_as_received(inp.fuel.lhv_dry_kwh_per_kg, inp.fuel.moisture_wb)
    mass_t = fuel_kwh / lhv / 1000.0
    # storage: nominal-power consumption for the autonomy period, bin 80 % usable
    nominal_kg_per_h = p_th / inp.eta_th / lhv
    storage_m3 = nominal_kg_per_h * 24.0 * inp.storage_days / inp.fuel.bulk_density_kg_m3 / 0.8
    return BiomassDesign(
        pathway=inp.pathway,
        driving_demand_kwh=q,
        thermal_power_kw=p_th,
        electric_power_kw=p_th * inp.eta_el / inp.eta_th,
        heat_useful_kwh=heat,
        heat_credited_kwh=heat,
        electricity_net_kwh=el_kwh,
        heat_coverage=inp.coverage,
        electricity_coverage=(el_kwh / inp.annual_electricity_demand_kwh
                              if inp.annual_electricity_demand_kwh > 0 else 0.0),
        fuel_energy_kwh=fuel_kwh,
        mass_t_per_year=mass_t,
        co2_avoided_t_per_year=_co2(inp, heat, el_kwh, fuel_kwh),
        full_load_hours=heat / p_th,
        load_factor=load_factor,
        power_ratio=ratio,
        lhv_as_received_kwh_per_kg=lhv,
        ash_t_per_year=mass_t * (1.0 - inp.fuel.moisture_wb) * inp.fuel.ash_dry,
        storage_m3=storage_m3,
        deliveries_per_year=bm.deliveries_per_year(mass_t, inp.truck_volume_m3,
                                                   inp.fuel.bulk_density_kg_m3),
    )


def _size_biogas(inp: BiomassInputs) -> BiomassDesign:
    e_dem = inp.annual_electricity_demand_kwh
    if e_dem <= 0:
        raise ValueError("the biogas pathway is sized on the electricity demand: it must be > 0")
    eta_el, eta_th = inp.eta_el, inp.eta_th
    if not 0.0 < eta_el < 1.0 or not 0.0 < eta_th < 1.0:
        raise ValueError("CHP electrical and thermal efficiencies must be in (0, 1)")
    if eta_el + eta_th > 1.0:
        raise ValueError("eta_th + eta_el cannot exceed 1")
    if not 0.0 <= inp.share_b <= 1.0:
        raise ValueError("the share of substrate B must be in [0, 1]")
    if inp.hrt_days <= 0 or inp.operating_hours <= 0:
        raise ValueError("retention time and operating hours must be > 0")
    if not 0.0 <= inp.parasitic_electricity < 1.0 or not 0.0 <= inp.digester_heat_share < 1.0:
        raise ValueError("parasitic electricity and digester heat share must be in [0, 1)")
    a, b, s = inp.substrate_a, inp.substrate_b, inp.share_b
    el_net_target = inp.coverage * e_dem
    el_gross = el_net_target / (1.0 - inp.parasitic_electricity)
    fuel_kwh = el_gross / eta_el
    ch4_m3 = fuel_kwh / bm.CH4_LHV_KWH_PER_NM3
    ch4_per_t = (1.0 - s) * a.ch4_m3_per_t + s * b.ch4_m3_per_t
    biogas_per_t = (1.0 - s) * a.ch4_m3_per_t / a.ch4_fraction + s * b.ch4_m3_per_t / b.ch4_fraction
    mass_t = ch4_m3 / ch4_per_t
    biogas_m3 = mass_t * biogas_per_t
    m_a, m_b = (1.0 - s) * mass_t, s * mass_t
    per_day = mass_t / 365.0
    v_total = bm.digester_volume_m3(per_day, inp.hrt_days)
    v_work = per_day * inp.hrt_days
    vs_kg_day = (m_a * a.vs_fresh + m_b * b.vs_fresh) * 1000.0 / 365.0
    heat_total = el_gross * eta_th / eta_el
    heat_dig = inp.digester_heat_share * heat_total
    heat_use = heat_total - heat_dig
    hectares = sum(m / sub.crop_yield_t_per_ha
                   for m, sub in ((m_a, a), (m_b, b)) if sub.crop_yield_t_per_ha > 0)
    q = inp.annual_heat_demand_kwh
    credited = min(heat_use, q) if q > 0 else 0.0
    return BiomassDesign(
        pathway="biogas",
        driving_demand_kwh=e_dem,
        thermal_power_kw=heat_use / inp.operating_hours,
        electric_power_kw=el_gross / inp.operating_hours,
        heat_useful_kwh=heat_use,
        electricity_net_kwh=el_net_target,
        heat_coverage=min(1.0, heat_use / q) if q > 0 else 0.0,
        electricity_coverage=inp.coverage,
        fuel_energy_kwh=fuel_kwh,
        mass_t_per_year=mass_t,
        heat_credited_kwh=credited,
        co2_avoided_t_per_year=_co2(inp, credited, el_net_target, fuel_kwh),
        full_load_hours=inp.operating_hours,
        ch4_m3_per_year=ch4_m3,
        biogas_m3_per_year=biogas_m3,
        ch4_fraction=ch4_m3 / biogas_m3,
        electricity_gross_kwh=el_gross,
        heat_total_kwh=heat_total,
        heat_digester_kwh=heat_dig,
        digester_volume_m3=v_total,
        working_volume_m3=v_work,
        olr_kg_vs_per_m3_day=bm.organic_loading_rate(vs_kg_day, v_work),
        crop_hectares=hectares,
        digestate_t_per_year=mass_t - biogas_m3 * bm.BIOGAS_DENSITY_KG_PER_NM3 / 1000.0,
        substrate_mass_a_t=m_a,
        substrate_mass_b_t=m_b,
    )


def default_efficiencies(pathway: str) -> tuple[float, float]:
    """Typical (eta_th, eta_el) of each pathway, as fractions of the fuel energy (LHV)."""
    return {"boiler": (0.85, 0.0), "orc": (0.70, 0.15), "biogas": (0.45, 0.38)}[pathway]
