"""Self-contained HTML report of a PV design (the GUI turns it into a PDF)."""

from __future__ import annotations

from html import escape

from resize_energy import __version__
from resize_energy.core.battery_design import MODES as BATTERY_MODES
from resize_energy.core.battery_design import BatteryDesign, BatteryInputs
from resize_energy.core.biomass_design import PATHWAYS, BiomassDesign, BiomassInputs
from resize_energy.core.comparison import ComparisonInputs, ComparisonResult
from resize_energy.core.geothermal_design import PATHWAYS as GEO_PATHWAYS
from resize_energy.core.geothermal_design import GeothermalDesign, GeothermalInputs
from resize_energy.core.hydro_design import HydroDesign, HydroInputs
from resize_energy.core.hydrogen_design import MODES, HydrogenDesign, HydrogenInputs
from resize_energy.core.pv_design import PVDesign, PVInputs
from resize_energy.core.solar_thermal import CHILLERS as SOLAR_CHILLERS
from resize_energy.core.solar_thermal_design import SolarThermalDesign, SolarThermalInputs
from resize_energy.core.wind_design import WindDesign, WindInputs
from resize_energy.report.charts import (
    ChartSpec,
    battery_charts,
    biomass_charts,
    comparison_charts,
    geothermal_charts,
    hydro_charts,
    hydrogen_charts,
    pv_charts,
    solar_charts,
    wind_charts,
)
from resize_energy.report.versus import versus_rounds
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.explanations import EXPLANATIONS, TOPIC_ORDER
from resize_energy.tutor.explanations_battery import BATTERY_TOPIC_ORDER
from resize_energy.tutor.explanations_biomass import topics_for
from resize_energy.tutor.explanations_compare import COMPARE_TOPIC_ORDER
from resize_energy.tutor.explanations_geothermal import topics_for as geothermal_topics
from resize_energy.tutor.explanations_hydro import HYDRO_TOPIC_ORDER
from resize_energy.tutor.explanations_hydrogen import HYDROGEN_TOPIC_ORDER
from resize_energy.tutor.explanations_solar import SOLAR_TOPIC_ORDER
from resize_energy.tutor.explanations_wind import WIND_TOPIC_ORDER
from resize_energy.tutor.sources import references_html
from resize_energy.tutor.why_html import explanation_html
from resize_energy.tutor.worked import worked_example
from resize_energy.tutor.worked_battery import battery_worked_example
from resize_energy.tutor.worked_biomass import biomass_worked_example
from resize_energy.tutor.worked_compare import compare_worked_example
from resize_energy.tutor.worked_geothermal import geothermal_worked_example
from resize_energy.tutor.worked_hydro import hydro_worked_example
from resize_energy.tutor.worked_hydrogen import hydrogen_worked_example
from resize_energy.tutor.worked_solar import solar_worked_example
from resize_energy.tutor.worked_wind import wind_worked_example

_LABELS = {"error": "ERROR", "warning": "WARNING", "info": "NOTE", "ok": "OK"}

# Two looks for the same report: "light" for the PDF (white paper), "screen" for the window.
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
    "screen": {
        "colors": {"error": "#B3261E", "warning": "#8F5600", "info": "#1F5FBF", "ok": "#0A7452"},
        "css": (
            "body { color: #0F1B2D; font-size: 10pt; }\n"
            "h1 { font-size: 17pt; color: #0F1B2D; }\n"
            "h2 { font-size: 13pt; margin-top: 16px; color: #0A7452; }\n"
            "h3 { font-size: 10.5pt; margin-bottom: 2px; color: #0A7452; }\n"
            "table { border-collapse: collapse; } td { padding: 2px 10px 2px 0; }\n"
            "code { background-color: #EAF0F6; color: #085F43; }"
        ),
    },
}


def _row(label: str, value: str) -> str:
    return f"<tr><td>{escape(label)}</td><td><b>{escape(value)}</b></td></tr>"


_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2, "ok": 3}


def _checks_html(findings: list[Finding], colors: dict[str, str]) -> str:
    """Summary line plus the checks, the ones that need attention first."""
    errors = sum(f.severity == "error" for f in findings)
    warnings = sum(f.severity == "warning" for f in findings)
    if errors or warnings:
        parts = ([f"{errors} error(s)"] if errors else []) + (
            [f"{warnings} warning(s)"] if warnings else [])
        color = colors["error" if errors else "warning"]
        head = (f'<p><span style="color:{color}"><b>{" and ".join(parts)} to look at.</b></span>'
                " Read them first: they say what to change.</p>")
    else:
        head = (f'<p><span style="color:{colors["ok"]}"><b>No errors and no warnings.</b></span>'
                " The notes below are for your information.</p>")
    ordered = sorted(findings, key=lambda f: _SEVERITY_ORDER.get(f.severity, 9))
    items = "".join(
        f'<li><span style="color:{colors[f.severity]}"><b>[{_LABELS[f.severity]}]</b></span> '
        f"{escape(f.message)}</li>" for f in ordered)
    return f"{head}<ul>{items}</ul>"


def _kpi_html(items: list[tuple[str, str]]) -> str:
    """Big numbers with a plain-language label under each: equal cells, at most four a row."""
    per_row = 4 if len(items) > 3 else max(1, len(items))
    width = 100 // per_row
    rows = []
    for start in range(0, len(items), per_row):
        chunk = items[start:start + per_row]
        cells = "".join(
            f'<td align="center" bgcolor="#E6F5EE" width="{width}%">'
            f'<span style="font-size:16pt; color:#085F43"><b>{escape(v)}</b></span><br>'
            f'<span style="color:#556377; font-size:9pt">{escape(label)}</span></td>'
            for v, label in chunk)
        cells += f'<td width="{width}%"></td>' * (per_row - len(chunk))
        rows.append(f"<tr>{cells}</tr>")
    return f'<table width="100%" cellspacing="6" cellpadding="9">{"".join(rows)}</table>'


def _charts_html(charts: dict[str, ChartSpec]) -> str:
    return "".join(
        f'<p align="center"><img src="chart:{name}" width="{c.width}" height="{c.height}">'
        + (f'<br><span style="color:#556377">{escape(c.caption)}</span>' if c.caption else "")
        + "</p>" for name, c in charts.items())


def _versus_html(r: ComparisonResult) -> str:
    """Round by round table with proportional bars (the window shows the animated version)."""
    out = []
    for i, rd in enumerate(versus_rounds(r), start=1):
        out.append(f'<tr><td colspan="3"><b>Round {i}: {escape(rd.title)}</b> '
                   f'<span style="color:#556377">({escape(rd.hint)})</span></td></tr>')
        for e in rd.entries:
            pct = max(1, round(100 * e.score))
            star = " &#9733;" if rd.winner == e.name else ""
            out.append(
                f"<tr><td>{escape(e.name)}</td><td>{escape(e.text)}{star}</td>"
                f'<td width="200"><table width="100%" cellspacing="0"><tr>'
                f'<td width="{pct}%" bgcolor="{_TECH_COLORS[e.key]}">&nbsp;</td><td></td>'
                "</tr></table></td></tr>")
    return f'<table cellpadding="2">{"".join(out)}</table>'


def _glance(kpis: list[tuple[str, str]], verdict: str,
            more: list[tuple[str, str]] | None = None) -> str:
    second = _kpi_html(more) if more else ""
    return f"{_kpi_html(kpis)}{second}<p>{verdict}</p>"


def _status_phrase(findings: list[Finding]) -> str:
    errors = sum(f.severity == "error" for f in findings)
    warnings = sum(f.severity == "warning" for f in findings)
    if errors:
        return f"<b>{errors} check(s) failed: see 'Design checks'.</b>"
    if warnings:
        return f"{warnings} warning(s) to read in 'Design checks'."
    return "All design checks passed."


