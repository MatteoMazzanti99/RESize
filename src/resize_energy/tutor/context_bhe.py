"""Plain-text summary of a borehole-field project for the AI tutor."""

from __future__ import annotations

from resize_energy.core.bhe_design import BheDesign, BheInputs
from resize_energy.tutor.checker import Finding

_SEVERITY = {"error": "ERROR", "warning": "WARNING", "info": "NOTE", "ok": "OK"}


def build_bhe_context(inp: BheInputs, d: BheDesign, findings: list[Finding]) -> str:
    lines = ["PROJECT: ground-source heat pump, vertical borehole heat exchangers, ASHRAE length "
             "method (preliminary sizing made with RESize)", "", "INPUTS",
             f"- Heating {inp.heating_kwh_per_year:,.0f} kWh/year, peak {inp.heating_peak_kw:,.0f} kW, "
             f"COP {inp.cop_design} (seasonal {inp.cop_seasonal})",
             f"- Cooling {inp.cooling_kwh_per_year:,.0f} kWh/year, peak {inp.cooling_peak_kw:,.0f} kW, "
             f"EER {inp.eer_design} (seasonal {inp.eer_seasonal})",
             f"- Ground {inp.ground_temp_c} degC, lambda {inp.ground_conductivity} W/mK, "
             f"alpha from rho {inp.ground_density:,.0f} and cp {inp.ground_cp:,.0f}",
             f"- Spacing {inp.spacing_m} m, maximum depth {inp.max_depth_m:,.0f} m, penalty "
             f"method {inp.penalty_method}", "", "RESULTS",
             f"- L heating {d.length_heating_m:,.0f} m, L cooling {d.length_cooling_m:,.0f} m: "
             f"{d.governing} governs; total {d.total_length_m:,.0f} m",
             f"- {d.boreholes} boreholes of {d.depth_m:,.0f} m ({d.rows} x {d.columns}), area "
             f"{d.area_needed_m2:,.0f} m2; temperature penalty {d.penalty_c:+.2f} K",
             f"- R_b {d.r_b:.3f}, Re {d.reynolds:,.0f}, net yearly load on the ground "
             f"{d.q_annual_w / 1000:+.1f} kW; {d.peak_w_per_m:.0f} W per metre at the peak",
             f"- CAPEX {d.capex:,.0f} euro", "", "DESIGN CHECKS"]
    lines += [f"- [{_SEVERITY[f.severity]}] {f.message}" for f in findings] or ["- (none)"]
    return "\n".join(lines)
