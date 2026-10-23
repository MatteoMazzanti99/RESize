"""Preliminary design of a wind plant: resource at hub height, yield and number of turbines."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from resize_energy.core import wind


@dataclass(frozen=True)
class TurbineSpec:
    """Wind turbine datasheet values."""

    name: str = "Generic 2 MW turbine"
    rated_power_kw: float = 2000.0
    rotor_diameter_m: float = 90.0
    hub_height_m: float = 80.0
    cut_in_ms: float = 3.0
    rated_speed_ms: float = 12.0
    cut_out_ms: float = 25.0
    # Optional tabulated power curve ((speed m/s, power kW), ...), e.g. from the library.
    # When empty, a generic cubic curve built from the speeds above is used.
    power_curve: tuple[tuple[float, float], ...] = ()
    curve_source: str = ""


@dataclass(frozen=True)
class WindInputs:
    """All inputs of the preliminary wind design."""

    annual_demand_kwh: float
    mean_speed_ref_ms: float            # mean wind speed at the reference height
    ref_height_m: float = 50.0
    weibull_k: float = 2.0
    shear_alpha: float = 0.14
    elevation_m: float = 100.0
    temperature_c: float = 12.0
    coverage: float = 1.0
    availability: float = 0.97          # share of time the turbine is available
    other_losses: float = 0.10          # wake, electrical, icing, curtailment, ...
    crosswind_spacing_d: float = 5.0
    downwind_spacing_d: float = 7.0
    turbine: TurbineSpec = field(default_factory=TurbineSpec)


@dataclass(frozen=True)
class WindDesign:
    """Result of the preliminary design."""

    mean_speed_hub_ms: float
    weibull_scale_ms: float
    air_density: float
    swept_area_m2: float
    specific_power_w_m2: float
    cp_rated: float
    gross_energy_per_turbine_kwh: float
    net_energy_per_turbine_kwh: float
    capacity_factor_gross: float
    capacity_factor_net: float
    full_load_hours_net: float
    n_turbines: int
    installed_power_kw: float
    annual_energy_kwh: float
    achieved_coverage: float
    array_area_km2: float
    tip_clearance_m: float
    rated_to_mean_ratio: float


def size_wind_plant(inp: WindInputs) -> WindDesign:
    """Size the plant: hub-height speed -> Weibull -> density -> yield per turbine -> number."""
    t = inp.turbine
    if not 0 < t.cut_in_ms < t.rated_speed_ms < t.cut_out_ms:
        raise ValueError("speeds must satisfy 0 < cut-in < rated < cut-out")
    if t.rated_power_kw <= 0 or t.rotor_diameter_m <= 0 or t.hub_height_m <= 0:
        raise ValueError("rated power, rotor diameter and hub height must be > 0")
    if inp.annual_demand_kwh <= 0:
        raise ValueError("annual demand must be > 0")
    if not 0 < inp.availability <= 1 or not 0 <= inp.other_losses < 1:
        raise ValueError("availability must be in (0, 1] and other losses in [0, 1)")
    v_hub = wind.shear_power_law(inp.mean_speed_ref_ms, inp.ref_height_m, t.hub_height_m,
                                 inp.shear_alpha)
    scale = wind.weibull_scale_from_mean(v_hub, inp.weibull_k)
    rho = wind.air_density(inp.elevation_m, inp.temperature_c)
    area = wind.swept_area_m2(t.rotor_diameter_m)

    def curve(v: float) -> float:
        if t.power_curve:
            return wind.curve_power_kw(v, t.power_curve, t.cut_out_ms, rho)
        return wind.generic_power_kw(v, t.rated_power_kw, t.cut_in_ms, t.rated_speed_ms,
                                     t.cut_out_ms, rho)

    gross = wind.annual_energy_kwh(curve, inp.weibull_k, scale)
    net = gross * inp.availability * (1.0 - inp.other_losses)
    n = wind.required_turbines(inp.annual_demand_kwh, net, inp.coverage)
    energy = n * net
    return WindDesign(
        mean_speed_hub_ms=v_hub,
        weibull_scale_ms=scale,
        air_density=rho,
        swept_area_m2=area,
        specific_power_w_m2=t.rated_power_kw * 1000.0 / area,
        cp_rated=wind.power_coefficient_at_rated(t.rated_power_kw, t.rotor_diameter_m,
                                                 t.rated_speed_ms, rho),
        gross_energy_per_turbine_kwh=gross,
        net_energy_per_turbine_kwh=net,
        capacity_factor_gross=wind.capacity_factor(gross, t.rated_power_kw),
        capacity_factor_net=wind.capacity_factor(net, t.rated_power_kw),
        full_load_hours_net=net / t.rated_power_kw,
        n_turbines=n,
        installed_power_kw=n * t.rated_power_kw,
        annual_energy_kwh=energy,
        achieved_coverage=energy / inp.annual_demand_kwh if inp.annual_demand_kwh > 0 else math.inf,
        array_area_km2=wind.array_area_km2(n, t.rotor_diameter_m, inp.crosswind_spacing_d,
                                           inp.downwind_spacing_d),
        tip_clearance_m=t.hub_height_m - t.rotor_diameter_m / 2.0,
        rated_to_mean_ratio=t.rated_speed_ms / v_hub,
    )