def _energy(kwh: float) -> str:
    if abs(kwh) >= 5e6:
        return f"{kwh / 1e6:,.1f} GWh"
    if abs(kwh) >= 5e3:
        return f"{kwh / 1e3:,.1f} MWh"
    return f"{kwh:,.0f} kWh"


def _economics_rows(e, econ) -> tuple[str, str]:
    """(input rows, result rows) of the cost step; empty when it was not filled in."""
    if e is None or econ is None:
        return "", ""
    inputs = "".join([
        _row("Cost of the plant", f"{e.capex_per_kw:,.0f} euro/kW"),
        _row("Operation and maintenance", f"{e.om_per_kw_year:,.0f} euro/kW per year"),
        _row("Lifetime / discount rate", f"{e.life_years:g} years / {e.discount_rate:.1%}"),
        _row("Price paid for electricity / paid for the surplus",
             f"{e.retail_price:.3f} / {e.export_price:.3f} euro/kWh"),
        _row("Grid emission factor / plant life-cycle",
             f"{e.grid_ef:.2f} kg/kWh / {e.lifecycle_g_per_kwh:.0f} g/kWh"),
    ])
    results = "".join([
        _row("Investment (CAPEX)", f"{econ.capex:,.0f} euro"),
        _row("Maintenance per year", f"{econ.om_per_year:,.0f} euro"),
        _row("Savings per year", f"{econ.savings_per_year:,.0f} euro "
             f"({econ.self_used_kwh:,.0f} kWh used, {econ.exported_kwh:,.0f} kWh exported)"),
        _row("Cost of the energy (LCOE)", f"{econ.lcoe:.3f} euro/kWh"),
        _row("Payback (simple / discounted)",
             f"{econ.payback_years:.1f} / {econ.discounted_payback_years:.1f} years"),
        _row("Net present value", f"{econ.npv:,.0f} euro"),
        _row("CO2 avoided", f"{econ.co2_avoided_t_per_year:.2f} t per year"),
    ])
    return inputs, results


def _economics_glance(econ) -> list[tuple[str, str]]:
    if econ is None:
        return []
    pay = f"{econ.payback_years:.1f} years" if econ.payback_years < 1e3 else "never"
    return [(f"{econ.lcoe:.3f} euro/kWh", "cost of the energy (LCOE)"),
            (pay, "simple payback"), (f"{econ.npv:,.0f} euro", "net present value")]


def build_pv_report(
    inp: PVInputs,
    design: PVDesign,
    findings: list[Finding],
    title: str = "Preliminary PV sizing report",
    site_note: str = "",
    theme: str = "light",
) -> str:
    """HTML string with inputs, results, checks and the formulas used.

    ``theme`` is "light" (for the PDF) or "screen" (for showing it inside the window).
    """
    look = _THEMES.get(theme, _THEMES["light"])
    colors = look["colors"]
    m, inv = inp.module, inp.inverter

    inputs_rows = "".join([
        _row("Annual electricity demand", f"{inp.annual_demand_kwh:,.0f} kWh"),
        _row("Target PV coverage", f"{inp.coverage:.0%}"),
        _row("Annual in-plane irradiation", f"{inp.annual_irradiation_kwh_m2:,.0f} kWh/m2"),
        _row("Performance ratio", f"{inp.performance_ratio:.2f}"),
        _row("Shading loss", f"{inp.shading_loss:.1%}" if inp.shading_loss > 0 else "none"),
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
    ]) + _economics_rows(inp.economics, design.economics)[0]

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
    ]) + _economics_rows(inp.economics, design.economics)[1]


    why = "".join(
        explanation_html(key, worked_example(key, inp, design), math=True)
        for key in TOPIC_ORDER
        if key in EXPLANATIONS
    )

    status = _status_phrase(findings)
    if design.feasible:
        verdict = (f"Install <b>{design.n_modules} modules</b> ({design.dc_power_kwp:.1f} kWp, "
                   f"{design.array_area_m2:,.0f} m2 of roof or land), wired as {design.n_series} "
                   f"in series x {design.n_parallel} strings, to cover "
                   f"<b>{design.achieved_coverage:.0%}</b> of your demand. {status}")
    else:
        verdict = ("<b>This module and inverter combination does not work</b>: the string "
                   f"voltages do not fit the inverter. {status}")
    glance = _glance([
        (f"{design.dc_power_kwp:.1f} kWp", "PV power to install"),
        (f"{design.n_modules} modules", f"{design.n_series} in series x {design.n_parallel} "
         "strings"),
        (_energy(design.annual_energy_kwh), "expected energy per year"),
        (f"{design.achieved_coverage:.0%}", "of your demand covered"),
    ], verdict, _economics_glance(design.economics))
    charts_html = _charts_html(pv_charts(inp, design))
    checks_html = _checks_html(findings, colors)
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>In short</h2>{glance}
<h2>The numbers in pictures</h2>{charts_html}
<h2>Design checks</h2>{checks_html}
<h2>Results in detail</h2><table>{results_rows}</table>
<h2>Your inputs</h2><table>{inputs_rows}</table>
<h2>Method and formulas</h2>{why}{references_html(why)}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational sizing only:
not a substitute for detailed engineering design (see DISCLAIMER).</i></p>
</body></html>"""


def _wake_model_text(inp: WindInputs) -> str:
    if not (inp.wake_model or inp.layout_mode == "optimized"):
        return "off: the single 'other losses' number"
    if inp.rose is not None:
        wind_text = (f"measured wind rose ({inp.rose.source}, "
                     f"{', '.join(str(y) for y in inp.rose.years)}), energy mainly from "
                     f"{inp.rose.prevailing_deg():.0f} deg")
    else:
        wind_text = (f"wind from {inp.prevailing_direction_deg:.0f} deg (concentration "
                     f"{inp.rose_concentration:g})")
    return f"Jensen, k = {inp.wake_decay}, {wind_text}"


def _layout_rows(inp: WindInputs, design: WindDesign) -> list[str]:
    if design.site is not None:
        rows = [_row("Layout", "turbines placed by the program"),
                _row("Site (width x length, length towards)",
                     f"{design.site.width_m:,.0f} m x {design.site.length_m:,.0f} m, "
                     f"{design.site.rotation_deg:.0f} deg"),
                _row("Minimum distance between turbines", f"{inp.min_spacing_d:g} D")]
        return rows
    return [_row("Layout", f"regular grid, {'staggered' if inp.stagger_rows else 'aligned'} rows"),
            _row("Spacing (across x along the wind)",
                 f"{inp.crosswind_spacing_d:.0f} D x {inp.downwind_spacing_d:.0f} D")]


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
        _row("Wake model", _wake_model_text(inp)),
        *_layout_rows(inp, design),
    ]) + _economics_rows(inp.economics, design.economics)[0]
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
        *([_row("Wake loss", f"{design.wake_loss:.1%}"
                + (f" (a regular grid of the same turbines: {design.grid_wake_loss:.1%})"
                   if design.grid_wake_loss is not None else ""))]
          if design.wake is not None else []),
    ]) + _economics_rows(inp.economics, design.economics)[1]
    why = "".join(
        explanation_html(key, wind_worked_example(key, inp, design), math=True)
        for key in WIND_TOPIC_ORDER
        if key in EXPLANATIONS
    )
    status = _status_phrase(findings)
    verdict = (f"<b>{design.n_turbines} turbine(s)</b> of {t.rated_power_kw:,.0f} kW "
               f"({design.installed_power_kw:,.0f} kW in total) produce about "
               f"{_energy(design.annual_energy_kwh)} a year, <b>{design.achieved_coverage:.0%}</b> "
               f"of your demand. {status}")
    glance = _glance([
        (f"{design.n_turbines} x {t.rated_power_kw:,.0f} kW", "turbines needed"),
        (_energy(design.annual_energy_kwh), "expected energy per year"),
        (f"{design.capacity_factor_net:.0%}", "capacity factor (time at full power)"),
        (f"{design.achieved_coverage:.0%}", "of your demand covered"),
    ], verdict, _economics_glance(design.economics))
    charts_html = _charts_html(wind_charts(inp, design))
    checks_html = _checks_html(findings, colors)
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>In short</h2>{glance}
<h2>The numbers in pictures</h2>{charts_html}
<h2>Design checks</h2>{checks_html}
<h2>Results in detail</h2><table>{results_rows}</table>
<h2>Your inputs</h2><table>{inputs_rows}</table>
<h2>Method and formulas</h2>{why}{references_html(why)}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational sizing only:
not a substitute for a wind measurement campaign and detailed design (see DISCLAIMER).</i></p>
</body></html>"""


