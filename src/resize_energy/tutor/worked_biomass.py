"""Worked examples of the biomass topics, with the user's own numbers."""

from __future__ import annotations

from resize_energy.core import biomass as bm
from resize_energy.core.biomass_design import BiomassDesign, BiomassInputs


def biomass_worked_example(key: str, inp: BiomassInputs, d: BiomassDesign) -> str | None:
    f = inp.fuel
    if key == "biomass.lhv":
        return (
            f"{f.name}: LHV_dry = {f.lhv_dry_kwh_per_kg:.2f} kWh/kg, M = {f.moisture_wb:.0%}\n"
            f"LHV_ar = {f.lhv_dry_kwh_per_kg:.2f} x (1 - {f.moisture_wb:.2f}) - "
            f"{bm.EVAPORATION_KWH_PER_KG:.3f} x {f.moisture_wb:.2f} = "
            f"{d.lhv_as_received_kwh_per_kg:.2f} kWh/kg"
        )
    if key == "biomass.load_duration":
        n = bm.load_exponent(d.load_factor)
        return (
            f"LF = {inp.annual_heat_demand_kwh:,.0f} / ({inp.peak_heat_kw:,.0f} x 8760) = "
            f"{d.load_factor:.3f}  ->  n = 1/LF - 1 = {n:.2f}\n"
            f"A plant of {d.power_ratio:.0%} of the peak covers "
            f"f = {bm.covered_fraction(d.power_ratio, d.load_factor):.1%} of the heat"
        )
    if key == "biomass.plant_power":
        text = (
            f"f(x) = {inp.coverage:.0%}  ->  x = {d.power_ratio:.3f}\n"
            f"P_th = {d.power_ratio:.3f} x {inp.peak_heat_kw:,.0f} kW = "
            f"{d.thermal_power_kw:,.0f} kW\n"
            f"Full-load hours = {d.heat_useful_kwh:,.0f} / {d.thermal_power_kw:,.0f} = "
            f"{d.full_load_hours:,.0f} h"
        )
        if inp.eta_el > 0:
            text += (f"\nP_el = {d.thermal_power_kw:,.0f} x {inp.eta_el:.2f} / {inp.eta_th:.2f} = "
                     f"{d.electric_power_kw:,.0f} kW")
        return text
    if key == "biomass.fuel_mass":
        return (
            f"E_fuel = {d.heat_useful_kwh:,.0f} / {inp.eta_th:.2f} = {d.fuel_energy_kwh:,.0f} kWh\n"
            f"m = {d.fuel_energy_kwh:,.0f} / {d.lhv_as_received_kwh_per_kg:.2f} = "
            f"{d.mass_t_per_year:,.0f} t per year (ash: {d.ash_t_per_year:.1f} t)"
        )
    if key == "biomass.storage":
        return (
            f"Nominal consumption = {d.thermal_power_kw:,.0f} / ({inp.eta_th:.2f} x "
            f"{d.lhv_as_received_kwh_per_kg:.2f}) = "
            f"{d.thermal_power_kw / inp.eta_th / d.lhv_as_received_kwh_per_kg:,.0f} kg/h\n"
            f"V = that x 24 h x {inp.storage_days:.0f} days / ({f.bulk_density_kg_m3:.0f} x 0.8) = "
            f"{d.storage_m3:,.0f} m3\n"
            f"Deliveries: {d.mass_t_per_year:,.0f} t / "
            f"({inp.truck_volume_m3:.0f} m3 x {f.bulk_density_kg_m3:.0f} kg/m3) = "
            f"{d.deliveries_per_year} truck loads per year"
        )
    a, b, s = inp.substrate_a, inp.substrate_b, inp.share_b
    if key == "biomass.biogas_yield":
        return (
            f"Mix: {1 - s:.0%} {a.name} ({a.ch4_m3_per_t:.0f} m3 CH4/t) + {s:.0%} {b.name} "
            f"({b.ch4_m3_per_t:.0f} m3 CH4/t)\n"
            f"Methane needed = {d.electricity_gross_kwh / inp.eta_el:,.0f} kWh / 9.97 = "
            f"{d.ch4_m3_per_year:,.0f} Nm3 per year\n"
            f"Substrate = {d.mass_t_per_year:,.0f} t per year; biogas "
            f"{d.biogas_m3_per_year:,.0f} Nm3 ({d.ch4_fraction:.0%} CH4)"
        )
    if key == "biomass.chp_biogas":
        return (
            f"E_gross = {d.electricity_net_kwh:,.0f} / (1 - {inp.parasitic_electricity:.2f}) = "
            f"{d.electricity_gross_kwh:,.0f} kWh\n"
            f"P_el = {d.electricity_gross_kwh:,.0f} / {inp.operating_hours:,.0f} h = "
            f"{d.electric_power_kw:,.0f} kW\n"
            f"E_CH4 = {d.electricity_gross_kwh:,.0f} / {inp.eta_el:.2f} = "
            f"{d.fuel_energy_kwh:,.0f} kWh"
        )
    if key == "biomass.digester":
        per_day = d.mass_t_per_year / 365.0
        return (
            f"Feed = {d.mass_t_per_year:,.0f} / 365 = {per_day:.1f} t/day\n"
            f"V_work = {per_day:.1f} x {inp.hrt_days:.0f} d = {d.working_volume_m3:,.0f} m3\n"
            f"V_total = {d.working_volume_m3:,.0f} / 0.9 = {d.digester_volume_m3:,.0f} m3"
        )
    if key == "biomass.olr":
        return (
            f"OLR = {d.olr_kg_vs_per_m3_day * d.working_volume_m3:,.0f} kg VS/day / "
            f"{d.working_volume_m3:,.0f} m3 = {d.olr_kg_vs_per_m3_day:.2f} kg VS/(m3 d)"
        )
    if key == "biomass.heat_balance":
        return (
            f"Q_total = {d.electricity_gross_kwh:,.0f} x {inp.eta_th:.2f} / {inp.eta_el:.2f} = "
            f"{d.heat_total_kwh:,.0f} kWh\n"
            f"Digester heating = {inp.digester_heat_share:.0%} -> {d.heat_digester_kwh:,.0f} kWh\n"
            f"Useful heat = {d.heat_useful_kwh:,.0f} kWh "
            f"({d.heat_useful_kwh / inp.annual_heat_demand_kwh:.0%} of the heat demand)"
            if inp.annual_heat_demand_kwh > 0 else
            f"Useful heat = {d.heat_useful_kwh:,.0f} kWh (no heat demand entered)"
        )
    if key == "biomass.land":
        return (
            f"{a.name}: {d.substrate_mass_a_t:,.0f} t"
            + (f" / {a.crop_yield_t_per_ha:.0f} t/ha" if a.crop_yield_t_per_ha else " (no land)")
            + f"\n{b.name}: {d.substrate_mass_b_t:,.0f} t"
            + (f" / {b.crop_yield_t_per_ha:.0f} t/ha" if b.crop_yield_t_per_ha else " (no land)")
            + f"\nArea = {d.crop_hectares:,.0f} ha; digestate = {d.digestate_t_per_year:,.0f} t/year"
        )
    if key == "biomass.co2":
        return (
            f"Heat replaced: {d.heat_credited_kwh:,.0f} / {inp.reference_heat_efficiency:.2f} x "
            f"{inp.reference_heat_ef:.3f} = "
            f"{d.heat_credited_kwh / inp.reference_heat_efficiency * inp.reference_heat_ef / 1000:,.0f}"
            f" t\nElectricity: {d.electricity_net_kwh:,.0f} x {inp.grid_ef:.3f} = "
            f"{d.electricity_net_kwh * inp.grid_ef / 1000:,.0f} t\n"
            f"Supply chain: -{d.fuel_energy_kwh:,.0f} x {inp.supply_chain_ef:.3f} = "
            f"-{d.fuel_energy_kwh * inp.supply_chain_ef / 1000:,.0f} t\n"
            f"Avoided = {d.co2_avoided_t_per_year:,.0f} t CO2 per year"
        )
    return None
