"""Sanity checks of a green hydrogen design."""

from __future__ import annotations

from resize_energy.core.hydrogen_design import HydrogenDesign, HydrogenInputs
from resize_energy.tutor.checker import Finding

EU_RFNBO_KG_CO2_PER_KG = 3.4   # 70 % below 94 g/MJ, on the hydrogen LHV


def check_hydrogen_design(inp: HydrogenInputs, d: HydrogenDesign) -> list[Finding]:
    out: list[Finding] = []
    if d.full_load_hours < 2500:
        out.append(Finding(
            "warning", "full_load_low",
            f"The electrolyser runs only {d.full_load_hours:,.0f} full-load hours a year: the "
            "capital cost is spread over few kilograms. More renewable power per kW of "
            "electrolyser, a second source or a smaller electrolyser would help.",
            "hydrogen.sizing"))
    elif d.full_load_hours > 8000:
        out.append(Finding(
            "info", "full_load_high",
            f"{d.full_load_hours:,.0f} full-load hours: the plant runs almost all year, which "
            "needs a steady source (grid); check the stack and the maintenance stops.",
            "hydrogen.stack"))
    if d.res_available_kwh > 0 and d.res_utilisation < 0.7:
        out.append(Finding(
            "warning", "curtailment",
            f"Only {d.res_utilisation:.0%} of the renewable energy is used: "
            f"{d.curtailed_kwh:,.0f} kWh a year are curtailed. The renewable plant is large "
            "for the electrolyser (or the electrolyser is small).", "hydrogen.dispatch"))
    if d.co2_kg_per_kg > inp.grey_h2_kg_co2_per_kg:
        out.append(Finding(
            "error", "worse_than_grey",
            f"Carbon intensity {d.co2_kg_per_kg:.1f} kg CO2/kg is worse than hydrogen from "
            "natural gas: with this grid mix the electrolyser increases emissions.",
            "hydrogen.co2"))
    elif d.co2_kg_per_kg > EU_RFNBO_KG_CO2_PER_KG:
        out.append(Finding(
            "warning", "carbon_high",
            f"Carbon intensity {d.co2_kg_per_kg:.1f} kg CO2 per kg of hydrogen is above the "
            f"about {EU_RFNBO_KG_CO2_PER_KG} kg threshold for renewable hydrogen under EU "
            "rules (lower the grid share).", "hydrogen.co2"))
    if d.stack_life_years < 5:
        out.append(Finding(
            "warning", "stack_short",
            f"The stack would last {d.stack_life_years:.1f} years at these hours: replacement "
            "costs weigh heavily.", "hydrogen.stack"))
    if d.efficiency_lhv < 0.5:
        out.append(Finding(
            "warning", "efficiency_low",
            f"System efficiency {d.efficiency_lhv:.0%} (LHV) is low for PEM (typically "
            "57-67 %): check the consumption per kilogram.", "hydrogen.efficiency"))
    out.append(Finding(
        "info", "water",
        f"Water: {d.water_m3:,.0f} m3 a year of very pure water (and {d.oxygen_t:,.0f} t of "
        "oxygen as by-product).", "hydrogen.water"))
    if d.profile_source != "NASA POWER":
        out.append(Finding(
            "warning", "synthetic_profile",
            "The hourly profiles are synthetic (invented, not measured): the hours of "
            "operation are indicative. Fetch the real hourly data in step 2 when you are online.",
            "hydrogen.dispatch"))
    if not any(f.severity in ("warning", "error") for f in out):
        out.insert(0, Finding("ok", "design_ok", "No problem found with the main design rules.",
                              None))
    return out