def _years(value: float) -> str:
    return "never" if value == float("inf") else f"{value:.1f}"


def _payback(value: float) -> str:
    return "never" if value == float("inf") else f"{value:.1f} years"


def _bar_rows(label: str, items: list[tuple[str, float, str]]) -> str:
    """One heading row and one proportional bar per (caption, value, colour) item.

    Bars are rich-text tables, so they also render in the window and in the PDF.
    """
    finite = [v for _, v, _ in items if v != float("inf")]
    top = max(finite, default=0.0)
    out = [f'<tr><td colspan="2"><i>{escape(label)}</i></td></tr>']
    for caption, value, color in items:
        pct = 100 if value == float("inf") or top <= 0 else max(2, round(100 * value / top))
        out.append(
            f'<tr><td>{escape(caption)}</td><td width="220"><table width="100%" cellspacing="0">'
            f'<tr><td width="{pct}%" bgcolor="{color}">&nbsp;</td><td></td></tr></table></td></tr>')
    return "".join(out)


_TECH_COLORS = {"pv": "#0A7452", "wind": "#1F5FBF", "biomass": "#8F5600", "hydrogen": "#7B3FB8"}
_TECH_SHORT = {"pv": "PV", "wind": "Wind", "biomass": "Biomass", "hydrogen": "Hydrogen"}


