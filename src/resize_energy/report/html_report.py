"""Self-contained HTML report of a PV design (the GUI turns it into a PDF)."""

from __future__ import annotations

from html import escape

from resize_energy import __version__
from resize_energy.core.pv_design import PVDesign, PVInputs
from resize_energy.core.wind_design import WindDesign, WindInputs
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.explanations import EXPLANATIONS, TOPIC_ORDER
from resize_energy.tutor.explanations_wind import WIND_TOPIC_ORDER
from resize_energy.tutor.why_html import explanation_html
from resize_energy.tutor.worked import worked_example
from resize_energy.tutor.worked_wind import wind_worked_example

_LABELS = {"error": "ERROR", "warning": "WARNING", "info": "NOTE", "ok": "OK"}

# Two looks for the same report: "light" for the PDF (white paper), "dark" for the window.
_THEMES = {
    "light": {
        "colors": {"error": "#b3261e", "warning": "#b26a00", "info": "#1a5fb4", "ok": "#2e7d32"},
        "css": (
            "body { font-family: Arial, sans-serif; font-size: 10pt; }\n"
            "h1 { font-size: 18pt; } h2 { font-size: 13pt; margin-top: 16px; }\n"
            "h3 { font-size: 10.5pt; margin-bottom: 2px; }\n"
            "table { border-collapse: collapse; } td { padding: 2px 10px 2px 0; }\n"
            "code { background: #eee; }"
        ),
    },
    "dark": {
        "colors": {"error": "#FF7A7A", "warning": "#F5B941", "info": "#6CB4FF", "ok": "#4ADE80"},
        "css": (
            "body { color: #E8EEF8; font-size: 10pt; }\n"
            "h1 { font-size: 17pt; color: #E8EEF8; }\n"
            "h2 { font-size: 13pt; margin-top: 16px; color: #2DE08A; }\n"
            "h3 { font-size: 10.5pt; margin-bottom: 2px; color: #2DE08A; }\n"
            "table { border-collapse: collapse; } td { padding: 2px 10px 2px 0; }\n"
            "code { background-color: #1A2540; color: #9CF3C6; }"
        ),
    },
}


def _row(label: str, value: str) -> str:
    return f"<tr><td>{escape(label)}</td><td><b>{escape(value)}</b></td></tr>"


def build_pv_report(
    inp: PVInputs,
    design: PVDesign,
    findings: list[Finding],
    title: str = "Preliminary PV sizing report",
    site_note: str = "",
    theme: str = "light",
) -> str:
    """HTML string with inputs, results, checks and the formulas used.

    ``theme`` is "light" (for the PDF) or "dark" (for showing it inside the dark window).
    """
    look = _THEMES.get(theme, _THEMES["light"])
    colors = look["colors"]
    m, inv = inp.module, inp.inverter

    inputs_rows = "".join([
        _row("Annual electricity demand", f"{inp.annual_demand_kwh:,.0f} kWh"),
        _row("Target PV coverage", f"{inp.coverage:.0%}"),
        _row("Annual in-plane irradiation", f"{inp.annual_irradiation_kwh_m2:,.0f} kWh/m2"),
        _row("Performance ratio", f"{inp.performance_ratio:.2f}"),
        _row("Minimum ambient temperature", f"{inp.t_min_c:.0f} degC"),
        _row("Maximum cell temperature", f"{inp.t_cell_max_c:.0f} degC"),
        _row("Module", f"{m.name} ({m.p_stc_w:.0f} Wp)"),
        _row("Module Voc / Vmp / Isc", f"{m.voc_v:.1f} V / {m.vmp_v:.1f} V / {m.isc_a:.1f} A"),
        _row("Voc / Vmp temp. coefficients",
             f"{m.temp_coeff_voc_pct_per_c:.2f} / {m.temp_coeff_vmp_pct_per_c:.2f} %/degC"),
        _row("Inverter", f"{inv.name} ({inv.p_ac_kw:.1f} kW AC)"),
        _row("Inverter Vdc,max / MPPT window",
             f"{inv.vdc_max_v:.0f} V / {inv.mppt_vmin_v:.0f}-{inv.mppt_vmax_v:.0f} V"),
        _row("Inverter MPPT inputs / current each", f"{inv.n_mppt} / {inv.imax_per_mppt_a:.1f} A"),
    ])

    results_rows = "".join([
        _row("Target peak power", f"{design.target_kwp:.2f} kWp"),
        _row("Admissible modules per string",
             f"{design.n_series_min} to {design.n_series_max}"),
        _row("Chosen layout", f"{design.n_series} in series x {design.n_parallel} in parallel"),
        _row("Total modules", f"{design.n_modules}"),
        _row("Installed DC power", f"{design.dc_power_kwp:.2f} kWp"),
        _row("DC/AC ratio", f"{design.dc_ac_ratio:.2f}"),
        _row("Array area", f"{design.array_area_m2:.1f} m2"),
        _row("String Voc at minimum temperature", f"{design.voc_cold_string_v:.0f} V"),
        _row("String Vmp at maximum cell temperature", f"{design.vmp_hot_string_v:.0f} V"),
        _row("Expected annual energy", f"{design.annual_energy_kwh:,.0f} kWh"),
        _row("Specific yield", f"{design.specific_yield_kwh_per_kwp:,.0f} kWh/kWp"),
        _row("Demand covered", f"{design.achieved_coverage:.0%}"),
    ])

    checks = "".join(
        f'<li><span style="color:{colors[f.severity]}"><b>[{_LABELS[f.severity]}]</b></span> '
        f"{escape(f.message)}</li>"
        for f in findings
    )

    why = "".join(
        explanation_html(key, worked_example(key, inp, design))
        for key in TOPIC_ORDER
        if key in EXPLANATIONS
    )

    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>1. Inputs</h2><table>{inputs_rows}</table>
