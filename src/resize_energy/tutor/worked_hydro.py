"""Worked examples of the hydropower topics, with the user's own numbers."""

from __future__ import annotations

import math

from resize_energy.core import hydro as hy
from resize_energy.core.hydro_design import HydroDesign, HydroInputs


def hydro_worked_example(key: str, inp: HydroInputs, d: HydroDesign) -> str | None:
    if key == "hydro.fdc":
        return (
            f"ln(Q_mean / Q95) = ln({inp.mean_flow_m3s:.2f} / {inp.q95_m3s:.2f}) = "
            f"{math.log(inp.mean_flow_m3s / inp.q95_m3s):.3f}\n"
            f"sigma = -1.645 + sqrt(1.645^2 + 2 x {math.log(inp.mean_flow_m3s / inp.q95_m3s):.3f}) = "
            f"{d.sigma:.3f};  mu = {d.mu:.3f}\n"
            f"Median flow = exp(mu) = {math.exp(d.mu):.2f} m3/s"
        )
    if key == "hydro.eco_flow":
        return (
            f"River flow exceeded {inp.design_exceedance:.0%} of the time: "
            f"{d.river_flow_at_design_m3s:.2f} m3/s\n"
            f"Environmental flow: {inp.eco_flow_m3s:.2f} m3/s ({d.eco_flow_share:.0%} of the mean "
            f"flow)\nLeft for the turbine: {d.river_flow_at_design_m3s:.2f} - "
            f"{inp.eco_flow_m3s:.2f} = {d.design_flow_m3s:.2f} m3/s"
        )
    if key == "hydro.design_flow":
        return (
            f"Q_design = {d.design_flow_m3s:.2f} m3/s, exceeded {inp.design_exceedance:.0%} of "
            f"the time in the river\nRated power {d.rated_kw:,.0f} kW; energy {d.energy_kwh:,.0f} "
            f"kWh\nCapacity factor = {d.energy_kwh:,.0f} / ({d.rated_kw:,.0f} x 8760) = "
            f"{d.capacity_factor:.1%}  ({d.full_load_hours:,.0f} full-load hours)"
        )
    if key == "hydro.power":
        return (
            f"P = 1000 x 9.81 x {d.design_flow_m3s:.2f} x {d.net_head_m:.1f} x "
            f"{d.turbine_eff:.2f} x {d.generator_eff:.3f} / 1000 = {d.rated_kw:,.0f} kW\n"
            f"(gross head {inp.gross_head_m:.1f} m, net head {d.net_head_m:.1f} m)"
        )
    if key == "hydro.penstock":
        return (
            f"D = sqrt(4 x {d.design_flow_m3s:.2f} / (pi x {d.velocity_ms:.1f})) = "
            f"{d.penstock_diameter_m:.2f} m\n"
            f"Loss at the design flow = (f x {inp.penstock_length_m:.0f} / "
            f"{d.penstock_diameter_m:.2f} + {inp.local_loss_k:.1f}) x v^2 / 2g = "
            f"{d.head_loss_m:.2f} m  ({d.head_loss_m / inp.gross_head_m:.1%} of the head)"
        )
    if key == "hydro.turbine":
        t = hy.TURBINES[d.turbine_key]
        return (
            f"Net head {d.net_head_m:.1f} m, design flow {d.design_flow_m3s:.2f} m3/s -> "
            f"{d.turbine_name} ({t.head_min:.0f}-{t.head_max:.0f} m)\n"
            f"Lowest flow = {t.min_flow_fraction:.0%} x {d.design_flow_m3s:.2f} = "
            f"{d.min_flow_m3s:.2f} m3/s; the turbine works {d.hours_working:,.0f} h per year"
        )
    if key == "hydro.energy":
        return (
            f"Hours at work: {d.hours_working:,.0f} of 8760; water through the turbine: "
            f"{d.water_used_fraction:.0%} of the river\n"
            f"E = {d.energy_kwh / (1 - inp.operating_losses):,.0f} x (1 - {inp.operating_losses:.2f})"
            f" = {d.energy_kwh:,.0f} kWh per year"
        )
    if key == "hydro.economics":
        return (
            f"CAPEX = {d.rated_kw:,.0f} kW x {inp.capex_per_kw:,.0f} = {d.capex:,.0f} euro\n"
            f"O&M = {inp.om_fraction:.1%} x CAPEX = {d.om_per_year:,.0f} euro per year\n"
            f"LCOE = {d.lcoe:.3f} euro/kWh;  payback "
            f"{'more than the life' if d.payback_years > inp.life_years else f'{d.payback_years:.1f} years'}"
            f";  NPV = {d.npv:,.0f} euro"
        )
    if key == "hydro.co2":
        return (
            f"{d.energy_kwh:,.0f} kWh x ({inp.grid_ef:.3f} - {inp.lifecycle_g_per_kwh / 1000:.3f}) "
            f"/ 1000 = {d.co2_avoided_t_per_year:,.0f} t CO2 per year"
        )
    return None