def build_comparison_report(
    inp: ComparisonInputs,
    r: ComparisonResult,
    findings: list[Finding],
    title: str = "",
    site_note: str = "",
    theme: str = "light",
) -> str:
    """HTML with the side-by-side figures, the checks and the formulas of the comparison."""
    look = _THEMES.get(theme, _THEMES["light"])
    colors = look["colors"]
    c = inp.costs
    techs = r.techs
    title = title or "Technology comparison: " + " vs ".join(_TECH_SHORT[t.key] for t in techs)

    def line(label: str, values: list[str]) -> str:
        cells = "".join(f'<td align="right"><b>{escape(v)}</b></td>' for v in values)
        return f"<tr><td>{escape(label)}</td>{cells}</tr>"

    def unit(t) -> str:
        return "kWh (H2, LHV)" if t.product == "hydrogen" else "kWh"

    head = "".join(f'<td align="right"><b>{escape(t.name)}</b></td>' for t in techs)
    table = "".join([
        line("Installed power", [f"{t.installed_kw:,.0f} kW" for t in techs]),
        line("Energy per year", [f"{t.energy_kwh:,.0f} {unit(t)}" for t in techs]),
        line("Demand covered", [f"{t.coverage:.0%}" for t in techs]),
        line("Full-load hours", [f"{t.full_load_hours:,.0f} h" for t in techs]),
        line("Investment (CAPEX)", [f"{t.capex_eur:,.0f} euro" for t in techs]),
        line("Running costs per year", [f"{t.om_eur_per_year:,.0f} euro" for t in techs]),
        line("Cost of energy (LCOE)", [f"{t.lcoe_eur_per_kwh:.3f} euro/kWh" for t in techs]),
        line("Savings per year", [f"{t.savings_eur_per_year:,.0f} euro" for t in techs]),
        line("Simple payback", [f"{_years(t.payback_years)} years" for t in techs]),
        line("Discounted payback", [f"{_years(t.discounted_payback_years)} years"
                                    for t in techs]),
        line("Net present value", [f"{t.npv_eur:,.0f} euro" for t in techs]),
        line("CO2 per kWh (life cycle)", [f"{t.co2_own_kg_per_kwh * 1000:,.0f} g" for t in techs]),
        line("CO2 avoided per year", [f"{t.co2_avoided_t_per_year:,.0f} t" for t in techs]),
        line("CO2 avoided over the lifetime", [f"{t.co2_avoided_lifetime_t:,.0f} t"
                                               for t in techs]),
    ])
    rows = [
        _row("Annual energy demand / coverage",
             f"{inp.annual_demand_kwh:,.0f} kWh / {inp.coverage:.0%}"),
        _row("Discount rate", f"{c.discount_rate:.1%}"),
        _row("Retail / export price",
             f"{c.retail_price_eur_per_kwh:.3f} / {c.export_price_eur_per_kwh:.3f} euro/kWh"),
        _row("Grid emission factor", f"{c.grid_kg_co2_per_kwh:.3f} kg CO2/kWh"),
    ]
    keys = [t.key for t in techs]
    if "pv" in keys or ("hydrogen" in keys and inp.h2_use_pv):
        rows.append(_row("Irradiation / performance ratio",
                         f"{inp.annual_irradiation_kwh_m2:,.0f} kWh/m2 / "
                         f"{inp.performance_ratio:.2f}"))
    if "wind" in keys or ("hydrogen" in keys and inp.h2_use_wind):
        rows.append(_row("Wind speed / turbine",
                         f"{inp.wind.mean_speed_ref_ms:.2f} m/s at {inp.wind.ref_height_m:.0f} m"
                         f" / {inp.wind.turbine.name} ({inp.wind.turbine.rated_power_kw:,.0f} kW)"))
    if "pv" in keys:
        rows.append(_row("PV cost", f"{c.pv_capex_eur_per_kwp:,.0f} euro/kWp + "
                         f"{c.pv_om_eur_per_kwp_year:,.0f} euro/kWp/year, "
                         f"{c.pv_lifetime_years:.0f} years, {c.pv_lifecycle_g_per_kwh:.0f} g/kWh"))
    if "wind" in keys:
        rows.append(_row("Wind cost", f"{c.wind_capex_eur_per_kw:,.0f} euro/kW + "
                         f"{c.wind_om_eur_per_kw_year:,.0f} euro/kW/year, "
                         f"{c.wind_lifetime_years:.0f} years, {c.wind_lifecycle_g_per_kwh:.0f} g/kWh"))
    if "biomass" in keys:
        b = inp.biomass
        rows.append(_row("Biogas CHP", f"{c.bio_capex_eur_per_kwe:,.0f} euro/kWe + "
                         f"{c.bio_om_eur_per_kwe_year:,.0f} euro/kWe/year + feedstock "
                         f"{c.bio_feedstock_eur_per_t:,.0f} euro/t, {c.bio_lifetime_years:.0f} years, "
                         f"{c.bio_lifecycle_g_per_kwh:.0f} g/kWh; {1 - b.share_b:.0%} "
                         f"{b.substrate_a.name} + {b.share_b:.0%} {b.substrate_b.name}"))
    if "hydrogen" in keys:
        src = " + ".join(n for n, on in (("PV", inp.h2_use_pv), ("wind", inp.h2_use_wind)) if on)
        rows.append(_row("Green hydrogen",
                         f"{c.h2_electrolyser_capex_eur_per_kw:,.0f} euro/kW electrolyser, fed by "
                         f"{src} (invented hourly year); reference: natural gas hydrogen "
                         f"{c.h2_reference_price_eur_per_kg:.2f} euro/kg, "
                         f"{c.h2_reference_kg_co2_per_kg:.1f} kg CO2/kg"))
    inputs_rows = "".join(rows)
    verdict = (
        f"<ul><li>Lowest cost of energy (LCOE): <b>{escape(r.lowest_lcoe)}</b></li>"
        f"<li>Fastest simple payback: <b>{escape(r.fastest_payback)}</b></li>"
        f"<li>Highest net present value: <b>{escape(r.highest_npv)}</b></li>"
        f"<li>Most CO2 avoided per year: <b>{escape(r.most_co2)}</b></li></ul>")
    why = "".join(
        explanation_html(key, compare_worked_example(key, inp, r), math=True)
        for key in COMPARE_TOPIC_ORDER
        if key in EXPLANATIONS
    )
    versus = _versus_html(r)
    glance = _kpi_html([
        (r.lowest_lcoe, "cheapest energy"), (r.fastest_payback, "fastest payback"),
        (r.highest_npv, "highest net present value"), (r.most_co2, "most CO2 avoided"),
    ])
    charts_html = _charts_html(comparison_charts(inp, r))
    checks_html = _checks_html(findings, colors)
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>Which is better, and for what?</h2>{glance}{verdict}
<h2>Round by round</h2>{versus}
<h2>The numbers in pictures</h2>{charts_html}
<h2>Checks</h2>{checks_html}
<h2>All figures side by side</h2>
<table cellpadding="3"><tr><td></td>{head}</tr>{table}</table>
<h2>Your inputs and assumptions</h2><table>{inputs_rows}</table>
<h2>Method and formulas</h2>{why}{references_html(why)}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational comparison:
prices are placeholders to be replaced with local quotes, and the hour-by-hour match is not
modelled (see DISCLAIMER).</i></p>
</body></html>"""


def build_biomass_report(
    inp: BiomassInputs,
    d: BiomassDesign,
    findings: list[Finding],
    title: str = "Preliminary biomass sizing report",
    site_note: str = "",
    theme: str = "light",
) -> str:
    """HTML string with inputs, results, checks and the formulas of a biomass design."""
    look = _THEMES.get(theme, _THEMES["light"])
    colors = look["colors"]
    biogas = d.pathway == "biogas"
    if biogas:
        a, b = inp.substrate_a, inp.substrate_b
        inputs = [
            _row("Pathway", PATHWAYS[inp.pathway]),
            _row("Electricity demand / coverage",
                 f"{inp.annual_electricity_demand_kwh:,.0f} kWh / {inp.coverage:.0%}"),
            _row("Heat demand", f"{inp.annual_heat_demand_kwh:,.0f} kWh"),
            _row("Substrates", f"{1 - inp.share_b:.0%} {a.name} + {inp.share_b:.0%} {b.name}"),
            _row("CHP efficiency (electrical / thermal)", f"{inp.eta_el:.2f} / {inp.eta_th:.2f}"),
            _row("CHP hours / parasitic electricity",
                 f"{inp.operating_hours:,.0f} h / {inp.parasitic_electricity:.0%}"),
            _row("Digester heating / retention time",
                 f"{inp.digester_heat_share:.0%} of the CHP heat / {inp.hrt_days:.0f} days"),
        ]
        results = [
            _row("CHP electric power (gross)", f"{d.electric_power_kw:,.0f} kW"),
            _row("Electricity net / gross",
                 f"{d.electricity_net_kwh:,.0f} / {d.electricity_gross_kwh:,.0f} kWh"),
            _row("Methane / biogas", f"{d.ch4_m3_per_year:,.0f} / {d.biogas_m3_per_year:,.0f} Nm3"
                 f" ({d.ch4_fraction:.0%} CH4)"),
            _row("Substrate per year", f"{d.mass_t_per_year:,.0f} t"),
            _row("Digester total / working volume",
                 f"{d.digester_volume_m3:,.0f} / {d.working_volume_m3:,.0f} m3"),
            _row("Organic loading rate", f"{d.olr_kg_vs_per_m3_day:.2f} kg VS/(m3 d)"),
            _row("Heat total / digester / useful",
                 f"{d.heat_total_kwh:,.0f} / {d.heat_digester_kwh:,.0f} / "
                 f"{d.heat_useful_kwh:,.0f} kWh"),
            _row("Crop land / digestate", f"{d.crop_hectares:,.0f} ha / "
                 f"{d.digestate_t_per_year:,.0f} t per year"),
            _row("CO2 avoided", f"{d.co2_avoided_t_per_year:,.0f} t per year"),
        ]
    else:
        f = inp.fuel
        inputs = [
            _row("Pathway", PATHWAYS[inp.pathway]),
            _row("Heat demand / peak load",
                 f"{inp.annual_heat_demand_kwh:,.0f} kWh / {inp.peak_heat_kw:,.0f} kW"),
            _row("Share of the heat to cover", f"{inp.coverage:.0%}"),
            _row("Fuel", f"{f.name}; LHV dry {f.lhv_dry_kwh_per_kg:.2f} kWh/kg; "
                 f"bulk {f.bulk_density_kg_m3:.0f} kg/m3"),
            _row("Efficiency (thermal / electrical)", f"{inp.eta_th:.2f} / {inp.eta_el:.2f}"),
            _row("Storage autonomy / truck", f"{inp.storage_days:.0f} days / "
                 f"{inp.truck_volume_m3:.0f} m3"),
        ]
        results = [
            _row("Load factor", f"{d.load_factor:.2f}"),
            _row("Plant thermal power", f"{d.thermal_power_kw:,.0f} kW "
                 f"({d.power_ratio:.0%} of the peak)"),
            _row("Plant electric power", f"{d.electric_power_kw:,.0f} kW"),
            _row("Useful heat per year", f"{d.heat_useful_kwh:,.0f} kWh"),
            _row("Electricity per year", f"{d.electricity_net_kwh:,.0f} kWh"),
            _row("Full-load hours", f"{d.full_load_hours:,.0f} h"),
            _row("Fuel energy / LHV as received",
                 f"{d.fuel_energy_kwh:,.0f} kWh / {d.lhv_as_received_kwh_per_kg:.2f} kWh/kg"),
            _row("Fuel per year", f"{d.mass_t_per_year:,.0f} t"),
            _row("Storage / deliveries", f"{d.storage_m3:,.0f} m3 / {d.deliveries_per_year} "
                 "truck loads per year"),
            _row("Ash", f"{d.ash_t_per_year:.1f} t per year"),
            _row("CO2 avoided", f"{d.co2_avoided_t_per_year:,.0f} t per year"),
        ]
    why = "".join(
        explanation_html(key, biomass_worked_example(key, inp, d), math=True)
        for key in topics_for(d.pathway)
        if key in EXPLANATIONS
    )
    status = _status_phrase(findings)
    if biogas:
        verdict = (f"A CHP engine of <b>{d.electric_power_kw:,.0f} kW</b> fed by a digester of "
                   f"{d.digester_volume_m3:,.0f} m3 gives {_energy(d.electricity_net_kwh)} of "
                   f"electricity a year, <b>{d.electricity_coverage:.0%}</b> of your demand. "
                   f"{status}")
        glance = _glance([
            (f"{d.electric_power_kw:,.0f} kW", "electric power of the engine"),
            (_energy(d.electricity_net_kwh), "electricity per year"),
            (f"{d.digester_volume_m3:,.0f} m3", "digester volume"),
            (f"{d.electricity_coverage:.0%}", "of your demand covered"),
        ], verdict)
    else:
        verdict = (f"A plant of <b>{d.thermal_power_kw:,.0f} kW</b> (heat) burning "
                   f"{d.mass_t_per_year:,.0f} t of fuel a year covers "
                   f"<b>{d.heat_coverage:.0%}</b> of your heat demand; the rest is left to a "
                   f"back-up boiler. {status}")
        glance = _glance([
            (f"{d.thermal_power_kw:,.0f} kW", "heat power of the plant"),
            (_energy(d.heat_useful_kwh), "heat per year"),
            (f"{d.mass_t_per_year:,.0f} t", "fuel per year"),
            (f"{d.heat_coverage:.0%}", "of your heat covered"),
        ], verdict)
    charts_html = _charts_html(biomass_charts(inp, d))
    checks_html = _checks_html(findings, colors)
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>In short</h2>{glance}
<h2>The numbers in pictures</h2>{charts_html}
<h2>Design checks</h2>{checks_html}
<h2>Results in detail</h2><table>{"".join(results)}</table>
<h2>Your inputs</h2><table>{"".join(inputs)}</table>
<h2>Method and formulas</h2>{why}{references_html(why)}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational sizing only:
fuel quality, supply contracts, emissions permits and detailed design are not covered
(see DISCLAIMER).</i></p>
</body></html>"""


