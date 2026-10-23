"""Plain-text summary of a wind project for the AI tutor (or any chatbot)."""

from __future__ import annotations

from resize_energy.core.wind_design import WindDesign, WindInputs
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.econ_support import context_lines

_SEVERITY = {"error": "ERROR", "warning": "WARNING", "info": "NOTE", "ok": "OK"}


def build_wind_context(inp: WindInputs, d: WindDesign, findings: list[Finding]) -> str:
    t = inp.turbine
    lines = [
        "PROJECT: onshore wind plant, preliminary sizing made with RESize",
        "",
        "INPUTS",
        f"- Annual electricity demand: {inp.annual_demand_kwh:,.0f} kWh; "
        f"share to cover with wind: {inp.coverage:.0%}",
        f"- Mean wind speed {inp.mean_speed_ref_ms:.2f} m/s at {inp.ref_height_m:.0f} m; "
        f"Weibull k = {inp.weibull_k:.2f}; shear exponent {inp.shear_alpha:.2f}",
        f"- Site: elevation {inp.elevation_m:.0f} m, mean temperature {inp.temperature_c:.0f} degC",
        f"- Turbine: {t.rated_power_kw:,.0f} kW, rotor {t.rotor_diameter_m:.0f} m, hub "
        f"{t.hub_height_m:.0f} m, cut-in {t.cut_in_ms:.1f}, rated {t.rated_speed_ms:.1f}, "
        f"cut-out {t.cut_out_ms:.1f} m/s",
        "- Power curve: " + (f"tabulated, {len(t.power_curve)} points, source {t.curve_source}"
                            if t.power_curve else "generic (cubic between cut-in and rated)"),
        f"- Availability {inp.availability:.0%}; other losses {inp.other_losses:.0%}; spacing "
        f"{inp.crosswind_spacing_d:.0f} D x {inp.downwind_spacing_d:.0f} D",
        "",
        "RESULTS",
        f"- Mean speed at hub height: {d.mean_speed_hub_ms:.2f} m/s (Weibull scale "
        f"{d.weibull_scale_ms:.2f} m/s); air density {d.air_density:.3f} kg/m3",
        f"- Rotor swept area {d.swept_area_m2:,.0f} m2; specific power "
        f"{d.specific_power_w_m2:.0f} W/m2; Cp at rated {d.cp_rated:.2f}",
        f"- Energy per turbine: gross {d.gross_energy_per_turbine_kwh:,.0f} kWh, net "
        f"{d.net_energy_per_turbine_kwh:,.0f} kWh; net capacity factor "
        f"{d.capacity_factor_net:.1%} ({d.full_load_hours_net:,.0f} full-load hours)",
        f"- Turbines: {d.n_turbines} ({d.installed_power_kw:,.0f} kW installed), "
        f"{d.annual_energy_kwh:,.0f} kWh/year = {d.achieved_coverage:.0%} of the demand",
        f"- Land for the array: {d.array_area_km2:.2f} km2; tip clearance "
        f"{d.tip_clearance_m:.0f} m",
        "",
        "DESIGN CHECKS",
    ]
    lines += [f"- [{_SEVERITY[f.severity]}] {f.message}" for f in findings] or ["- (none)"]
    lines += context_lines(inp.economics, d.economics)
    return "\n".join(lines)
