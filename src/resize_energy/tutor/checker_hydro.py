"""Sanity checks of a hydropower design (deterministic, offline)."""

from __future__ import annotations

from resize_energy.core import hydro as hy
from resize_energy.core.hydro_design import HydroDesign, HydroInputs
from resize_energy.tutor.checker import Finding


def check_hydro_design(inp: HydroInputs, d: HydroDesign) -> list[Finding]:
    out: list[Finding] = []
    t = hy.TURBINES[d.turbine_key]
    if not t.head_min <= d.net_head_m <= t.head_max:
        out.append(Finding(
            "warning", "turbine_head",
            f"The net head of {d.net_head_m:.0f} m is outside the usual range of a "
            f"{d.turbine_name} ({t.head_min:.0f}-{t.head_max:.0f} m). Choose another type or "
            "ask the maker.", "hydro.turbine"))
    if d.head_loss_m / inp.gross_head_m > 0.10:
        out.append(Finding(
            "warning", "head_loss",
            f"The penstock loses {d.head_loss_m / inp.gross_head_m:.0%} of the head. Use a wider "
            "pipe or a lower velocity: a 5-10 % loss is usual.", "hydro.penstock"))
    if d.velocity_ms > 5.0:
        out.append(Finding(
            "warning", "velocity_high",
            f"The water runs at {d.velocity_ms:.1f} m/s in the penstock: erosion, noise and "
            "water hammer grow quickly above 4-5 m/s.", "hydro.penstock"))
    if d.eco_flow_share < 0.10:
        out.append(Finding(
            "warning", "eco_flow_low",
            f"The environmental flow is {d.eco_flow_share:.0%} of the mean flow: below the "
            "10 % that is usually taken as a bare minimum. Check the rule of your river basin: "
            "it can make the permit impossible.", "hydro.eco_flow"))
    elif d.eco_flow_share > 0.5:
        out.append(Finding(
            "info", "eco_flow_high",
            f"The environmental flow is {d.eco_flow_share:.0%} of the mean flow: the river is "
            "well protected but little water is left for the turbine.", "hydro.eco_flow"))
    if d.capacity_factor < 0.30:
        out.append(Finding(
            "warning", "capacity_factor",
            f"Capacity factor {d.capacity_factor:.0%}: the machine is large for this river and "
            "idle most of the year. Raise the design exceedance (a smaller design flow).",
            "hydro.design_flow"))
    elif d.capacity_factor > 0.75:
        out.append(Finding(
            "info", "capacity_factor_high",
            f"Capacity factor {d.capacity_factor:.0%}: the turbine is small and the river "
            "often carries more water than it takes. A larger design flow would produce more "
            "energy.", "hydro.design_flow"))
    if inp.design_exceedance > 0.60:
        out.append(Finding(
            "info", "design_flow_small",
            f"The design flow is available {inp.design_exceedance:.0%} of the time: most of "
            "the water in the river goes by the turbine.", "hydro.design_flow"))
    if inp.mean_flow_m3s > 0 and inp.mean_flow_m3s / inp.q95_m3s > 15:
        out.append(Finding(
            "warning", "flashy",
            f"Mean flow / Q95 = {inp.mean_flow_m3s / inp.q95_m3s:.0f}: a very uneven river. "
            "The log-normal curve is a poor model for it: use measured daily flows.",
            "hydro.fdc"))
    if d.lcoe > inp.export_price and inp.annual_demand_kwh <= 0:
        out.append(Finding(
            "warning", "lcoe_high",
            f"The energy costs {d.lcoe:.3f} euro/kWh and is sold at {inp.export_price:.3f}: "
            "the plant does not pay for itself at these prices.", "hydro.economics"))
    out.append(Finding(
        "info", "annual_balance",
        "A typical year of flows and a constant efficiency: no dry years, floods, ice, water "
        "hammer or reservoir are modelled.", None))
    if not any(f.severity in ("warning", "error") for f in out):
        out.insert(0, Finding("ok", "design_ok", "No problem found with the main design rules.",
                              None))
    return out