def build_hydrogen_report(
    inp: HydrogenInputs,
    d: HydrogenDesign,
    findings: list[Finding],
    title: str = "Preliminary green hydrogen sizing report",
    site_note: str = "",
    theme: str = "light",
) -> str:
    """HTML string with inputs, results, checks and the formulas of a hydrogen design."""
    look = _THEMES.get(theme, _THEMES["light"])
    colors = look["colors"]
    sources = ", ".join(n for n, on in (("PV", inp.use_pv), ("wind", inp.use_wind),
                                        ("grid", inp.use_grid)) if on)
    inputs = "".join([
        _row("Starting point", MODES[inp.mode]),
        _row("Electricity sources", sources),
        _row("Hourly profiles", d.profile_source),
        _row("Consumption (stack and auxiliaries)", f"{inp.kwh_per_kg_stack:.1f} kWh/kg"),
        _row("Minimum load", f"{inp.min_load:.0%}"),
        _row("Pressure (outlet / storage)", f"{inp.outlet_bar:.0f} / {inp.storage_bar:.0f} bar"),
        _row("Storage", f"{inp.storage_days:.0f} days of autonomy" if inp.storage_mode == "days"
             else "sized hour by hour from the production"),
        _row("Part-load efficiency", f"on (auxiliaries {inp.aux_share:.0%}, stack gain "
             f"{inp.stack_gain:.0%})" if inp.part_load_model else "off (one constant value)"),
        _row("Stack ageing", f"{inp.degradation_per_1000h:.2%} per 1000 h"
             if inp.degradation_per_1000h > 0 else "off"),
        _row("Grid purchase", "cheapest hours first, hourly prices" if inp.cheapest_hours_first
             else "spread evenly" if inp.use_grid else "not used"),
        _row("Grid limit", f"{inp.grid_hours_cap:,.0f} full-load hours" if inp.use_grid
             else "not used"),
        _row("Costs",
             f"electrolyser {inp.electrolyser_capex_per_kw:,.0f} euro/kW, PV "
             f"{inp.pv_capex_per_kwp:,.0f} euro/kWp, wind {inp.wind_capex_per_kw:,.0f} euro/kW, "
             f"grid {inp.grid_price_per_kwh:.3f} euro/kWh, discount {inp.discount_rate:.1%}"),
    ])
    results = "".join([
        _row("Electrolyser power", f"{d.electrolyser_kw:,.0f} kW"),
        _row("PV / wind power", f"{d.pv_kwp:,.0f} kWp / {d.wind_kw:,.0f} kW"),
        _row("Hydrogen per year", f"{d.hydrogen_kg:,.0f} kg ({d.hydrogen_kg_per_day:,.0f} kg/day)"),
        _row("Full-load hours / hours on", f"{d.full_load_hours:,.0f} h / {d.hours_on:,} h"),
        _row("Electricity used", f"{d.electricity_kwh:,.0f} kWh "
             f"({d.kwh_per_kg_total:.1f} kWh/kg, efficiency {d.efficiency_lhv:.0%} LHV)"),
        _row("Renewable used / curtailed", f"{d.res_used_kwh:,.0f} kWh ({d.res_utilisation:.0%})"
             f" / {d.curtailed_kwh:,.0f} kWh"),
        _row("Grid energy", f"{d.grid_kwh:,.0f} kWh ({d.grid_share:.0%})"),
        _row("Water / oxygen", f"{d.water_m3:,.0f} m3 / {d.oxygen_t:,.0f} t per year"),
        _row("Storage", f"{d.storage_kg:,.0f} kg = {d.storage_m3:,.1f} m3 at "
             f"{inp.storage_bar:.0f} bar"),
        _row("Stack life", f"{d.stack_life_years:.1f} years"),
        _row("Cost of hydrogen (LCOH)", f"{d.lcoh:.2f} euro/kg"),
        _row("Carbon intensity", f"{d.co2_kg_per_kg:.2f} kg CO2 per kg H2"),
        _row("CO2 saved vs grey hydrogen", f"{d.co2_saved_t_per_year:,.0f} t per year"),
    ])
    parts = [("Electrolyser", d.cost_electrolyser), ("Stack replacement", d.cost_stack),
             ("Storage", d.cost_storage), ("Renewable plant", d.cost_res),
             ("Grid electricity", d.cost_grid), ("Water", d.cost_water)]
    top = max(v for _, v in parts) or 1.0
    bars = "".join(
        f'<tr><td>{escape(n)}</td><td align="right">{v:,.0f} euro/year</td>'
        f'<td width="200"><table width="100%" cellspacing="0"><tr>'
        f'<td width="{max(1, round(100 * v / top))}%" bgcolor="#0A7452">&nbsp;</td><td></td>'
        f"</tr></table></td></tr>"
        for n, v in parts if v > 0)
    why = "".join(
        explanation_html(key, hydrogen_worked_example(key, inp, d), math=True)
        for key in HYDROGEN_TOPIC_ORDER
        if key in EXPLANATIONS
    )
    status = _status_phrase(findings)
    green = d.co2_kg_per_kg <= 3.4
    verdict = (f"<b>{d.hydrogen_kg:,.0f} kg</b> of hydrogen a year with a "
               f"{d.electrolyser_kw:,.0f} kW electrolyser, at about <b>{d.lcoh:.2f} euro/kg</b>. "
               f"Its carbon footprint is {d.co2_kg_per_kg:.1f} kg CO2 per kg: "
               + ("below the EU limit for renewable hydrogen. " if green else
                  "above the EU limit (3.4), so it does not count as renewable. ") + status)
    glance = _glance([
        (f"{d.hydrogen_kg:,.0f} kg", "hydrogen per year"),
        (f"{d.lcoh:.2f} euro/kg", "cost of the hydrogen (LCOH)"),
        (f"{d.full_load_hours:,.0f} h", "electrolyser at full power per year"),
        (f"{d.co2_kg_per_kg:.1f} kg", "CO2 per kg of hydrogen"),
    ], verdict)
    charts_html = _charts_html(hydrogen_charts(inp, d))
    checks_html = _checks_html(findings, colors)
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>In short</h2>{glance}
<h2>The numbers in pictures</h2>{charts_html}
<h2>Design checks</h2>{checks_html}
<h2>Results in detail</h2><table>{results}</table>
<h2>Your inputs</h2><table>{inputs}</table>
<h2>Where the cost comes from, in euro per year</h2><table cellpadding="2">{bars}</table>
<h2>Method and formulas</h2>{why}{references_html(why)}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational sizing only:
no dynamic model of the electrolyser, no safety, permitting or grid-connection study
(see DISCLAIMER).</i></p>
</body></html>"""


def build_battery_report(
    inp: BatteryInputs,
    d: BatteryDesign,
    findings: list[Finding],
    title: str = "Preliminary battery storage sizing report",
    site_note: str = "",
    theme: str = "light",
) -> str:
    """HTML string with inputs, results, checks and the formulas of a battery design."""
    look = _THEMES.get(theme, _THEMES["light"])
    colors = look["colors"]
    plant = ", ".join(x for x in (f"PV {inp.pv_kwp:g} kWp" if inp.use_pv else "",
                                  f"wind {inp.wind_kw:g} kW" if inp.use_wind else "") if x)
    inputs = "".join([
        _row("Starting point", BATTERY_MODES[inp.mode]),
        _row("Plant", plant),
        _row("Load", f"{inp.load_kind}, {inp.annual_demand_kwh:,.0f} kWh/year"),
        _row("Production profile", d.profile_source),
        _row("Battery", f"round trip {inp.eta_roundtrip:.0%}, depth of discharge "
             f"{inp.usable_fraction:.0%}, state of health {inp.health:.0%}, C-rate {inp.c_rate}"),
        _row("Life", f"{inp.cycle_life:,.0f} cycles or {inp.calendar_life_years:.0f} years"),
        _row("Prices", f"buy {inp.retail_price} euro/kWh, sell {inp.export_price} euro/kWh, "
             f"discount {inp.discount_rate:.1%}"),
        _row("Battery cost", f"{inp.capex_per_kwh:,.0f} euro/kWh + {inp.capex_per_kw:,.0f} "
             f"euro/kW, O&M {inp.om_fraction:.1%} of the CAPEX per year"),
    ])
    results = "".join([
        _row("Battery", f"{d.capacity_kwh:.1f} kWh ({d.usable_kwh:.1f} kWh usable), "
             f"{d.power_kw:.1f} kW"),
        _row("Self-sufficiency", f"{d.self_sufficiency_without:.0%} without, "
             f"{d.self_sufficiency:.0%} with the battery"),
        _row("Self-consumption", f"{d.self_consumption_without:.0%} without, "
             f"{d.self_consumption:.0%} with the battery"),
        _row("Imported / exported", f"{d.import_kwh:,.0f} / {d.export_kwh:,.0f} kWh "
             f"(without: {d.import_without_kwh:,.0f} / {d.export_without_kwh:,.0f})"),
        _row("Delivered by the battery", f"{d.battery_kwh:,.0f} kWh/year "
             f"({d.loss_kwh:,.0f} kWh lost)"),
        _row("Cycles / life", f"{d.cycles_per_year:.0f} per year / {d.life_years:.1f} years "
             f"({d.life_limit})"),
        _row("CAPEX / O&M", f"{d.capex:,.0f} euro / {d.om_per_year:,.0f} euro per year"),
        _row("Savings", f"{d.savings_per_year:,.0f} euro per year"),
        _row("Payback / NPV", f"{d.payback_years:.1f} years / {d.npv:,.0f} euro"),
        _row("Cost of storage (LCOS)", f"{d.lcos:.3f} euro/kWh"),
        _row("CO2 avoided", f"{d.co2_avoided_t_per_year:,.2f} t per year"),
    ])
    why = "".join(
        explanation_html(key, battery_worked_example(key, inp, d), math=True)
        for key in BATTERY_TOPIC_ORDER
        if key in EXPLANATIONS
    )
    gain = d.self_sufficiency - d.self_sufficiency_without
    money = ("it repays itself" if d.npv >= 0 else "over its life it costs more than it saves")
    verdict = (f"A <b>{d.capacity_kwh:.1f} kWh</b> battery raises self-sufficiency from "
               f"{d.self_sufficiency_without:.0%} to <b>{d.self_sufficiency:.0%}</b> "
               f"(+{gain * 100:.0f} points) and {money} (NPV {d.npv:,.0f} euro). "
               + _status_phrase(findings))
    glance = _glance([
        (f"{d.capacity_kwh:.1f} kWh", "battery capacity"),
        (f"{d.self_sufficiency:.0%}", f"self-sufficiency (was {d.self_sufficiency_without:.0%})"),
        (f"{d.payback_years:.0f} years" if d.payback_years != float("inf") else "never",
         "payback time"),
        (f"{d.npv:,.0f} euro", "net present value"),
    ], verdict)
    charts_html = _charts_html(battery_charts(inp, d))
    checks_html = _checks_html(findings, colors)
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>In short</h2>{glance}
<h2>The numbers in pictures</h2>{charts_html}
<h2>Design checks</h2>{checks_html}
<h2>Results in detail</h2><table>{results}</table>
<h2>Your inputs</h2><table>{inputs}</table>
<h2>Method and formulas</h2>{why}{references_html(why)}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational sizing only:
hourly model with a typical load, no battery ageing curve, no inverter or grid-connection
study (see DISCLAIMER).</i></p>
</body></html>"""


