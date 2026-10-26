"""Sanity checks of a geothermal design (deterministic, offline)."""

from __future__ import annotations

from resize_energy.core.geothermal_design import FLASH_FROM_C, GeothermalDesign, GeothermalInputs
from resize_energy.tutor.checker import Finding


def check_geothermal_design(inp: GeothermalInputs, d: GeothermalDesign) -> list[Finding]:
    out: list[Finding] = []
    if d.depth_m > 4500:
        out.append(Finding(
            "warning", "depth_high",
            f"At {inp.gradient_k_per_km:.0f} K/km the wells must be {d.depth_m / 1000:.1f} km "
            "deep: very expensive. Check whether your area has a higher gradient (a volcanic or "
            "tectonic anomaly) or a hot aquifer at a shallower depth.", "geo.wells"))
    elif d.depth_m < 600:
        out.append(Finding(
            "info", "depth_low",
            f"The wells are only {d.depth_m:,.0f} m deep: at this depth a ground-source heat "
            "pump with borehole heat exchangers is usually the better option.", "geo.wells"))
    if inp.gradient_k_per_km < 20 or inp.gradient_k_per_km > 60:
        out.append(Finding(
            "info", "gradient",
            f"A gradient of {inp.gradient_k_per_km:.0f} K/km is far from the normal 25-35: "
            "use a value measured near the site.", "geo.wells"))
    out.append(Finding(
        "info", "resource_risk",
        "Whether the reservoir really gives this flow at this temperature is known only after "
        "drilling: exploration and the failure of a well are the main risks and are not "
        "included in the costs.", "geo.economics"))
    if d.pathway == "heat":
        out += _check_heat(inp, d)
    else:
        out += _check_power(inp, d)
    out.append(Finding(
        "info", "annual_balance",
        "Constant flow and temperature for the whole life: thermal decline of the reservoir, "
        "scaling, corrosion and the hourly load are not modelled.", None))
    if not any(f.severity in ("warning", "error") for f in out):
        out.insert(0, Finding("ok", "design_ok", "No problem found with the main design rules.",
                              None))
    return out


def _check_heat(inp: GeothermalInputs, d: GeothermalDesign) -> list[Finding]:
    out: list[Finding] = []
    if inp.reservoir_temp_c < 50:
        out.append(Finding(
            "warning", "temp_low",
            f"Brine at {inp.reservoir_temp_c:.0f} degC is too cold for a network without a heat "
            "pump: the supply temperature would not reach the radiators.", "geo.heat_power"))
    if inp.return_temp_c > 60:
        out.append(Finding(
            "info", "return_high",
            f"A return temperature of {inp.return_temp_c:.0f} degC leaves much of the heat in the "
            "water: a low-temperature network (40-50 degC) takes far more from each well.",
            "geo.heat_power"))
    if d.full_load_hours < 2500:
        out.append(Finding(
            "warning", "full_load_hours",
            f"Only {d.full_load_hours:,.0f} full-load hours per year: the doublet is large "
            "for this load and the investment is hard to repay. Cover a smaller share.",
            "geo.coverage"))
    if d.coverage < inp.coverage - 0.05 or d.coverage > min(1.0, inp.coverage + 0.15):
        out.append(Finding(
            "info", "coverage_steps",
            f"Wells come in whole pairs, so the plant covers {d.coverage:.0%} of the heat "
            f"instead of the {inp.coverage:.0%} you asked for.", "geo.coverage"))
    if d.spf and d.spf < 15:
        out.append(Finding(
            "warning", "spf_low",
            f"The doublet gives {d.spf:.0f} units of heat per unit of pumping electricity: low "
            "for a good reservoir. Check the pressure rise and the flow per well.",
            "geo.pumping"))
    if d.lcoe > inp.heat_price_eur_per_kwh:
        out.append(Finding(
            "warning", "lcoe_high",
            f"The heat costs {d.lcoe:.3f} euro/kWh and the heat you replace {inp.heat_price_eur_per_kwh:.3f}: "
            "the plant does not pay for itself at these prices.", "geo.economics"))
    return out


def _check_power(inp: GeothermalInputs, d: GeothermalDesign) -> list[Finding]:
    out: list[Finding] = []
    t = inp.reservoir_temp_c
    if d.plant == "binary" and (t < 100 or t > 170):
        out.append(Finding(
            "warning", "binary_range",
            f"The binary efficiency fit is based on plants between 103 and 166 degC: at "
            f"{t:.0f} degC it is an extrapolation.", "geo.binary"))
    if d.plant == "flash" and t < FLASH_FROM_C:
        out.append(Finding(
            "warning", "flash_cold",
            f"A flash plant at {t:.0f} degC makes little steam: below about "
            f"{FLASH_FROM_C:.0f} degC a binary plant is the normal choice.", "geo.flash"))
    if d.plant == "binary" and t > 200:
        out.append(Finding(
            "info", "binary_hot",
            f"At {t:.0f} degC a flash plant would convert more of the heat than a binary one.",
            "geo.flash"))
    if t < 100:
        out.append(Finding(
            "warning", "temp_low",
            f"Brine at {t:.0f} degC gives very little electricity: heat is the better use "
            "of this resource.", "geo.exergy"))
    share = d.pumps_kw / d.gross_kw if d.gross_kw else 0.0
    if share > 0.20:
        out.append(Finding(
            "warning", "pump_share",
            f"The pumps use {share:.0%} of the gross power: the project is sensitive to the "
            "productivity of the wells.", "geo.net_power"))
    if inp.operating_hours < 7000:
        out.append(Finding(
            "info", "hours_low",
            f"{inp.operating_hours:,.0f} h per year is low for a geothermal plant, which runs "
            "as base load (7500 h or more).", "geo.net_power"))
    if d.coverage > 1.15:
        out.append(Finding(
            "info", "surplus",
            f"One pair of wells already gives {d.coverage:.0%} of the demand: the surplus is "
            "sold to the grid.", "geo.net_power"))
    if d.lcoe > inp.export_price:
        out.append(Finding(
            "warning", "lcoe_high",
            f"The electricity costs {d.lcoe:.3f} euro/kWh and the surplus is sold at "
            f"{inp.export_price:.3f}: it pays only for the share you use yourself.",
            "geo.economics"))
    return out
