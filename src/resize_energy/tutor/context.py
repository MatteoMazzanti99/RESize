"""Plain-text summary of a PV project, given to the AI tutor (or copied into any chatbot)."""

from __future__ import annotations

from resize_energy.core.pv_design import PVDesign, PVInputs
from resize_energy.tutor.checker import Finding

_SEVERITY = {"error": "ERROR", "warning": "WARNING", "info": "NOTE", "ok": "OK"}


def build_project_context(inp: PVInputs, design: PVDesign, findings: list[Finding]) -> str:
    """Inputs, results and design checks of the current project, as readable text."""
    m, inv = inp.module, inp.inverter
    lines = [
        "PROJECT: grid-connected photovoltaic plant, preliminary sizing made with RESize",
        "",
        "INPUTS",
        f"- Annual electricity demand: {inp.annual_demand_kwh:,.0f} kWh",
        f"- Share of demand to cover with PV: {inp.coverage:.0%}",
        f"- Annual in-plane irradiation H: {inp.annual_irradiation_kwh_m2:,.0f} kWh/m2",
        f"- Performance ratio PR: {inp.performance_ratio:.2f}",
        f"- Minimum ambient temperature: {inp.t_min_c:.0f} degC; "
        f"maximum cell temperature: {inp.t_cell_max_c:.0f} degC",
        f"- Module: {m.p_stc_w:.0f} Wp, Voc {m.voc_v:.2f} V, Vmp {m.vmp_v:.2f} V, "
        f"Isc {m.isc_a:.2f} A, temp. coefficients Voc {m.temp_coeff_voc_pct_per_c:.2f} "
        f"and Vmp {m.temp_coeff_vmp_pct_per_c:.2f} %/degC, area {m.area_m2:.2f} m2",
        f"- Inverter: {inv.p_ac_kw:.1f} kW AC, max DC voltage {inv.vdc_max_v:.0f} V, "
        f"MPPT window {inv.mppt_vmin_v:.0f}-{inv.mppt_vmax_v:.0f} V, "
        f"{inv.n_mppt} MPPT inputs of {inv.imax_per_mppt_a:.1f} A each",
        "",
        "RESULTS",
        f"- Target peak power: {design.target_kwp:.2f} kWp ({design.modules_target} modules)",
        f"- Admissible modules per string: {design.n_series_min} to {design.n_series_max}"
        + ("" if design.feasible else " (NO VALID STRING LENGTH)"),
        f"- Chosen layout: {design.n_series} in series x {design.n_parallel} in parallel "
        f"= {design.n_modules} modules",
        f"- Installed DC power: {design.dc_power_kwp:.2f} kWp; "
        f"DC/AC ratio {design.dc_ac_ratio:.2f}",
        f"- String Voc at minimum temperature: {design.voc_cold_string_v:.0f} V; "
        f"Vmp at maximum cell temperature: {design.vmp_hot_string_v:.0f} V",
        f"- Expected annual energy: {design.annual_energy_kwh:,.0f} kWh "
        f"({design.specific_yield_kwh_per_kwp:,.0f} kWh/kWp), "
        f"covering {design.achieved_coverage:.0%} of the demand",
        f"- Array area: {design.array_area_m2:.1f} m2",
        "",
        "DESIGN CHECKS",
    ]
    lines += [f"- [{_SEVERITY[f.severity]}] {f.message}" for f in findings] or ["- (none)"]
    return "\n".join(lines)