def build_solar_report(
    inp: SolarThermalInputs,
    d: SolarThermalDesign,
    findings: list[Finding],
    title: str = "Preliminary solar thermal sizing report",
    site_note: str = "",
    theme: str = "light",
) -> str:
    """HTML string with inputs, results, checks and the formulas of a solar thermal design."""
    look = _THEMES.get(theme, _THEMES["light"])
    colors = look["colors"]
    r, c = d.run, d.collector
    loads = ", ".join(x for x in (
        f"hot water {inp.dhw_litres_per_day:g} L/day at {inp.t_use_c:g} degC"
        if inp.dhw_litres_per_day > 0 else "",
        f"cooling {inp.cooling_kwh_per_year:,.0f} kWh/year" if inp.cooling_kwh_per_year > 0
        else "") if x)
    inputs = "".join([
        _row("Loads", loads),
        _row("Site", f"latitude {inp.latitude_deg:.1f}, {inp.irradiation_kwh_m2:,.0f} kWh/m2 on "
             f"the collector, air {inp.t_mean_c:g} degC +/- {inp.t_season_amp_c:g} K"),
        _row("Collector", f"{c.name}: eta0 {c.eta0:.2f}, a1 {c.a1:g}, a2 {c.a2:g}"),
        _row("Store / pipe losses", f"{inp.store_l_per_m2:g} L per m2 / {inp.loop_loss:.0%}"),
        _row("Cooling machine", (f"{SOLAR_CHILLERS[inp.chiller].name}: COP {inp.cop_nominal:.2f}, "
                                 f"drive {inp.t_drive_min_c:g}-{inp.t_drive_nominal_c:g} degC")
             if inp.cooling_kwh_per_year > 0 else "none"),
        _row("Costs", f"collector {c.cost_per_m2:,.0f} euro/m2, tank "
             f"{inp.store_cost_per_litre:g} euro/L, fixed {inp.fixed_cost:,.0f} euro, chiller "
             f"{inp.chiller_cost_per_kw:,.0f} euro/kW, O&M {inp.om_fraction:.1%}"),
        _row("Prices and finance", f"heat {inp.heat_price} euro/kWh, electricity "
             f"{inp.electricity_price} euro/kWh, discount {inp.discount_rate:.1%}, life "
             f"{inp.life_years:g} years"),
    ])
    rows = [
        _row("Collectors / tank", f"{d.area_m2:g} m2 / {d.store_litres:,.0f} L"
             + (f" / chiller {d.chiller_kw:.1f} kW" if d.chiller_kw > 0 else "")),
        _row("Heat from the collectors", f"{r.collector_kwh:,.0f} kWh/year "
             f"({d.yield_kwh_m2:,.0f} kWh of useful energy per m2)"),
    ]
    if r.heat_demand_kwh > 0:
        rows.append(_row("Hot water", f"{r.heat_solar_kwh:,.0f} of {r.heat_demand_kwh:,.0f} kWh "
                         f"from the sun ({r.heat_fraction:.0%})"))
    if r.cooling_demand_kwh > 0:
        rows.append(_row("Cooling", f"{r.cooling_solar_kwh:,.0f} of {r.cooling_demand_kwh:,.0f} "
                         f"kWh from the sun ({r.cooling_fraction:.0%}); hot water used "
                         f"{r.chiller_heat_kwh:,.0f} kWh"))
    rows += [
        _row("Overheating", f"{r.hours_stagnation} hours at 95 degC, {r.wasted_kwh:,.0f} kWh "
             "dumped"),
        _row("CAPEX / O&M", f"{d.capex:,.0f} euro / {d.om_per_year:,.0f} euro per year"),
        _row("Savings", f"{d.savings_per_year:,.0f} euro per year"),
        _row("Payback / NPV", f"{d.payback_years:.1f} years / {d.npv:,.0f} euro"),
        _row("Cost of useful solar energy (LCOH)", f"{d.lcoh:.3f} euro/kWh"),
        _row("CO2 avoided", f"{d.co2_avoided_t:,.2f} t per year"),
    ]
    results = "".join(rows)
    if d.cooling_options:
        results += _row("Cooling technologies", "; ".join(
            f"{o.name.split(' (')[0]}{' (main)' if o.is_main else ''}: "
            f"{o.cooling_fraction:.0%} of the cooling, COP {o.mean_cop:.2f}, NPV {o.npv:,.0f} euro"
            for o in d.cooling_options))
    why = "".join(
        explanation_html(key, solar_worked_example(key, inp, d), math=True)
        for key in SOLAR_TOPIC_ORDER
        if key in EXPLANATIONS
    )
    money = "repays itself" if d.npv >= 0 else "costs more than it saves over its life"
    what = ("hot water" if inp.cooling_kwh_per_year <= 0 else
            "cooling" if inp.dhw_litres_per_day <= 0 else "hot water and cooling")
    verdict = (f"<b>{d.area_m2:g} m2</b> of {c.name.lower()} collectors and a "
               f"{d.store_litres:,.0f} L tank give <b>{r.solar_fraction:.0%}</b> of your {what} "
               f"from the sun; the plant {money} (NPV {d.npv:,.0f} euro). "
               + _status_phrase(findings))
    glance = _glance([
        (f"{d.area_m2:g} m2", "of collectors"),
        (f"{r.solar_fraction:.0%}", "solar fraction"),
        (_energy(d.solar_useful_kwh), "useful solar energy per year"),
        (f"{d.co2_avoided_t:.1f} t", "CO2 avoided per year"),
    ], verdict, [
        (f"{d.lcoh:.3f} euro/kWh", "cost of solar energy (LCOH)"),
        (f"{d.payback_years:.1f} years" if d.payback_years < 1e3 else "never", "simple payback"),
        (f"{d.npv:,.0f} euro", "net present value"),
    ])
    charts_html = _charts_html(solar_charts(inp, d))
    checks_html = _checks_html(findings, colors)
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>In short</h2>{glance}
<h2>The numbers in pictures</h2>{charts_html}
<h2>Design checks</h2>{checks_html}
<h2>Results in detail</h2><table>{results}</table>
<h2>Your inputs</h2><table>{inputs}</table>
<h2>Method and formulas</h2>{why}{references_html(why)}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational sizing only:
hourly model with one mixed tank and a synthetic year, no detailed hydraulics, stratification,
frost protection or heat-rejection design (see DISCLAIMER).</i></p>
</body></html>"""


def build_hydro_report(
    inp: HydroInputs,
    d: HydroDesign,
    findings: list[Finding],
    title: str = "Preliminary hydropower sizing report",
    site_note: str = "",
    theme: str = "light",
) -> str:
    """HTML string with inputs, results, checks and the formulas of a run-of-river plant."""
    look = _THEMES.get(theme, _THEMES["light"])
    colors = look["colors"]
    inputs = "".join([
        _row("Gross head", f"{inp.gross_head_m:.1f} m"),
        _row("River flow", f"mean {inp.mean_flow_m3s:.2f} m3/s, Q95 {inp.q95_m3s:.2f} m3/s"),
        _row("Environmental flow", f"{inp.eco_flow_m3s:.2f} m3/s ({d.eco_flow_share:.0%} of the mean)"),
        _row("Design flow", f"exceeded {inp.design_exceedance:.0%} of the time"),
        _row("Penstock", f"{inp.penstock_length_m:.0f} m, roughness {inp.roughness_mm:.2f} mm, "
             f"local losses K = {inp.local_loss_k:.1f}"),
        _row("Operating losses", f"{inp.operating_losses:.0%} of the energy"),
        _row("Demand", f"{inp.annual_demand_kwh:,.0f} kWh/year" if inp.annual_demand_kwh > 0
             else "none: everything is sold"),
        _row("Prices", f"buy {inp.retail_price} euro/kWh, sell {inp.export_price} euro/kWh, "
             f"discount {inp.discount_rate:.1%}"),
        _row("Cost", f"{inp.capex_per_kw:,.0f} euro/kW, O&M {inp.om_fraction:.1%} of the CAPEX per "
             f"year, life {inp.life_years:.0f} years"),
    ])
    results = "".join([
        _row("Design flow", f"{d.design_flow_m3s:.2f} m3/s (river {d.river_flow_at_design_m3s:.2f} "
             f"m3/s minus the environmental flow)"),
        _row("Penstock", f"{d.penstock_diameter_m:.2f} m, {d.velocity_ms:.1f} m/s, loss "
             f"{d.head_loss_m:.2f} m"),
        _row("Net head", f"{d.net_head_m:.1f} m"),
        _row("Turbine", f"{d.turbine_name}, efficiency {d.turbine_eff:.2f}, generator "
             f"{d.generator_eff:.3f}; lowest flow {d.min_flow_m3s:.2f} m3/s"),
        _row("Rated power", f"{d.rated_kw:,.0f} kW"),
        _row("Energy per year", f"{d.energy_kwh:,.0f} kWh"),
        _row("Full-load hours / capacity factor", f"{d.full_load_hours:,.0f} h / "
             f"{d.capacity_factor:.0%}"),
        _row("Turbine at work", f"{d.hours_working:,.0f} h per year, {d.water_used_fraction:.0%} of "
             "the water of the river"),
        _row("CAPEX / O&M", f"{d.capex:,.0f} euro / {d.om_per_year:,.0f} euro per year"),
        _row("Cost of the energy (LCOE)", f"{d.lcoe:.3f} euro/kWh"),
        _row("Payback / NPV", f"{_payback(d.payback_years)} / {d.npv:,.0f} euro"),
        _row("CO2 avoided", f"{d.co2_avoided_t_per_year:,.0f} t per year"),
    ])
    why = "".join(
        explanation_html(key, hydro_worked_example(key, inp, d), math=True)
        for key in HYDRO_TOPIC_ORDER if key in EXPLANATIONS)
    status = _status_phrase(findings)
    verdict = (f"A <b>{d.rated_kw:,.0f} kW</b> plant ({d.turbine_name.split(' (')[0]} turbine, "
               f"{d.net_head_m:.0f} m of net head) gives {_energy(d.energy_kwh)} a year at about "
               f"<b>{d.lcoe:.3f} euro/kWh</b>, with a capacity factor of {d.capacity_factor:.0%}. "
               f"{status}")
    glance = _glance([
        (f"{d.rated_kw:,.0f} kW", "rated power"),
        (_energy(d.energy_kwh), "energy per year"),
        (f"{d.capacity_factor:.0%}", "capacity factor"),
        (f"{d.lcoe:.3f} euro/kWh", "cost of the energy (LCOE)"),
    ], verdict)
    charts_html = _charts_html(hydro_charts(inp, d))
    checks_html = _checks_html(findings, colors)
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>In short</h2>{glance}
<h2>The numbers in pictures</h2>{charts_html}
<h2>Design checks</h2>{checks_html}
<h2>Results in detail</h2><table>{results}</table>
<h2>Your inputs</h2><table>{inputs}</table>
<h2>Method and formulas</h2>{why}{references_html(why)}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational sizing only:
hydrology, environmental permit, water hammer, civil works and grid connection are not
studied (see DISCLAIMER).</i></p>
</body></html>"""


