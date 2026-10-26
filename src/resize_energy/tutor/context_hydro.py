"""Plain-text summary of a hydropower project for the AI tutor."""

from __future__ import annotations

from resize_energy.core.hydro_design import HydroDesign, HydroInputs
from resize_energy.tutor.checker import Finding

_SEVERITY = {"error": "ERROR", "warning": "WARNING", "info": "NOTE", "ok": "OK"}


def build_hydro_context(inp: HydroInputs, d: HydroDesign, findings: list[Finding]) -> str:
    lines = [
        "PROJECT: run-of-river hydropower (preliminary sizing made with RESize)", "", "INPUTS",
        f"- Gross head {inp.gross_head_m:.1f} m; mean flow {inp.mean_flow_m3s:.2f} m3/s, Q95 "
        f"{inp.q95_m3s:.2f} m3/s; environmental flow {inp.eco_flow_m3s:.2f} m3/s",
        f"- Design flow exceeded {inp.design_exceedance:.0%} of the time; penstock "
        f"{inp.penstock_length_m:.0f} m long, roughness {inp.roughness_mm:.2f} mm, K "
        f"{inp.local_loss_k:.1f}",
        f"- Costs: {inp.capex_per_kw:,.0f} euro/kW, O&M {inp.om_fraction:.1%}, life "
        f"{inp.life_years:.0f} years, discount rate {inp.discount_rate:.1%}",
        "", "RESULTS",
        f"- Design flow {d.design_flow_m3s:.2f} m3/s, net head {d.net_head_m:.1f} m (loss "
        f"{d.head_loss_m:.2f} m), penstock {d.penstock_diameter_m:.2f} m at {d.velocity_ms:.1f} m/s",
        f"- {d.turbine_name}, efficiency {d.turbine_eff:.2f}, generator {d.generator_eff:.3f}; "
        f"rated power {d.rated_kw:,.0f} kW",
        f"- Energy {d.energy_kwh:,.0f} kWh/year, capacity factor {d.capacity_factor:.0%}, "
        f"{d.hours_working:,.0f} h at work; {d.water_used_fraction:.0%} of the river used",
        f"- CAPEX {d.capex:,.0f} euro, LCOE {d.lcoe:.3f} euro/kWh, NPV {d.npv:,.0f} euro; "
        f"CO2 avoided {d.co2_avoided_t_per_year:,.0f} t/year",
        "", "DESIGN CHECKS",
    ]
    lines += [f"- [{_SEVERITY[f.severity]}] {f.message}" for f in findings] or ["- (none)"]
    return "\n".join(lines)
