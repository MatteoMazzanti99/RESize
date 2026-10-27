"""HTML report of a borehole-field (ground-source heat pump) design."""

from __future__ import annotations

from html import escape

from resize_energy import __version__
from resize_energy.core.bhe_design import BheDesign, BheInputs, annualised_cost
from resize_energy.report.charts_bhe import bhe_charts
from resize_energy.report.html_report import (
    _THEMES,
    _charts_html,
    _checks_html,
    _glance,
    _row,
    _status_phrase,
)
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.explanations_bhe import BHE_TOPIC_ORDER
from resize_energy.tutor.sources import references_html
from resize_energy.tutor.why_html import explanation_html
from resize_energy.tutor.worked_bhe import bhe_worked_example


def build_bhe_report(
    inp: BheInputs,
    d: BheDesign,
    findings: list[Finding],
    title: str = "Preliminary borehole field sizing report",
    site_note: str = "",
    theme: str = "light",
) -> str:
    look = _THEMES.get(theme, _THEMES["light"])
    colors = look["colors"]
    inputs = [
        _row("Heating", f"{inp.heating_kwh_per_year:,.0f} kWh/year, peak {inp.heating_peak_kw:,.0f} kW; "
             f"COP {inp.cop_design} (seasonal {inp.cop_seasonal})"),
        _row("Cooling", f"{inp.cooling_kwh_per_year:,.0f} kWh/year, peak {inp.cooling_peak_kw:,.0f} kW; "
             f"EER {inp.eer_design} (seasonal {inp.eer_seasonal})"),
        _row("Fluid temperatures", f"heating {inp.fluid_in_heating_c:.0f} / {inp.fluid_out_heating_c:.0f} "
             f"degC, cooling {inp.fluid_in_cooling_c:.0f} / {inp.fluid_out_cooling_c:.0f} degC"),
        _row("Ground", f"{inp.ground_temp_c} degC, lambda {inp.ground_conductivity} W/(m K), rho "
             f"{inp.ground_density:,.0f} kg/m3, cp {inp.ground_cp:,.0f} J/(kg K)"),
        _row("Borehole", f"diameter {inp.borehole_diameter_mm:.0f} mm, pipes "
             f"{inp.pipe_outer_mm}/{inp.pipe_inner_mm} mm at {inp.pipe_spacing_mm} mm, grout "
             f"{inp.grout_conductivity} W/(m K), F_sc {inp.short_circuit_factor}"),
        _row("Field", f"spacing {inp.spacing_m} m, maximum depth {inp.max_depth_m:,.0f} m, "
             f"penalty method {inp.penalty_method}"),
        _row("Cost", f"{inp.drilling_eur_per_m:,.0f} euro per metre, O&M {inp.om_fraction:.1%} of "
             f"the CAPEX per year, life {inp.life_years:.0f} years, discount rate "
             f"{inp.discount_rate:.1%}"),
    ]
    results = [
        _row("Length for heating / cooling", f"{d.length_heating_m:,.0f} m / {d.length_cooling_m:,.0f} m"),
        _row("Governing case", f"{d.governing} (without the penalty: {d.length_first_m:,.0f} m)"),
        _row("Total length", f"{d.total_length_m:,.0f} m"),
        _row("Boreholes", f"{d.boreholes} x {d.depth_m:,.0f} m ({d.rows} rows x {d.columns} columns)"),
        _row("Area of the field", f"{d.area_needed_m2:,.0f} m2"
             + ("" if d.fits_area is None else (" (fits)" if d.fits_area else " (does NOT fit)"))),
        _row("Temperature penalty", f"{d.penalty_c:+.2f} K"),
        _row("Borehole resistance", f"R_b = {d.r_b:.3f} m K/W (pipes {d.r_pp:.3f}, grout {d.r_gr:.3f})"),
        _row("Ground resistances", f"R_ga = {d.r_ga:.3f}, R_gm = {d.r_gm:.3f}, R_gd = {d.r_gd:.3f} m K/W"),
        _row("Flow per borehole", f"{d.flow_per_borehole_kg_s:.2f} kg/s, Re = {d.reynolds:,.0f}"),
        _row("Net yearly load on the ground", f"{d.q_annual_w / 1000:+.1f} kW (positive: heat taken out)"),
        _row("Peak load per metre", f"{d.peak_w_per_m:.0f} W/m"),
        _row("CAPEX / O&M", f"{d.capex:,.0f} euro / {d.om_per_year:,.0f} euro per year"),
        _row("Annual cost of the field", f"{annualised_cost(d, inp):,.0f} euro per year"),
    ]
    verdict = (f"You need <b>{d.total_length_m:,.0f} m</b> of borehole: <b>{d.boreholes}</b> "
               f"boreholes of <b>{d.depth_m:,.0f} m</b>, governed by {d.governing}. "
               f"{_status_phrase(findings)}")
    glance = _glance([
        (f"{d.total_length_m:,.0f} m", "of borehole in total"),
        (f"{d.boreholes} x {d.depth_m:,.0f} m", "boreholes"),
        (f"{d.area_needed_m2:,.0f} m2", "of land"),
        (f"{d.capex:,.0f} euro", "drilling cost"),
    ], verdict)
    why = "".join(explanation_html(key, bhe_worked_example(key, inp, d), math=True)
                  for key in BHE_TOPIC_ORDER if key in EXPLANATIONS)
    charts_html = _charts_html(bhe_charts(inp, d))
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
the ground is uniform, groundwater flow and the hourly behaviour of the heat pump are not
modelled; confirm with a thermal response test and a dynamic simulation (see DISCLAIMER).</i></p>
</body></html>"""
