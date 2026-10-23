"""Worked examples of the wind topics, with the user's own numbers."""

from __future__ import annotations

import math

from resize_energy.core import wind
from resize_energy.core.wind_design import WindDesign, WindInputs


def wind_worked_example(key: str, inp: WindInputs, d: WindDesign) -> str | None:
    """Plain-text substitution of the user's values into the formula, or None if unknown."""
    t = inp.turbine
    k = inp.weibull_k

    if key == "wind.resource":
        return (
            f"v_mean = {inp.mean_speed_ref_ms:.2f} m/s at {inp.ref_height_m:.0f} m\n"
            f"Power in the wind at that speed = 0.5 x 1.225 x {inp.mean_speed_ref_ms:.2f}^3 = "
            f"{wind.wind_power_density_w_m2(1.225, inp.mean_speed_ref_ms):.0f} W/m2"
        )
    if key == "wind.weibull":
        gamma = math.gamma(1 + 1 / k)
        return (
            f"k = {k:.2f}  ->  Gamma(1 + 1/k) = {gamma:.4f}\n"
            f"A = v_mean / Gamma = {d.mean_speed_hub_ms:.2f} / {gamma:.4f} = "
            f"{d.weibull_scale_ms:.2f} m/s (at hub height)"
        )
    if key == "wind.shear":
        return (
            f"v({t.hub_height_m:.0f} m) = {inp.mean_speed_ref_ms:.2f} x "
            f"({t.hub_height_m:.0f} / {inp.ref_height_m:.0f})^{inp.shear_alpha:.2f} = "
            f"{d.mean_speed_hub_ms:.2f} m/s"
        )
    if key == "wind.air_density":
        return (
            f"z = {inp.elevation_m:.0f} m, T = {inp.temperature_c:.0f} degC\n"
            f"rho = {d.air_density:.3f} kg/m3 ({d.air_density / wind.RHO_STANDARD - 1:+.1%} "
            "vs 1.225 standard)"
        )
    if key == "wind.power_curve":
        v_mid = 0.5 * (t.cut_in_ms + t.rated_speed_ms)
        p_mid = wind.generic_power_kw(v_mid, t.rated_power_kw, t.cut_in_ms, t.rated_speed_ms,
                                      t.cut_out_ms, d.air_density)
        return (
            f"Cut-in {t.cut_in_ms:.1f} m/s, rated {t.rated_speed_ms:.1f} m/s "
            f"({t.rated_power_kw:,.0f} kW), cut-out {t.cut_out_ms:.1f} m/s\n"
            f"Example: at {v_mid:.1f} m/s the turbine gives {p_mid:,.0f} kW at your density"
        )
    if key == "wind.cp_betz":
        return (
            f"Swept area = pi x ({t.rotor_diameter_m:.0f}/2)^2 = {d.swept_area_m2:,.0f} m2\n"
            f"Specific power = {t.rated_power_kw * 1000:,.0f} W / {d.swept_area_m2:,.0f} m2 = "
            f"{d.specific_power_w_m2:.0f} W/m2\n"
            f"Cp at rated = {t.rated_power_kw * 1000:,.0f} / (0.5 x {d.air_density:.3f} x "
            f"{d.swept_area_m2:,.0f} x {t.rated_speed_ms:.1f}^3) = {d.cp_rated:.2f}  "
            f"(Betz limit 0.59)"
        )
    if key == "wind.annual_energy":
        return (
            f"Weibull k = {k:.2f}, A = {d.weibull_scale_ms:.2f} m/s, rho = {d.air_density:.3f}\n"
            f"Gross energy per turbine = {d.gross_energy_per_turbine_kwh:,.0f} kWh/year"
        )
    if key == "wind.losses":
        return (
            f"E_net = {d.gross_energy_per_turbine_kwh:,.0f} x {inp.availability:.2f} x "
            f"(1 - {inp.other_losses:.2f}) = {d.net_energy_per_turbine_kwh:,.0f} kWh/year"
        )
    if key == "wind.capacity_factor":
        return (
            f"CF = {d.net_energy_per_turbine_kwh:,.0f} / ({t.rated_power_kw:,.0f} x 8760) = "
            f"{d.capacity_factor_net:.1%}  (gross {d.capacity_factor_gross:.1%})\n"
            f"Full-load hours = {d.full_load_hours_net:,.0f} h"
        )
    if key == "wind.number_of_turbines":
        return (
            f"N = ceil({inp.coverage:.0%} x {inp.annual_demand_kwh:,.0f} / "
            f"{d.net_energy_per_turbine_kwh:,.0f}) = {d.n_turbines}\n"
            f"Installed power = {d.n_turbines} x {t.rated_power_kw:,.0f} kW = "
            f"{d.installed_power_kw:,.0f} kW\n"
            f"Energy = {d.annual_energy_kwh:,.0f} kWh ({d.achieved_coverage:.0%} of the demand)"
        )
    if key == "wind.spacing":
        return (
            f"Spacing {inp.crosswind_spacing_d:.0f} D x {inp.downwind_spacing_d:.0f} D with "
            f"D = {t.rotor_diameter_m:.0f} m: {inp.crosswind_spacing_d * t.rotor_diameter_m:.0f}"
            f" m x {inp.downwind_spacing_d * t.rotor_diameter_m:.0f} m per turbine\n"
            f"Area for {d.n_turbines} turbine(s) = {d.array_area_km2:.2f} km2"
        )
    return None
