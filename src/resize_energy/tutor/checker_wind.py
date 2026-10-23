"""Deterministic design checks of the wind module (offline, repeatable)."""

from __future__ import annotations

from resize_energy.core import wind
from resize_energy.core.wind_design import WindDesign, WindInputs
from resize_energy.tutor.checker import Finding


def check_wind_design(inp: WindInputs, d: WindDesign) -> list[Finding]:
    """Check a wind design against common rules of thumb. One finding per rule."""
    out: list[Finding] = []

    # 1. Resource at hub height
    v = d.mean_speed_hub_ms
    if v < 5.0:
        out.append(Finding("error", "resource",
                           f"Mean wind speed at hub height is {v:.1f} m/s: below about 5 m/s a "
                           "wind plant is rarely viable. Check the site or consider PV.",
                           "wind.resource"))
    elif v < 6.0:
        out.append(Finding("warning", "resource",
                           f"Mean wind speed at hub height is {v:.1f} m/s: a modest resource, "
                           "economics depend on a low-wind turbine (large rotor).",
                           "wind.resource"))
    else:
        out.append(Finding("ok", "resource",
                           f"Mean wind speed at hub height is {v:.1f} m/s: a good resource.",
                           "wind.resource"))

    # 2. Weibull shape and shear
    if not 1.3 <= inp.weibull_k <= 3.5:
        out.append(Finding("warning", "weibull_k",
                           f"Weibull shape k = {inp.weibull_k:.2f} is outside the usual 1.3-3.5 "
                           "range: check the distribution.", "wind.weibull"))
    if not 0.05 <= inp.shear_alpha <= 0.40:
        out.append(Finding("warning", "shear",
                           f"Shear exponent {inp.shear_alpha:.2f} is outside the usual "
                           "0.05-0.40 range.", "wind.shear"))

    # 3. Capacity factor
    cf = d.capacity_factor_net
    if cf < 0.20:
        out.append(Finding("warning", "capacity_factor",
                           f"Net capacity factor {cf:.0%} is low (typical onshore 25-40 %): "
                           "the turbine is too large for this wind, or the site is poor.",
                           "wind.capacity_factor"))
    elif cf > 0.50:
        out.append(Finding("warning", "capacity_factor",
                           f"Net capacity factor {cf:.0%} is very high (offshore-class): "
                           "double-check the wind speed and the loss assumptions.",
                           "wind.capacity_factor"))
    else:
        out.append(Finding("ok", "capacity_factor",
                           f"Net capacity factor {cf:.0%} ({d.full_load_hours_net:,.0f} "
                           "full-load hours) is in a plausible range.", "wind.capacity_factor"))

    # 4. Power coefficient vs Betz
    if d.cp_rated > wind.BETZ_LIMIT:
        out.append(Finding("error", "betz",
                           f"Cp at rated speed is {d.cp_rated:.2f}, above the Betz limit "
                           "0.59: the datasheet values (power, rotor, rated speed) are "
                           "inconsistent.", "wind.cp_betz"))
    elif d.cp_rated > 0.50:
        out.append(Finding("warning", "betz",
                           f"Cp at rated speed is {d.cp_rated:.2f}: close to the best that "
                           "real machines achieve at their peak. Check the datasheet.",
                           "wind.cp_betz"))
    elif d.cp_rated < 0.15:
        out.append(Finding("warning", "betz",
                           f"Cp at rated speed is only {d.cp_rated:.2f}: the rated speed or "
                           "the rotor diameter may be mistyped.", "wind.cp_betz"))
    else:
        out.append(Finding("ok", "betz",
                           f"Cp at rated speed {d.cp_rated:.2f} is below the Betz limit "
                           "(0.59), plausible.", "wind.cp_betz"))

    # 5. Rotor and tower geometry
    if d.tip_clearance_m <= 0:
        out.append(Finding("error", "tip_clearance",
                           "The blade tip would touch the ground: the hub is lower than the "
                           "rotor radius.", "wind.shear"))
    elif d.tip_clearance_m < 20.0:
        out.append(Finding("warning", "tip_clearance",
                           f"Lower blade tip is only {d.tip_clearance_m:.0f} m above ground: "
                           "most standards and sites ask for 20-30 m or more.", "wind.shear"))

    # 6. Rated speed vs mean speed
    r = d.rated_to_mean_ratio
    if r < 1.4 or r > 2.8:
        out.append(Finding("info", "rated_ratio",
                           f"Rated speed is {r:.1f} times the mean wind speed (usual 1.6-2.5): "
                           "the turbine will rarely reach rated power, or be saturated for "
                           "long.", "wind.power_curve"))

    # 7. Specific power
    sp = d.specific_power_w_m2
    if sp > 450:
        out.append(Finding("info", "specific_power",
                           f"Specific power {sp:.0f} W/m2 is high: such turbines suit windy "
                           "sites (above 8 m/s).", "wind.cp_betz"))
    elif sp < 200:
        out.append(Finding("info", "specific_power",
                           f"Specific power {sp:.0f} W/m2 is low: a low-wind design with a "
                           "large rotor.", "wind.cp_betz"))

    # 8. Air density
    if d.air_density < 1.10:
        out.append(Finding("info", "density",
                           f"Air density {d.air_density:.2f} kg/m3 is "
                           f"{1 - d.air_density / wind.RHO_STANDARD:.0%} below standard: the "
                           "power curve was corrected for it.", "wind.air_density"))

    # 9. Spacing
    if inp.crosswind_spacing_d < 3.0 or inp.downwind_spacing_d < 5.0:
        out.append(Finding("warning", "spacing",
                           f"Spacing {inp.crosswind_spacing_d:.0f} D x "
                           f"{inp.downwind_spacing_d:.0f} D is tighter than the usual "
                           "3-5 D x 5-9 D: wake losses will exceed the assumed "
                           f"{inp.other_losses:.0%}.", "wind.spacing"))

    # 10. Coverage
    if inp.annual_demand_kwh > 0:
        if d.achieved_coverage > 2.0 and d.n_turbines == 1:
            out.append(Finding("warning", "oversized",
                               f"One turbine already produces {d.achieved_coverage:.0%} of the "
                               "demand: a smaller machine, or grid export, should be "
                               "considered.", "wind.number_of_turbines"))
        elif d.achieved_coverage > 1.1 * inp.coverage:
            out.append(Finding("info", "coverage_high",
                               f"The plant covers {d.achieved_coverage:.0%} of the demand "
                               f"versus {inp.coverage:.0%} requested (turbines come in whole "
                               "units).", "wind.number_of_turbines"))
    if d.wake is not None:
        if d.wake_loss > 0.12:
            out.append(Finding(
                "warning", "wake_high",
                f"The wake loss is {d.wake_loss:.1%}: widen the spacing along the prevailing "
                "wind or reduce the number of rows.", "wind.wake"))
        worst = min(d.wake.sector_efficiency)
        if worst < 0.75:
            out.append(Finding(
                "info", "wake_sector",
                f"From the worst direction the array makes only {worst:.0%} of its free-wind "
                "energy (turbines in line): fine if that wind is rare, check the rose.",
                "wind.rose"))
        if inp.other_losses >= 0.10:
            out.append(Finding(
                "info", "double_count",
                "With the wake model on, 'other losses' should no longer include the wake: "
                "10 % was a value for wake plus electrical losses; 3-6 % is more usual now.",
                "wind.losses"))
    return out
