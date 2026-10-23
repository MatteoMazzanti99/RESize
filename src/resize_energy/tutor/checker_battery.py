"""Sanity checks of a battery design."""

from __future__ import annotations

from resize_energy.core.battery_design import BatteryDesign, BatteryInputs
from resize_energy.tutor.checker import Finding


def check_battery_design(inp: BatteryInputs, d: BatteryDesign) -> list[Finding]:
    out: list[Finding] = []
    if d.capacity_kwh <= 0:
        out.append(Finding("info", "no_battery",
                           "Capacity 0: this is the case without a battery.", "battery.capacity"))
        return out
    if d.npv < 0:
        margin = inp.retail_price - inp.export_price
        out.append(Finding(
            "warning", "npv_negative",
            f"The net present value is {d.npv:,.0f} euro: with the margin of {margin:.2f} "
            f"euro/kWh between buying and selling and a battery cost of "
            f"{inp.capex_per_kwh:,.0f} euro/kWh, it does not pay back over its life. It can still "
            "be worth it for independence or backup.", "battery.economics"))
    if d.payback_years > d.life_years:
        out.append(Finding(
            "warning", "payback_beyond_life",
            f"Payback {d.payback_years:.0f} years is longer than the battery life of "
            f"{d.life_years:.0f} years.", "battery.life"))
    if d.cycles_per_year < 100:
        out.append(Finding(
            "warning", "few_cycles",
            f"Only {d.cycles_per_year:.0f} cycles a year: the battery is too big for this "
            "plant and load, much of it is rarely filled.", "battery.diminishing"))
    elif d.cycles_per_year > 400:
        out.append(Finding(
            "info", "many_cycles",
            f"{d.cycles_per_year:.0f} cycles a year is a heavy use: check the cycle life.",
            "battery.life"))
    if d.life_limit == "cycles":
        out.append(Finding(
            "info", "cycle_limited",
            f"The cycles, not the calendar, limit the life to {d.life_years:.1f} years.",
            "battery.life"))
    gain = d.self_sufficiency - d.self_sufficiency_without
    if gain < 0.05:
        out.append(Finding(
            "warning", "small_gain",
            f"The battery raises self-sufficiency by only {gain:.0%}: the plant leaves little "
            "surplus to store or the load already uses the production.", "battery.selfuse"))
    if d.generation_kwh < 0.5 * d.load_kwh:
        out.append(Finding(
            "info", "small_plant",
            "The plant produces less than half of the load: there is little surplus, a battery "
            "will not help much.", "battery.dispatch"))
    if d.profile_source == "synthetic":
        out.append(Finding(
            "warning", "synthetic_profile",
            "The production profile is synthetic (invented, not measured) and the load is a "
            "typical shape: results are indicative.", "battery.load"))
    if not any(f.severity in ("warning", "error") for f in out):
        out.insert(0, Finding("ok", "design_ok", "No problem found with the main design rules.",
                              None))
    return out
