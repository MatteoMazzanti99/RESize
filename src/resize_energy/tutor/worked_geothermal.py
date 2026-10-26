"""Worked examples of the geothermal topics, with the user's own numbers."""

from __future__ import annotations

from resize_energy.core import biomass as bm
from resize_energy.core import geothermal as geo
from resize_energy.core.geothermal_design import GeothermalDesign, GeothermalInputs


def geothermal_worked_example(key: str, inp: GeothermalInputs, d: GeothermalDesign) -> str | None:
    m = inp.flow_per_well_kg_s
    if key == "geo.heat_power":
        raw = geo.thermal_power_kw(m, inp.reservoir_temp_c, inp.return_temp_c)
        return (
            f"P_th = {m:.0f} x 4.18 x ({inp.reservoir_temp_c:.0f} - {inp.return_temp_c:.0f}) = "
            f"{raw:,.0f} kW\nAfter the exchanger: {raw:,.0f} x {inp.exchanger_efficiency:.2f} = "
            f"{d.heat_per_pair_kw:,.0f} kW per pair of wells"
        )
    if key == "geo.coverage":
        n = bm.load_exponent(d.load_factor)
        return (
            f"LF = {inp.annual_heat_demand_kwh:,.0f} / ({inp.peak_heat_kw:,.0f} x 8760) = "
            f"{d.load_factor:.3f}  ->  n = {n:.2f}\n"
            f"{d.wells_pairs} pair(s) x {d.heat_per_pair_kw:,.0f} kW = "
            f"{d.wells_pairs * d.heat_per_pair_kw:,.0f} kW = {d.power_ratio:.0%} of the peak\n"
            f"f = {bm.covered_fraction(d.power_ratio, d.load_factor):.1%}; with the availability of "
            f"{inp.availability:.0%}: {d.heat_kwh:,.0f} kWh ({d.coverage:.0%} of the demand)"
        )
    if key == "geo.wells":
        return (
            f"z = ({inp.reservoir_temp_c:.0f} - {inp.ambient_temp_c:.0f}) / "
            f"{inp.gradient_k_per_km:.0f} K/km = {d.depth_m / 1000:.2f} km\n"
            f"Wells: {2 * d.wells_pairs} x {d.depth_m:,.0f} m x {inp.drilling_eur_per_m:,.0f} euro/m = "
            f"{2 * d.wells_pairs * d.depth_m * inp.drilling_eur_per_m:,.0f} euro"
        )
    if key == "geo.pumping":
        per_pair = geo.pump_power_kw(m, inp.pump_pressure_bar, inp.pump_efficiency)
        text = (
            f"P_pump = ({m:.0f} / 1000) x {inp.pump_pressure_bar * 100:,.0f} kPa / "
            f"{inp.pump_efficiency:.2f} = {per_pair:,.0f} kW per pair"
        )
        if d.spf:
            text += f"\nSPF = {d.heat_kwh:,.0f} kWh of heat / {d.heat_kwh / d.spf:,.0f} kWh = {d.spf:.0f}"
        return text
    if key == "geo.exergy":
        return (
            f"e = 4.18 x (({inp.reservoir_temp_c + 273.15:.1f} - {inp.ambient_temp_c + 273.15:.1f}) "
            f"- {inp.ambient_temp_c + 273.15:.1f} x ln({inp.reservoir_temp_c + 273.15:.1f} / "
            f"{inp.ambient_temp_c + 273.15:.1f})) = {d.exergy_kj_per_kg:.0f} kJ/kg\n"
            f"At {m:.0f} kg/s the brine carries {m * d.exergy_kj_per_kg:,.0f} kW of exergy"
        )
    if key == "geo.binary":
        heat = geo.thermal_power_kw(m, inp.reservoir_temp_c, inp.reinjection_temp_c)
        eta = geo.binary_cycle_efficiency(inp.reservoir_temp_c)
        return (
            f"eta = 0.09345 x {inp.reservoir_temp_c:.0f} - 2.32657 = {eta * 100:.1f} %\n"
            f"Heat taken = {m:.0f} x 4.18 x ({inp.reservoir_temp_c:.0f} - "
            f"{inp.reinjection_temp_c:.0f}) = {heat:,.0f} kW\n"
            f"P_gross = {eta:.3f} x {heat:,.0f} = {eta * heat:,.0f} kW per well"
        )
    if key == "geo.flash":
        gross = inp.flash_utilization * m * d.exergy_kj_per_kg
        return (
            f"P_gross = {inp.flash_utilization:.2f} x {m:.0f} x {d.exergy_kj_per_kg:.0f} = "
            f"{gross:,.0f} kW per well\nPlant auxiliaries: {inp.flash_parasitic:.0%} -> "
            f"{gross * (1 - inp.flash_parasitic):,.0f} kW before the pumps"
        )
    if key == "geo.net_power":
        return (
            f"Per pair: gross - plant - pumps = {d.net_kw / d.wells_pairs:,.0f} kW net\n"
            f"Target: {inp.coverage:.0%} x {inp.annual_electricity_demand_kwh:,.0f} / "
            f"{inp.operating_hours:,.0f} h = "
            f"{inp.coverage * inp.annual_electricity_demand_kwh / inp.operating_hours:,.0f} kW  ->  "
            f"{d.wells_pairs} pair(s), {d.net_kw:,.0f} kW\n"
            f"Energy = {d.net_kw:,.0f} x {inp.operating_hours:,.0f} = {d.electricity_kwh:,.0f} kWh "
            f"({d.coverage:.0%} of the demand)"
        )
    if key == "geo.economics":
        unit = "heat" if d.pathway == "heat" else "electricity"
        energy = d.heat_kwh if d.pathway == "heat" else d.electricity_kwh
        if d.pathway == "heat":
            capex = (f"CAPEX = wells + surface = {d.capex:,.0f} euro "
                     f"({d.capex / (d.wells_pairs * d.heat_per_pair_kw):,.0f} euro per kW of heat)")
        else:
            capex = f"CAPEX = {d.net_kw:,.0f} kW x {inp.capex_per_kw_el:,.0f} = {d.capex:,.0f} euro"
        return (
            f"{capex}\nO&M = {inp.om_fraction:.0%} x CAPEX = {d.om_per_year:,.0f} euro per year\n"
            f"Cost of the {unit} = {d.lcoe:.3f} euro/kWh over {energy:,.0f} kWh per year;  "
            f"NPV = {d.npv:,.0f} euro"
        )
    if key == "geo.co2":
        if d.pathway == "heat":
            pump_kwh = d.heat_kwh / d.spf if d.spf else 0.0
            return (
                f"Heat replaced: {d.heat_kwh:,.0f} / {inp.reference_heat_efficiency:.2f} x "
                f"{inp.reference_heat_ef:.3f} = "
                f"{d.heat_kwh / inp.reference_heat_efficiency * inp.reference_heat_ef / 1000:,.0f} t\n"
                f"Pumping: -{pump_kwh:,.0f} x {inp.grid_ef:.3f} = -{pump_kwh * inp.grid_ef / 1000:,.0f} t\n"
                f"Avoided = {d.co2_avoided_t_per_year:,.0f} t CO2 per year"
            )
        return (
            f"{d.electricity_kwh:,.0f} kWh x ({inp.grid_ef:.3f} - {inp.lifecycle_g_per_kwh / 1000:.3f}) "
            f"/ 1000 = {d.co2_avoided_t_per_year:,.0f} t CO2 per year"
        )
    return None
