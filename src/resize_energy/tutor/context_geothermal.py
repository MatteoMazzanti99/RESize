"""Plain-text summary of a geothermal project for the AI tutor."""

from __future__ import annotations

from resize_energy.core.geothermal_design import PATHWAYS, GeothermalDesign, GeothermalInputs
from resize_energy.tutor.checker import Finding

_SEVERITY = {"error": "ERROR", "warning": "WARNING", "info": "NOTE", "ok": "OK"}


def build_geothermal_context(inp: GeothermalInputs, d: GeothermalDesign,
                             findings: list[Finding]) -> str:
    lines = [f"PROJECT: geothermal, {PATHWAYS[inp.pathway]} (preliminary sizing made with RESize)",
             "", "INPUTS",
             f"- Reservoir {inp.reservoir_temp_c:.0f} degC, {inp.flow_per_well_kg_s:.0f} kg/s per "
             f"well, gradient {inp.gradient_k_per_km:.0f} K/km, ambient {inp.ambient_temp_c:.0f} degC",
             f"- Pumps: {inp.pump_pressure_bar:.0f} bar, efficiency {inp.pump_efficiency:.2f}"]
    if d.pathway == "heat":
        lines += [
            f"- Heat demand {inp.annual_heat_demand_kwh:,.0f} kWh/year, peak {inp.peak_heat_kw:,.0f} "
            f"kW, coverage {inp.coverage:.0%}; return {inp.return_temp_c:.0f} degC",
            "", "RESULTS",
            f"- {d.wells_pairs} pair(s) of wells {d.depth_m:,.0f} m deep, {d.heat_per_pair_kw:,.0f} "
            f"kW of heat each ({d.power_ratio:.0%} of the peak)",
            f"- Heat {d.heat_kwh:,.0f} kWh/year ({d.coverage:.0%} of the demand), "
            f"{d.full_load_hours:,.0f} full-load hours, SPF {d.spf:.0f}",
        ]
    else:
        lines += [
            f"- Electricity demand {inp.annual_electricity_demand_kwh:,.0f} kWh/year, coverage "
            f"{inp.coverage:.0%}; {inp.operating_hours:,.0f} h per year; reinjection "
            f"{inp.reinjection_temp_c:.0f} degC",
            "", "RESULTS",
            f"- {d.plant} plant, {d.wells_pairs} pair(s) of wells {d.depth_m:,.0f} m deep; efficiency "
            f"{d.efficiency:.1%}",
            f"- Gross {d.gross_kw:,.0f} kW, pumps {d.pumps_kw:,.0f} kW, net {d.net_kw:,.0f} kW; "
            f"{d.electricity_kwh:,.0f} kWh/year ({d.coverage:.0%} of the demand)",
        ]
    lines += [f"- CAPEX {d.capex:,.0f} euro, cost {d.lcoe:.3f} euro/kWh, NPV {d.npv:,.0f} euro; "
              f"CO2 avoided {d.co2_avoided_t_per_year:,.0f} t/year", "", "DESIGN CHECKS"]
    lines += [f"- [{_SEVERITY[f.severity]}] {f.message}" for f in findings] or ["- (none)"]
    return "\n".join(lines)
