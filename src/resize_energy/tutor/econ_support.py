"""Worked examples, checks and context lines of the cost step (shared by PV and wind)."""

from __future__ import annotations

from resize_energy.core.plant_economics import EconomicInputs, Economics
from resize_energy.tutor.checker import Finding


def worked_economics(key: str, e: EconomicInputs | None, econ: Economics | None,
                     power_kw: float, demand_kwh: float) -> str | None:
    """The user's numbers in the cost formulas; None if the key is not an economics key."""
    if key.endswith(".economics"):
        if e is None or econ is None:
            return "The cost step was not filled in: CAPEX 0 euro, no economic result."
        return (
            f"CAPEX = {power_kw:,.1f} kW x {e.capex_per_kw:,.0f} euro/kW = {econ.capex:,.0f} euro; "
            f"O&M = {power_kw:,.1f} x {e.om_per_kw_year:,.0f} = {econ.om_per_year:,.0f} euro/year\n"
            f"Savings = {econ.self_used_kwh:,.0f} kWh x {e.retail_price:.3f} + "
            f"{econ.exported_kwh:,.0f} kWh x {e.export_price:.3f} = "
            f"{econ.savings_per_year:,.0f} euro/year -> net {econ.net_benefit_per_year:,.0f} euro/year\n"
            f"LCOE = {econ.lcoe:.3f} euro/kWh against {e.retail_price:.3f} euro/kWh paid to the grid\n"
            f"Payback = {econ.payback_years:.1f} years; NPV at {e.discount_rate:.1%} over "
            f"{e.life_years:g} years = {econ.npv:,.0f} euro\n"
            f"CO2 avoided = {econ.energy_kwh:,.0f} kWh x ({e.grid_ef:.2f} - "
            f"{e.lifecycle_g_per_kwh / 1000:.3f}) kg/kWh = {econ.co2_avoided_t_per_year:.2f} t/year"
        )
    if key.endswith(".sensitivity"):
        if econ is None or econ.sensitivity is None:
            if econ is None:
                return "No economic result, so no sensitivity: base NPV 0 euro (cost step not filled)."
            return f"No sensitivity available; base NPV {econ.npv:,.0f} euro."
        curves = sorted(econ.sensitivity.curves, key=lambda c: -c.swing)
        top = curves[0]
        lines = [f"Base NPV {econ.npv:,.0f} euro. Swing of the NPV for -20 % / +20 %:"]
        lines += [f"- {c.label}: {c.swing:,.0f} euro" for c in curves[:4]]
        lines.append(f"The result depends most on: {top.label.lower()}.")
        return "\n".join(lines)
    return None


def check_economics(prefix: str, e: EconomicInputs | None, econ: Economics | None) -> list[Finding]:
    """Findings on the economics; empty when the cost step was not filled in."""
    if e is None or econ is None:
        return []
    key = f"{prefix}.economics"
    out: list[Finding] = []
    if econ.lcoe >= e.retail_price:
        out.append(Finding(
            "warning", "lcoe_above_retail",
            f"The energy costs {econ.lcoe:.3f} euro/kWh to make, more than the "
            f"{e.retail_price:.3f} euro/kWh you pay the grid: on these numbers the plant does "
            "not pay back.", key))
    elif econ.npv < 0:
        out.append(Finding(
            "warning", "npv_negative",
            f"The net present value is {econ.npv:,.0f} euro: part of the energy is sold at the "
            "low export price, or the plant does not repay the investment within its life.", key))
    elif econ.payback_years > 0.8 * e.life_years:
        out.append(Finding(
            "warning", "payback_long",
            f"Payback of {econ.payback_years:.1f} years is close to the {e.life_years:g}-year "
            "life: small changes in prices or yield would erase the gain.", key))
    else:
        out.append(Finding(
            "ok", "economics",
            f"Payback {econ.payback_years:.1f} years, NPV {econ.npv:,.0f} euro, "
            f"LCOE {econ.lcoe:.3f} euro/kWh.", key))
    if econ.exported_kwh > 0.5 * econ.energy_kwh:
        out.append(Finding(
            "info", "export_dominates",
            f"{econ.exported_kwh / econ.energy_kwh:.0%} of the energy is exported at "
            f"{e.export_price:.2f} euro/kWh, well below the retail price: a smaller plant or a "
            "battery may pay better.", key))
    sens = econ.sensitivity
    if sens is not None and econ.npv > 0:
        flips = [c.label for c in sens.curves if min(c.values) < 0]
        if flips:
            out.append(Finding(
                "info", "npv_fragile",
                f"The NPV turns negative if {flips[0].lower()} moves by 20 %: check that number "
                "first.", f"{prefix}.sensitivity"))
    return out


def context_lines(e: EconomicInputs | None, econ: Economics | None) -> list[str]:
    if e is None or econ is None:
        return []
    return [
        "",
        "COSTS AND SAVINGS",
        f"- CAPEX {econ.capex:,.0f} euro ({e.capex_per_kw:,.0f} euro/kW), O&M "
        f"{econ.om_per_year:,.0f} euro/year, life {e.life_years:g} years, discount rate "
        f"{e.discount_rate:.1%}",
        f"- Prices: retail {e.retail_price:.3f}, export {e.export_price:.3f} euro/kWh",
        f"- LCOE {econ.lcoe:.3f} euro/kWh; savings {econ.savings_per_year:,.0f} euro/year; "
        f"payback {econ.payback_years:.1f} years; NPV {econ.npv:,.0f} euro; "
        f"CO2 avoided {econ.co2_avoided_t_per_year:.2f} t/year",
    ]
