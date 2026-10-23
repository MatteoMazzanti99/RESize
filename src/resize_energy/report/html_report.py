"""Self-contained HTML report of a PV design (the GUI turns it into a PDF)."""

from __future__ import annotations

from html import escape

from resize_energy import __version__
from resize_energy.core.biomass_design import PATHWAYS, BiomassDesign, BiomassInputs
from resize_energy.core.comparison import ComparisonInputs, ComparisonResult
from resize_energy.core.pv_design import PVDesign, PVInputs
from resize_energy.core.wind_design import WindDesign, WindInputs
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.explanations import EXPLANATIONS, TOPIC_ORDER
from resize_energy.tutor.explanations_biomass import topics_for
from resize_energy.tutor.explanations_compare import COMPARE_TOPIC_ORDER
from resize_energy.tutor.explanations_wind import WIND_TOPIC_ORDER
from resize_energy.tutor.why_html import explanation_html
from resize_energy.tutor.worked import worked_example
from resize_energy.tutor.worked_biomass import biomass_worked_example
from resize_energy.tutor.worked_compare import compare_worked_example
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


def _years(value: float) -> str:
    return "never" if value == float("inf") else f"{value:.1f}"


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


def build_comparison_report(
    inp: ComparisonInputs,
    r: ComparisonResult,
    findings: list[Finding],
    title: str = "Technology comparison: photovoltaic vs wind",
    site_note: str = "",
    theme: str = "light",
) -> str:
    """HTML with the side-by-side figures, the checks and the formulas of the comparison."""
    look = _THEMES.get(theme, _THEMES["light"])
    colors = look["colors"]
    c = inp.costs
    a, b = r.pv, r.wind

    def two(label: str, fa: str, fb: str) -> str:
        return (f"<tr><td>{escape(label)}</td><td align=\"right\"><b>{escape(fa)}</b></td>"
                f"<td align=\"right\"><b>{escape(fb)}</b></td></tr>")

    table = "".join([
        two("Installed power", f"{a.installed_kw:,.0f} kW(p)", f"{b.installed_kw:,.0f} kW"),
        two("Energy per year", f"{a.energy_kwh:,.0f} kWh", f"{b.energy_kwh:,.0f} kWh"),
        two("Demand covered", f"{a.coverage:.0%}", f"{b.coverage:.0%}"),
        two("Full-load hours", f"{a.full_load_hours:,.0f} h", f"{b.full_load_hours:,.0f} h"),
        two("Investment (CAPEX)", f"{a.capex_eur:,.0f} euro", f"{b.capex_eur:,.0f} euro"),
        two("O&M per year", f"{a.om_eur_per_year:,.0f} euro", f"{b.om_eur_per_year:,.0f} euro"),
        two("LCOE", f"{a.lcoe_eur_per_kwh:.3f} euro/kWh", f"{b.lcoe_eur_per_kwh:.3f} euro/kWh"),
        two("Savings per year", f"{a.savings_eur_per_year:,.0f} euro",
            f"{b.savings_eur_per_year:,.0f} euro"),
        two("Simple payback", f"{_years(a.payback_years)} years", f"{_years(b.payback_years)} years"),
        two("Discounted payback", f"{_years(a.discounted_payback_years)} years",
            f"{_years(b.discounted_payback_years)} years"),
        two("Net present value", f"{a.npv_eur:,.0f} euro", f"{b.npv_eur:,.0f} euro"),
        two("CO2 avoided per year", f"{a.co2_avoided_t_per_year:,.0f} t",
            f"{b.co2_avoided_t_per_year:,.0f} t"),
        two("CO2 avoided over the lifetime", f"{a.co2_avoided_lifetime_t:,.0f} t",
            f"{b.co2_avoided_lifetime_t:,.0f} t"),
    ])
    pv_color, wind_color = ("#0A7452", "#1F5FBF")

    bars = "".join([
        _bar_rows("Cost of energy, euro/kWh (lower is better)", [
            (f"PV {a.lcoe_eur_per_kwh:.3f}", a.lcoe_eur_per_kwh, pv_color),
            (f"Wind {b.lcoe_eur_per_kwh:.3f}", b.lcoe_eur_per_kwh, wind_color)]),
        _bar_rows("Simple payback, years (lower is better)", [
            (f"PV {_years(a.payback_years)}", a.payback_years, pv_color),
            (f"Wind {_years(b.payback_years)}", b.payback_years, wind_color)]),
        _bar_rows("CO2 avoided per year, tonnes (higher is better)", [
            (f"PV {a.co2_avoided_t_per_year:,.0f}", a.co2_avoided_t_per_year, pv_color),
            (f"Wind {b.co2_avoided_t_per_year:,.0f}", b.co2_avoided_t_per_year, wind_color)]),
    ])
    inputs_rows = "".join([
        _row("Annual electricity demand / coverage",
             f"{inp.annual_demand_kwh:,.0f} kWh / {inp.coverage:.0%}"),
        _row("Irradiation / performance ratio",
             f"{inp.annual_irradiation_kwh_m2:,.0f} kWh/m2 / {inp.performance_ratio:.2f}"),
        _row("Wind speed / turbine",
             f"{inp.wind.mean_speed_ref_ms:.2f} m/s at {inp.wind.ref_height_m:.0f} m / "
             f"{inp.wind.turbine.name} ({inp.wind.turbine.rated_power_kw:,.0f} kW)"),
        _row("PV cost", f"{c.pv_capex_eur_per_kwp:,.0f} euro/kWp + {c.pv_om_eur_per_kwp_year:,.0f}"
             f" euro/kWp/year, {c.pv_lifetime_years:.0f} years, {c.pv_lifecycle_g_per_kwh:.0f} g/kWh"),
        _row("Wind cost", f"{c.wind_capex_eur_per_kw:,.0f} euro/kW + {c.wind_om_eur_per_kw_year:,.0f}"
             f" euro/kW/year, {c.wind_lifetime_years:.0f} years, "
             f"{c.wind_lifecycle_g_per_kwh:.0f} g/kWh"),
        _row("Discount rate", f"{c.discount_rate:.1%}"),
        _row("Retail / export price",
             f"{c.retail_price_eur_per_kwh:.3f} / {c.export_price_eur_per_kwh:.3f} euro/kWh"),
        _row("Grid emission factor", f"{c.grid_kg_co2_per_kwh:.3f} kg CO2/kWh"),
    ])
    verdict = (
        f"<ul><li>Lowest cost of energy (LCOE): <b>{escape(r.lowest_lcoe)}</b></li>"
        f"<li>Fastest simple payback: <b>{escape(r.fastest_payback)}</b></li>"
        f"<li>Highest net present value: <b>{escape(r.highest_npv)}</b></li>"
        f"<li>Most CO2 avoided per year: <b>{escape(r.most_co2)}</b></li></ul>")
    checks = "".join(
        f'<li><span style="color:{colors[f.severity]}"><b>[{_LABELS[f.severity]}]</b></span> '
        f"{escape(f.message)}</li>"
        for f in findings
    )
    why = "".join(
        explanation_html(key, compare_worked_example(key, inp, r))
        for key in COMPARE_TOPIC_ORDER
        if key in EXPLANATIONS
    )
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>1. Comparison</h2>
<table cellpadding="3"><tr><td></td><td align="right"><b>Photovoltaic</b></td>
<td align="right"><b>Wind</b></td></tr>{table}</table>
<h2>2. Which is better, and for what?</h2>{verdict}
<table>{bars}</table>
<h2>3. Inputs and assumptions</h2><table>{inputs_rows}</table>
<h2>4. Checks</h2><ul>{checks}</ul>
<h2>5. Method and formulas</h2>{why}
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
    checks = "".join(
        f'<li><span style="color:{colors[x.severity]}"><b>[{_LABELS[x.severity]}]</b></span> '
        f"{escape(x.message)}</li>"
        for x in findings
    )
    why = "".join(
        explanation_html(key, biomass_worked_example(key, inp, d))
        for key in topics_for(d.pathway)
        if key in EXPLANATIONS
    )
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>1. Inputs</h2><table>{"".join(inputs)}</table>
<h2>2. Results</h2><table>{"".join(results)}</table>
<h2>3. Design checks</h2><ul>{checks}</ul>
<h2>4. Method and formulas</h2>{why}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational sizing only:
fuel quality, supply contracts, emissions permits and detailed design are not covered
(see DISCLAIMER).</i></p>
</body></html>"""
