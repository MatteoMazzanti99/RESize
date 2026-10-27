"""Sanity checks of a borehole-field design (deterministic, offline)."""

from __future__ import annotations

from resize_energy.core.bhe_design import BheDesign, BheInputs
from resize_energy.tutor.checker import Finding


def check_bhe_design(inp: BheInputs, d: BheDesign) -> list[Finding]:
    out: list[Finding] = []
    if d.r_b > 0.20:
        out.append(Finding(
            "warning", "rb_high",
            f"The borehole resistance is {d.r_b:.2f} m K/W, above the usual 0.08-0.15: a better "
            "grout, a turbulent flow or a larger distance between the pipes shortens the field.",
            "bhe.borehole"))
    if d.reynolds and d.reynolds < 2300:
        out.append(Finding(
            "warning", "laminar",
            f"The flow in the pipes is laminar (Re = {d.reynolds:,.0f}): the film of fluid "
            "resists the heat much more than in turbulent flow.", "bhe.borehole"))
    if inp.spacing_m < 5.0:
        out.append(Finding(
            "warning", "spacing_close",
            f"Boreholes {inp.spacing_m:.1f} m apart interfere strongly: 6 m or more is the "
            "usual choice.", "bhe.penalty"))
    if d.peak_w_per_m > 80 or d.peak_w_per_m < 15:
        out.append(Finding(
            "warning", "w_per_m",
            f"{d.peak_w_per_m:.0f} W per metre at the peak is far from the usual 30-60 W/m of "
            "borehole: check the loads, the temperatures and the ground conductivity.",
            "bhe.length"))
    balance = abs(d.q_annual_w) * 8.76 / max(d.ground_extracted_kwh, d.ground_injected_kwh, 1.0)
    if balance > 0.15:
        out.append(Finding(
            "warning" if balance > 0.30 else "info", "imbalance",
            f"Over the year the ground gets {'less' if d.q_annual_w > 0 else 'more'} heat than "
            f"it gives ({abs(d.q_annual_w) / 1000:.1f} kW on average): the ground temperature "
            "drifts over the years and the penalty lengthens the field. Balance heating and "
            "cooling (for example by free cooling or a second source) if you can.", "bhe.loads"))
    if d.depth_m > 150.0:
        out.append(Finding(
            "info", "depth_authorisation",
            f"Boreholes of {d.depth_m:,.0f} m: in several regions the simplified procedure stops "
            "at 100-150 m, and deeper ones need a full authorisation.", "bhe.field"))
    if d.fits_area is False:
        out.append(Finding(
            "warning", "area",
            f"The field needs {d.area_needed_m2:,.0f} m2 but {inp.available_area_m2:,.0f} m2 are "
            "available.", "bhe.field"))
    if d.penalty_c and abs(d.penalty_c) > 3.0:
        out.append(Finding(
            "warning", "penalty_large",
            f"The temperature penalty of {d.penalty_c:+.1f} K is large: the field works against "
            "a ground that has drifted by several degrees.", "bhe.penalty"))
    if inp.fluid_in_heating_c < 0:
        out.append(Finding(
            "info", "freezing",
            "A fluid below 0 degC needs antifreeze and a heat pump rated for it.", "bhe.length"))
    for message in d.warnings:
        if "did not settle" in message:
            out.append(Finding("warning", "no_convergence", message, "bhe.penalty"))
    out.append(Finding(
        "info", "no_groundwater",
        "Groundwater flow, layered ground and the hourly behaviour of the heat pump are not "
        "modelled: for a large field use a dynamic simulation and a thermal response test.",
        None))
    if not any(f.severity in ("warning", "error") for f in out):
        out.insert(0, Finding("ok", "design_ok", "No problem found with the main design rules.",
                              None))
    return out