def build_geothermal_report(
    inp: GeothermalInputs,
    d: GeothermalDesign,
    findings: list[Finding],
    title: str = "Preliminary geothermal sizing report",
    site_note: str = "",
    theme: str = "light",
) -> str:
    """HTML string with inputs, results, checks and the formulas of a geothermal design."""
    look = _THEMES.get(theme, _THEMES["light"])
    colors = look["colors"]
    heat = d.pathway == "heat"
    common = [
        _row("Pathway", GEO_PATHWAYS[inp.pathway]),
        _row("Reservoir", f"{inp.reservoir_temp_c:.0f} degC, {inp.flow_per_well_kg_s:.0f} kg/s per "
             f"production well, gradient {inp.gradient_k_per_km:.0f} K/km"),
        _row("Pumps", f"{inp.pump_pressure_bar:.0f} bar, efficiency {inp.pump_efficiency:.2f}"),
    ]
    if heat:
        inputs = common + [
            _row("Heat demand", f"{inp.annual_heat_demand_kwh:,.0f} kWh/year, peak "
                 f"{inp.peak_heat_kw:,.0f} kW, coverage {inp.coverage:.0%}"),
            _row("Return temperature / exchanger", f"{inp.return_temp_c:.0f} degC / "
                 f"{inp.exchanger_efficiency:.2f}"),
            _row("Cost", f"{inp.drilling_eur_per_m:,.0f} euro/m of well, "
                 f"{inp.surface_eur_per_kw_th:,.0f} euro/kW of surface equipment, O&M "
                 f"{inp.om_fraction:.0%} of the CAPEX per year, life {inp.life_years:.0f} years"),
            _row("Value of the heat", f"{inp.heat_price_eur_per_kwh} euro/kWh"),
        ]
        results = [
            _row("Wells", f"{d.wells_pairs} pair(s), {d.depth_m:,.0f} m deep"),
            _row("Heat per pair", f"{d.heat_per_pair_kw:,.0f} kW"),
            _row("Plant power", f"{d.wells_pairs * d.heat_per_pair_kw:,.0f} kW "
                 f"({d.power_ratio:.0%} of the peak, load factor {d.load_factor:.2f})"),
            _row("Heat per year", f"{d.heat_kwh:,.0f} kWh ({d.coverage:.0%} of the demand)"),
            _row("Full-load hours", f"{d.full_load_hours:,.0f} h"),
            _row("Pumps / SPF", f"{d.pumps_kw:,.0f} kW / {d.spf:.0f}"),
            _row("CAPEX / O&M", f"{d.capex:,.0f} euro / {d.om_per_year:,.0f} euro per year"),
            _row("Cost of the heat", f"{d.lcoe:.3f} euro/kWh"),
            _row("Payback / NPV", f"{_payback(d.payback_years)} / {d.npv:,.0f} euro"),
            _row("CO2 avoided", f"{d.co2_avoided_t_per_year:,.0f} t per year"),
        ]
        verdict = (f"<b>{d.wells_pairs}</b> pair(s) of wells {d.depth_m / 1000:.1f} km deep deliver "
                   f"{_energy(d.heat_kwh)} of heat a year, <b>{d.coverage:.0%}</b> of your demand, "
                   f"at about <b>{d.lcoe:.3f} euro/kWh</b>. {_status_phrase(findings)}")
        glance = _glance([
            (f"{d.wells_pairs * d.heat_per_pair_kw:,.0f} kW", "heat power of the wells"),
            (_energy(d.heat_kwh), "heat per year"),
            (f"{d.coverage:.0%}", "of your heat covered"),
            (f"{d.lcoe:.3f} euro/kWh", "cost of the heat"),
        ], verdict)
    else:
        inputs = common + [
            _row("Electricity demand", f"{inp.annual_electricity_demand_kwh:,.0f} kWh/year, "
                 f"coverage {inp.coverage:.0%}; {inp.operating_hours:,.0f} h per year"),
            _row("Plant", f"{d.plant}; reinjection at {inp.reinjection_temp_c:.0f} degC"),
            _row("Cost", f"{inp.capex_per_kw_el:,.0f} euro per kW of net power, O&M "
                 f"{inp.om_fraction:.0%} of the CAPEX per year, life {inp.life_years:.0f} years"),
            _row("Prices", f"buy {inp.retail_price} euro/kWh, sell {inp.export_price} euro/kWh"),
        ]
        results = [
            _row("Plant", f"{d.plant}, {d.wells_pairs} pair(s) of wells {d.depth_m:,.0f} m deep"),
            _row("Efficiency", f"{d.efficiency:.1%} ({'cycle' if d.plant == 'binary' else 'utilization'})"),
            _row("Gross power", f"{d.gross_kw:,.0f} kW"),
            _row("Pumps", f"{d.pumps_kw:,.0f} kW"),
            _row("Net power", f"{d.net_kw:,.0f} kW"),
            _row("Electricity per year", f"{d.electricity_kwh:,.0f} kWh ({d.coverage:.0%} of the demand)"),
            _row("CAPEX / O&M", f"{d.capex:,.0f} euro / {d.om_per_year:,.0f} euro per year"),
            _row("Cost of the electricity", f"{d.lcoe:.3f} euro/kWh"),
            _row("Payback / NPV", f"{_payback(d.payback_years)} / {d.npv:,.0f} euro"),
            _row("CO2 avoided", f"{d.co2_avoided_t_per_year:,.0f} t per year"),
        ]
        verdict = (f"A {d.plant} plant of <b>{d.net_kw:,.0f} kW</b> (net) on {d.wells_pairs} pair(s) "
                   f"of wells gives {_energy(d.electricity_kwh)} a year, <b>{d.coverage:.0%}</b> "
                   f"of your demand, at about <b>{d.lcoe:.3f} euro/kWh</b>. "
                   f"{_status_phrase(findings)}")
        glance = _glance([
            (f"{d.net_kw:,.0f} kW", "net electric power"),
            (_energy(d.electricity_kwh), "electricity per year"),
            (f"{d.coverage:.0%}", "of your demand covered"),
            (f"{d.lcoe:.3f} euro/kWh", "cost of the electricity"),
        ], verdict)
    why = "".join(
        explanation_html(key, geothermal_worked_example(key, inp, d), math=True)
        for key in geothermal_topics(d.pathway) if key in EXPLANATIONS)
    charts_html = _charts_html(geothermal_charts(inp, d))
    checks_html = _checks_html(findings, colors)
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>In short</h2>{glance}
<h2>The numbers in pictures</h2>{charts_html}
<h2>Design checks</h2>{checks_html}
<h2>Results in detail</h2><table>{"".join(results)}</table>
<h2>Your inputs</h2><table>{"".join(inputs)}</table>
<h2>Method and formulas</h2>{why}{references_html(why)}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational sizing only:
the resource is assumed to exist as described; exploration, reservoir modelling, scaling,
permits and drilling risk are not covered (see DISCLAIMER).</i></p>
</body></html>"""
