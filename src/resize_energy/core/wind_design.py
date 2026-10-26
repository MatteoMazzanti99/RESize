"""Preliminary design of a wind plant: resource at hub height, yield and number of turbines."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from resize_energy.core import wind
from resize_energy.core import wind_wake as ww
from resize_energy.core.plant_economics import (
    EconomicInputs,
    Economics,
    evaluate_economics,
    with_sensitivity,
)
from resize_energy.core.wind_layout import SiteArea, optimise_layout
from resize_energy.core.wind_rose import WindRose


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
    # --- wake model (off: the single 'other losses' number is used, as before) ---
    wake_model: bool = False
    turbines_per_row: int = 0           # 0 = about square
    stagger_rows: bool = True
    wake_decay: float = 0.075           # 0.075 onshore, 0.04-0.05 offshore
    prevailing_direction_deg: float = 270.0
    rose_concentration: float = 1.0
    rose: WindRose | None = None        # measured rose: replaces prevailing direction + concentration
    # --- layout: a regular grid, or turbines placed by the program inside a site area ---
    layout_mode: str = "grid"           # "grid" or "optimized"
    site_width_m: float = 2500.0
    site_length_m: float = 2500.0
    site_rotation_deg: float = 0.0      # compass bearing of the length of the rectangle
    min_spacing_d: float = 3.0          # closest two turbines may stand, in rotor diameters
    turbine: TurbineSpec = field(default_factory=TurbineSpec)
    economics: EconomicInputs | None = None   # costs and prices; None = no economic step


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
    wake_loss: float = 0.0
    wake: ww.WakeResult | None = None
    turbines_per_row: int = 0
    rows: int = 0
    economics: Economics | None = None
    layout_mode: str = "grid"
    site: SiteArea | None = None
    grid_wake_loss: float | None = None   # the same turbines on a regular grid (optimised mode)
    min_distance_d: float = 0.0           # closest pair of the layout, in rotor diameters


def _min_distance_d(wake: ww.WakeResult | None, diameter_m: float) -> float:
    if wake is None or len(wake.positions) < 2:
        return 0.0
    pts = wake.positions
    return min(math.dist(a, b) for i, a in enumerate(pts) for b in pts[i + 1:]) / diameter_m


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
    net_free = gross * inp.availability * (1.0 - inp.other_losses)
    n = wind.required_turbines(inp.annual_demand_kwh, net_free, inp.coverage)
    if inp.layout_mode not in ("grid", "optimized"):
        raise ValueError("the layout must be 'grid' or 'optimized'")
    optimized = inp.layout_mode == "optimized"
    wake: ww.WakeResult | None = None
    per_row = 0
    site: SiteArea | None = None
    grid_loss: float | None = None
    if inp.wake_model or optimized:
        if inp.rose is not None:
            weights, factors = inp.rose.frequency, inp.rose.speed_factor
            energy_weights = inp.rose.energy_share()
        else:
            weights = ww.rose_weights(inp.prevailing_direction_deg, inp.rose_concentration)
            factors, energy_weights = None, weights
        if optimized:
            if inp.min_spacing_d < 1.0:
                raise ValueError("the minimum spacing must be at least 1 rotor diameter")
            site = SiteArea(inp.site_width_m, inp.site_length_m, inp.site_rotation_deg)

        def grid(count: int) -> tuple[list[tuple[float, float]], int]:
            row = inp.turbines_per_row or max(1, round(math.sqrt(count)))
            return ww.grid_layout(count, row, inp.crosswind_spacing_d, inp.downwind_spacing_d,
                                  t.rotor_diameter_m, inp.stagger_rows,
                                  inp.prevailing_direction_deg), row

        def run(layout: list[tuple[float, float]]) -> ww.WakeResult:
            return ww.wake_efficiency(layout, curve, t.rotor_diameter_m, v_hub, inp.weibull_k,
                                      t.cut_in_ms, t.rated_speed_ms, t.cut_out_ms,
                                      inp.wake_decay, weights, factors)

        def evaluate(count: int, steps: int) -> tuple[ww.WakeResult, int]:
            if site is None:
                layout, row = grid(count)
                return run(layout), row
            layout = optimise_layout(count, site, t.rotor_diameter_m, inp.min_spacing_d,
                                     energy_weights, inp.wake_decay, steps=steps)
            return run(layout), 0

        # more turbines mean more wake: raise the number until the demand is covered
        for _ in range(25):
            wake, per_row = evaluate(n, 1500 if optimized else 0)
            needed = wind.required_turbines(inp.annual_demand_kwh,
                                            net_free * wake.array_efficiency, inp.coverage)
            if needed <= n:
                break
            n = needed
        if optimized:
            wake, per_row = evaluate(n, 8000)          # the final, longer search
            grid_loss = run(grid(n)[0]).wake_loss
    net = net_free * (wake.array_efficiency if wake else 1.0)
    energy = n * net
    design = WindDesign(
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
        array_area_km2=(site.area_km2 if site else wind.array_area_km2(
            n, t.rotor_diameter_m, inp.crosswind_spacing_d, inp.downwind_spacing_d)),
        tip_clearance_m=t.hub_height_m - t.rotor_diameter_m / 2.0,
        rated_to_mean_ratio=t.rated_speed_ms / v_hub,
        wake_loss=wake.wake_loss if wake else 0.0, wake=wake, turbines_per_row=per_row,
        rows=math.ceil(n / per_row) if per_row else 0,
        layout_mode=inp.layout_mode, site=site, grid_wake_loss=grid_loss,
        min_distance_d=_min_distance_d(wake, t.rotor_diameter_m),
    )
    if inp.economics is not None and energy > 0:
        econ = evaluate_economics(design.installed_power_kw, energy, inp.annual_demand_kwh,
                                  inp.economics)
        design = replace(design, economics=with_sensitivity(
            econ, design.installed_power_kw, inp.annual_demand_kwh, inp.economics))
    return design
