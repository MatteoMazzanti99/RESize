"""Sanity checks of a solar thermal design."""

from __future__ import annotations

from resize_energy.core.solar_thermal_design import SolarThermalDesign, SolarThermalInputs
from resize_energy.tutor.checker import Finding


def check_solar_design(inp: SolarThermalInputs, d: SolarThermalDesign) -> list[Finding]:
    out: list[Finding] = []
    r = d.run
    f = r.solar_fraction
    heat_only = inp.cooling_kwh_per_year <= 0

    if not d.target_reached:
        out.append(Finding(
            "warning", "target_unreachable",
            f"A solar fraction of {inp.target_fraction:.0%} could not be reached even with "
            f"{d.area_m2:g} m2: the winter sun is too weak. Aim lower or accept a backup.",
            "solar.area"))
    potential = r.collector_kwh + r.wasted_kwh
    waste = r.wasted_kwh / potential if potential > 0 else 0.0
    if waste > 0.20 or r.hours_stagnation > 400:
        out.append(Finding(
            "warning", "stagnation",
            f"The tank reaches 95 degC for {r.hours_stagnation} hours and {waste:.0%} of the "
            "possible heat is thrown away: the collector field is too big for the load. Reduce "
            "the area, enlarge the tank or find a summer use for the heat.", "solar.stagnation"))
    elif r.hours_stagnation > 0:
        out.append(Finding(
            "info", "stagnation_some",
            f"The tank touches 95 degC in {r.hours_stagnation} hours of the year: check that the "
            "collectors and the glycol are rated for stagnation.", "solar.stagnation"))
    if heat_only:
        if f > 0.85:
            out.append(Finding(
                "warning", "fraction_too_high",
                f"A solar fraction of {f:.0%} means much of the summer heat is wasted: the "
                "extra area adds little in winter. A fraction of 50-70 % is usual.",
                "solar.area"))
        elif f < 0.25:
            out.append(Finding(
                "info", "fraction_low",
                f"Only {f:.0%} of the demand is solar: the plant is small for the load or the "
                "sun is weak.", "solar.solar_fraction"))
        if inp.t_use_c > 65 and inp.collector == "flat":
            out.append(Finding(
                "info", "collector_temperature",
                f"At {inp.t_use_c:.0f} degC the flat plate loses much of its efficiency: "
                "evacuated tubes may be better.", "solar.collector"))
    ratio = inp.store_l_per_m2
    if not 35 <= ratio <= 110:
        out.append(Finding(
            "warning", "store_ratio",
            f"{ratio:g} litres per m2 of collector is outside the usual 40-100: a small tank "
            "overheats, a large one loses heat and costs money.", "solar.store"))
    if inp.cooling_kwh_per_year > 0:
        if r.cooling_fraction < 0.25:
            out.append(Finding(
                "warning", "cooling_low",
                f"The sun covers only {r.cooling_fraction:.0%} of the cooling: the tank is "
                "often below the minimum drive temperature or the chiller is small. Use "
                "evacuated tubes, a smaller store per m2 or a bigger field.", "solar.chiller_cop"))
        if r.hours_below_drive > 500:
            out.append(Finding(
                "info", "cold_tank",
                f"In {r.hours_below_drive} hours the cooling was needed but the tank was below "
                f"{inp.t_drive_min_c:.0f} degC; a conventional chiller must cover them.",
                "solar.chiller_cop"))
        best = max(d.cooling_options, key=lambda o: o.cooling_fraction, default=None)
        main = next((o for o in d.cooling_options if o.is_main), None)
        if best and main and not best.is_main and best.cooling_fraction > main.cooling_fraction + 0.05:
            out.append(Finding(
                "info", "better_cooling",
                f"On the same collectors, {best.name.lower()} covers {best.cooling_fraction:.0%} "
                f"of the cooling against {main.cooling_fraction:.0%} of the main technology: "
                "see the comparison.", "solar.chillers"))
        if inp.collector == "unglazed":
            out.append(Finding(
                "error", "unglazed_cooling",
                "Unglazed collectors cannot reach the drive temperature of a chiller.",
                "solar.collector"))
    if d.npv < 0:
        out.append(Finding(
            "warning", "npv_negative",
            f"The net present value is {d.npv:,.0f} euro and the heat costs "
            f"{d.lcoh:.3f} euro/kWh against {inp.heat_price:.3f} you pay now: without "
            "incentives it does not repay itself on these prices. Check the sensitivity.",
            "solar.economics"))
    elif d.payback_years > 0.8 * inp.life_years:
        out.append(Finding(
            "warning", "payback_long",
            f"Payback of {d.payback_years:.1f} years is close to the {inp.life_years:g}-year "
            "life of the plant.", "solar.economics"))
    if not any(x.severity in ("warning", "error") for x in out):
        out.append(Finding(
            "ok", "plausible",
            f"Solar fraction {f:.0%}, payback {d.payback_years:.1f} years: plausible.",
            "solar.solar_fraction"))
    return out
