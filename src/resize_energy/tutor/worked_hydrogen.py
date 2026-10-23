"""Worked examples of the hydrogen topics, with the user's own numbers."""

from __future__ import annotations

from resize_energy.core import hydrogen as h2
from resize_energy.core.hydrogen_design import HydrogenDesign, HydrogenInputs


def hydrogen_worked_example(key: str, inp: HydrogenInputs, d: HydrogenDesign) -> str | None:
    if key == "hydrogen.efficiency":
        return (
            f"Stack and auxiliaries {inp.kwh_per_kg_stack:.1f} + compression "
            f"{d.compression_kwh_per_kg:.2f} = {d.kwh_per_kg_total:.1f} kWh/kg\n"
            f"eta (LHV) = {h2.H2_LHV_KWH_PER_KG} / {d.kwh_per_kg_total:.1f} = "
            f"{d.efficiency_lhv:.1%}\n"
            f"Electricity used = {d.hydrogen_kg:,.0f} kg x {d.kwh_per_kg_total:.1f} = "
            f"{d.electricity_kwh:,.0f} kWh"
        )
    if key == "hydrogen.dispatch":
        sources = [name for name, on in (("PV", inp.use_pv), ("wind", inp.use_wind),
                                         ("grid", inp.use_grid)) if on]
        return (
            f"Sources: {', '.join(sources)}; profile: {d.profile_source}\n"
            f"Renewable energy available {d.res_available_kwh:,.0f} kWh, used "
            f"{d.res_used_kwh:,.0f} kWh ({d.res_utilisation:.0%}), curtailed "
            f"{d.curtailed_kwh:,.0f} kWh\n"
            f"Grid {d.grid_kwh:,.0f} kWh ({d.grid_share:.0%} of the electricity); on for "
            f"{d.hours_on:,} h; minimum load {inp.min_load:.0%} x {d.electrolyser_kw:,.0f} kW = "
            f"{inp.min_load * d.electrolyser_kw:,.0f} kW\n"
            f"Full-load hours = {d.electricity_kwh:,.0f} / {d.electrolyser_kw:,.0f} = "
            f"{d.full_load_hours:,.0f} h"
        )
    if key == "hydrogen.sizing":
        if inp.mode == "demand":
            return (
                f"1 kW of electrolyser makes {d.hydrogen_kg / d.electrolyser_kw:.1f} kg/year\n"
                f"P_el = {inp.h2_demand_kg_per_year:,.0f} / "
                f"{d.hydrogen_kg / d.electrolyser_kw:.1f} = {d.electrolyser_kw:,.0f} kW\n"
                f"PV {d.pv_kwp:,.0f} kWp, wind {d.wind_kw:,.0f} kW"
            )
        return (
            f"Electrolyser {d.electrolyser_kw:,.0f} kW, PV {d.pv_kwp:,.0f} kWp, wind "
            f"{d.wind_kw:,.0f} kW\nHydrogen = {d.hydrogen_kg:,.0f} kg/year "
            f"({d.hydrogen_kg_per_day:,.0f} kg/day)"
        )
    if key == "hydrogen.compression":
        return (
            f"w = 4124 x 298 x ln({inp.storage_bar:.0f}/{inp.outlet_bar:.0f}) / 3.6e6 / 0.60 = "
            f"{d.compression_kwh_per_kg:.2f} kWh/kg"
        )
    if key == "hydrogen.storage":
        rho = h2.hydrogen_density_kg_m3(inp.storage_bar)
        return (
            f"Buffer = {d.hydrogen_kg_per_day:,.0f} kg/day x {inp.storage_days:.0f} days = "
            f"{d.storage_kg:,.0f} kg\nrho({inp.storage_bar:.0f} bar) = {rho:.1f} kg/m3\n"
            f"V = {d.storage_kg:,.0f} / {rho:.1f} = {d.storage_m3:,.1f} m3"
        )
    if key == "hydrogen.water":
        return (
            f"Water = {d.hydrogen_kg:,.0f} kg x {inp.water_l_per_kg:.0f} L/kg = "
            f"{d.water_m3:,.0f} m3 per year (stoichiometric minimum "
            f"{d.hydrogen_kg * h2.WATER_STOICHIOMETRIC_KG_PER_KG / 1000:,.0f} m3)\n"
            f"Oxygen = {d.hydrogen_kg:,.0f} x 7.94 = {d.oxygen_t:,.0f} t per year"
        )
    if key == "hydrogen.stack":
        return (
            f"Life = {inp.stack_hours:,.0f} h / {d.full_load_hours:,.0f} h per year = "
            f"{d.stack_life_years:.1f} years\n"
            f"Yearly share of the replacement = {inp.stack_cost_fraction:.0%} x "
            f"{d.electrolyser_kw * inp.electrolyser_capex_per_kw:,.0f} x "
            f"{d.full_load_hours:,.0f}/{inp.stack_hours:,.0f} = {d.cost_stack:,.0f} euro"
        )
    if key == "hydrogen.lcoh":
        return (
            f"Electrolyser {d.cost_electrolyser:,.0f} + stack {d.cost_stack:,.0f} + storage "
            f"{d.cost_storage:,.0f} + renewables {d.cost_res:,.0f} + grid {d.cost_grid:,.0f} + "
            f"water {d.cost_water:,.0f} euro/year\n"
            f"LCOH = {d.lcoh * d.hydrogen_kg:,.0f} / {d.hydrogen_kg:,.0f} = {d.lcoh:.2f} euro/kg"
        )
    if key == "hydrogen.co2":
        return (
            f"Grid {d.grid_kwh:,.0f} x {inp.grid_ef:.3f} + PV/wind used "
            f"({d.res_used_kwh:,.0f} kWh at {inp.pv_ef:.3f} / {inp.wind_ef:.3f}) = "
            f"{d.co2_kg_per_kg * d.hydrogen_kg / 1000:,.0f} t CO2\n"
            f"CI = {d.co2_kg_per_kg:.2f} kg CO2 per kg H2 (grey hydrogen: "
            f"{inp.grey_h2_kg_co2_per_kg:.1f}); saved {d.co2_saved_t_per_year:,.0f} t per year"
        )
    return None
