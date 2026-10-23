"""Worked examples of the battery topics, with the user's own numbers."""

from __future__ import annotations

from resize_energy.core.battery_design import BatteryDesign, BatteryInputs


def battery_worked_example(key: str, inp: BatteryInputs, d: BatteryDesign) -> str | None:
    if key == "battery.selfuse":
        return (
            f"Load {d.load_kwh:,.0f} kWh, production {d.generation_kwh:,.0f} kWh\n"
            f"Import: {d.import_without_kwh:,.0f} kWh without battery, {d.import_kwh:,.0f} kWh "
            f"with it\n"
            f"Self-sufficiency = 1 - {d.import_kwh:,.0f} / {d.load_kwh:,.0f} = "
            f"{d.self_sufficiency:.0%} (was {d.self_sufficiency_without:.0%})\n"
            f"Self-consumption = {d.self_consumption:.0%} (was {d.self_consumption_without:.0%})"
        )
    if key == "battery.load":
        return (
            f"Type: {inp.load_kind}; yearly demand {inp.annual_demand_kwh:,.0f} kWh = "
            f"{d.daily_load_kwh:,.1f} kWh per day on average"
        )
    if key == "battery.dispatch":
        return (
            f"Used directly {d.direct_kwh:,.0f} kWh; from the battery {d.battery_kwh:,.0f} kWh; "
            f"imported {d.import_kwh:,.0f} kWh; exported {d.export_kwh:,.0f} kWh "
            f"(was {d.export_without_kwh:,.0f} kWh)"
        )
    if key == "battery.capacity":
        return (
            f"Usable = {d.capacity_kwh:.1f} kWh x {inp.usable_fraction:.0%} x {inp.health:.0%} "
            f"= {d.capacity_kwh * inp.usable_fraction * inp.health:.1f} kWh\n"
            f"Power = {inp.c_rate} x {d.capacity_kwh:.1f} = {d.power_kw:.1f} kW\n"
            f"The battery equals {d.capacity_kwh / d.daily_load_kwh:.0%} of the daily load"
        )
    if key == "battery.efficiency":
        return (
            f"Round trip {inp.eta_roundtrip:.0%}: energy lost in the battery "
            f"{d.loss_kwh:,.0f} kWh a year"
        )
    if key == "battery.diminishing":
        pts = "; ".join(f"{p.capacity_kwh:.0f} kWh -> {p.self_sufficiency:.0%}" for p in d.sweep)
        return "Self-sufficiency by capacity: " + pts
    if key == "battery.life":
        return (
            f"Cycles per year = {d.battery_kwh:,.0f} / {d.usable_kwh:.1f} = "
            f"{d.cycles_per_year:.0f}\n"
            f"By cycles: {inp.cycle_life:,.0f} / {d.cycles_per_year:.0f} years; by time: "
            f"{inp.calendar_life_years:.0f} years -> life {d.life_years:.1f} years "
            f"({d.life_limit})"
        ) if d.cycles_per_year > 0 else "The battery is never used."
    if key == "battery.economics":
        return (
            f"S = ({d.import_without_kwh:,.0f} - {d.import_kwh:,.0f}) x {inp.retail_price} - "
            f"({d.export_without_kwh:,.0f} - {d.export_kwh:,.0f}) x {inp.export_price} = "
            f"{d.savings_per_year:,.0f} euro/year\n"
            f"Less O&M {d.om_per_year:,.0f} = {d.net_benefit_per_year:,.0f} euro/year on a "
            f"CAPEX of {d.capex:,.0f} euro\n"
            f"Payback {d.payback_years:.1f} years; NPV over {d.life_years:.0f} years "
            f"{d.npv:,.0f} euro"
        )
    if key == "battery.lcos":
        margin = inp.retail_price - inp.export_price
        return (
            f"LCOS = {d.lcos:.3f} euro/kWh; margin retail - export = {margin:.2f} euro/kWh "
            f"(before losses)"
        )
    if key == "battery.co2":
        return (
            f"({d.import_without_kwh:,.0f} - {d.import_kwh:,.0f}) kWh x {inp.grid_ef} kg/kWh = "
            f"{d.co2_avoided_t_per_year * 1000:,.0f} kg CO2 per year"
        )
    return None