<h2>2. Results</h2><table>{results_rows}</table>
<h2>3. Design checks</h2><ul>{checks}</ul>
<h2>4. Method and formulas</h2>{why}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational sizing only:
not a substitute for detailed engineering design (see DISCLAIMER).</i></p>
</body></html>"""


def build_wind_report(
    inp: WindInputs,
    design: WindDesign,
    findings: list[Finding],
    title: str = "Preliminary wind sizing report",
    site_note: str = "",
    theme: str = "light",
) -> str:
    """HTML string with inputs, results, checks and the formulas of a wind design."""
    look = _THEMES.get(theme, _THEMES["light"])
    colors = look["colors"]
    t = inp.turbine

    inputs_rows = "".join([
        _row("Annual electricity demand", f"{inp.annual_demand_kwh:,.0f} kWh"),
        _row("Target wind coverage", f"{inp.coverage:.0%}"),
        _row("Mean wind speed (reference)",
             f"{inp.mean_speed_ref_ms:.2f} m/s at {inp.ref_height_m:.0f} m"),
        _row("Weibull shape k / shear exponent", f"{inp.weibull_k:.2f} / {inp.shear_alpha:.2f}"),
        _row("Elevation / mean temperature",
             f"{inp.elevation_m:.0f} m / {inp.temperature_c:.0f} degC"),
        _row("Turbine", f"{t.name} ({t.rated_power_kw:,.0f} kW)"),
        _row("Rotor diameter / hub height", f"{t.rotor_diameter_m:.0f} m / {t.hub_height_m:.0f} m"),
        _row("Cut-in / rated / cut-out speed",
             f"{t.cut_in_ms:.1f} / {t.rated_speed_ms:.1f} / {t.cut_out_ms:.1f} m/s"),
        _row("Power curve",
             f"tabulated, {len(t.power_curve)} points ({t.curve_source})" if t.power_curve
             else "generic (cubic between cut-in and rated)"),
        _row("Availability / other losses", f"{inp.availability:.0%} / {inp.other_losses:.0%}"),
        _row("Spacing (across x along the wind)",
             f"{inp.crosswind_spacing_d:.0f} D x {inp.downwind_spacing_d:.0f} D"),
    ])
    results_rows = "".join([
        _row("Mean speed at hub height", f"{design.mean_speed_hub_ms:.2f} m/s"),
        _row("Weibull scale A", f"{design.weibull_scale_ms:.2f} m/s"),
        _row("Air density", f"{design.air_density:.3f} kg/m3"),
        _row("Swept area / specific power",
             f"{design.swept_area_m2:,.0f} m2 / {design.specific_power_w_m2:.0f} W/m2"),
        _row("Cp at rated speed", f"{design.cp_rated:.2f}"),
        _row("Energy per turbine (gross / net)",
             f"{design.gross_energy_per_turbine_kwh:,.0f} / "
             f"{design.net_energy_per_turbine_kwh:,.0f} kWh"),
        _row("Capacity factor (net)", f"{design.capacity_factor_net:.1%}"),
        _row("Full-load hours (net)", f"{design.full_load_hours_net:,.0f} h"),
        _row("Number of turbines", f"{design.n_turbines}"),
        _row("Installed power", f"{design.installed_power_kw:,.0f} kW"),
        _row("Expected annual energy", f"{design.annual_energy_kwh:,.0f} kWh"),
        _row("Demand covered", f"{design.achieved_coverage:.0%}"),
        _row("Land for the array", f"{design.array_area_km2:.2f} km2"),
    ])
    checks = "".join(
        f'<li><span style="color:{colors[f.severity]}"><b>[{_LABELS[f.severity]}]</b></span> '
        f"{escape(f.message)}</li>"
        for f in findings
    )
    why = "".join(
        explanation_html(key, wind_worked_example(key, inp, design))
        for key in WIND_TOPIC_ORDER
        if key in EXPLANATIONS
    )
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>1. Inputs</h2><table>{inputs_rows}</table>
<h2>2. Results</h2><table>{results_rows}</table>
<h2>3. Design checks</h2><ul>{checks}</ul>
<h2>4. Method and formulas</h2>{why}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational sizing only:
not a substitute for a wind measurement campaign and detailed design (see DISCLAIMER).</i></p>
</body></html>"""
