"""Plain-text summary of a battery project for the AI tutor."""

from __future__ import annotations

from resize_energy.core.battery_design import BatteryDesign, BatteryInputs
from resize_energy.tutor.checker import Finding

_SEVERITY = {"error": "ERROR", "warning": "WARNING", "info": "NOTE", "ok": "OK"}


def build_battery_context(inp: BatteryInputs, d: BatteryDesign,
                          findings: list[Finding]) -> str:
    plant = [f"PV {inp.pv_kwp:g} kWp" if inp.use_pv else "", f"wind {inp.wind_kw:g} kW"
             if inp.use_wind else ""]
    lines = [
        "PROJECT: battery storage for self-consumption (preliminary sizing made with RESize)",
        "",
        "INPUTS",
        f"- Plant: {', '.join(p for p in plant if p)}; load {inp.load_kind}, "
        f"{inp.annual_demand_kwh:,.0f} kWh/year; profile: {d.profile_source}",
        f"- Mode {inp.mode}; round-trip {inp.eta_roundtrip:.0%}; depth of discharge "
        f"{inp.usable_fraction:.0%}; C-rate {inp.c_rate}",
        f"- Prices: buy {inp.retail_price} euro/kWh, sell {inp.export_price} euro/kWh; battery "
        f"{inp.capex_per_kwh:g} euro/kWh + {inp.capex_per_kw:g} euro/kW",
        "",
        "RESULTS",
        f"- Battery {d.capacity_kwh:.1f} kWh ({d.usable_kwh:.1f} usable), {d.power_kw:.1f} kW",
        f"- Self-sufficiency {d.self_sufficiency_without:.0%} -> {d.self_sufficiency:.0%}; "
        f"self-consumption {d.self_consumption_without:.0%} -> {d.self_consumption:.0%}",
        f"- {d.cycles_per_year:.0f} cycles/year, life {d.life_years:.1f} years ({d.life_limit})",
        f"- CAPEX {d.capex:,.0f} euro; savings {d.savings_per_year:,.0f} euro/year; payback "
        f"{d.payback_years:.1f} years; NPV {d.npv:,.0f} euro; LCOS {d.lcos:.3f} euro/kWh",
        "",
        "DESIGN CHECKS",
    ]
    lines += [f"- [{_SEVERITY[f.severity]}] {f.message}" for f in findings] or ["- (none)"]
    return "\n".join(lines)
