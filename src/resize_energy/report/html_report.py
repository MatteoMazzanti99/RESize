"""Self-contained HTML report of a PV design (the GUI turns it into a PDF)."""

from __future__ import annotations

from html import escape

from resize_energy import __version__
from resize_energy.core.biomass_design import PATHWAYS, BiomassDesign, BiomassInputs
from resize_energy.core.comparison import ComparisonInputs, ComparisonResult
from resize_energy.core.hydrogen_design import MODES, HydrogenDesign, HydrogenInputs
from resize_energy.core.pv_design import PVDesign, PVInputs
from resize_energy.core.wind_design import WindDesign, WindInputs
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.explanations import EXPLANATIONS, TOPIC_ORDER
from resize_energy.tutor.explanations_biomass import topics_for
from resize_energy.tutor.explanations_compare import COMPARE_TOPIC_ORDER
from resize_energy.tutor.explanations_hydrogen import HYDROGEN_TOPIC_ORDER
from resize_energy.tutor.explanations_wind import WIND_TOPIC_ORDER
from resize_energy.tutor.why_html import explanation_html
from resize_energy.tutor.worked import worked_example
from resize_energy.tutor.worked_biomass import biomass_worked_example
from resize_energy.tutor.worked_compare import compare_worked_example
from resize_energy.tutor.worked_hydrogen import hydrogen_worked_example
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
    bars = "".join([
        _bar_rows("Cost of energy, euro/kWh (lower is better)", [
            (f"{_TECH_SHORT[t.key]} {t.lcoe_eur_per_kwh:.3f}", t.lcoe_eur_per_kwh,
             _TECH_COLORS[t.key]) for t in techs]),
        _bar_rows("Simple payback, years (lower is better)", [
            (f"{_TECH_SHORT[t.key]} {_years(t.payback_years)}", t.payback_years,
             _TECH_COLORS[t.key]) for t in techs]),
        _bar_rows("CO2 avoided per year, tonnes (higher is better)", [
            (f"{_TECH_SHORT[t.key]} {t.co2_avoided_t_per_year:,.0f}",
             max(0.0, t.co2_avoided_t_per_year), _TECH_COLORS[t.key]) for t in techs]),
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
<table cellpadding="3"><tr><td></td>{head}</tr>{table}</table>
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
        _row("Storage autonomy", f"{inp.storage_days:.0f} days"),
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
    checks = "".join(
        f'<li><span style="color:{colors[x.severity]}"><b>[{_LABELS[x.severity]}]</b></span> '
        f"{escape(x.message)}</li>"
        for x in findings
    )
    why = "".join(
        explanation_html(key, hydrogen_worked_example(key, inp, d))
        for key in HYDROGEN_TOPIC_ORDER
        if key in EXPLANATIONS
    )
    note = f"<p>{escape(site_note)}</p>" if site_note else ""
    return f"""<html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
{look["css"]}
</style></head><body>
<h1>{escape(title)}</h1>{note}
<h2>1. Inputs</h2><table>{inputs}</table>
<h2>2. Results</h2><table>{results}</table>
<h2>3. Where the cost comes from</h2><table cellpadding="2">{bars}</table>
<h2>4. Design checks</h2><ul>{checks}</ul>
<h2>5. Method and formulas</h2>{why}
<hr><p><i>Generated by RESize {escape(__version__)}. Preliminary and educational sizing only:
no dynamic model of the electrolyser, no safety, permitting or grid-connection study
(see DISCLAIMER).</i></p>
</body></html>"""
