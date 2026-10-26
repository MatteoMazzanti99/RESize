"""Preliminary design of a run-of-river hydropower plant (no reservoir).

The river is described by its mean flow and by Q95 (the flow exceeded 95 % of the time): from
these two numbers a log-normal flow-duration curve is built. The turbine takes the river flow
minus the environmental flow that must stay in the river, up to its design flow, and works only
above its minimum flow. Pure calculation, no GUI.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from resize_energy.core import economics as eco
from resize_energy.core import hydro as hy

STEPS = 400   # points of the flow-duration curve used for the yearly integration


@dataclass(frozen=True)
class HydroInputs:
    # --- site ---
    gross_head_m: float = 40.0
    mean_flow_m3s: float = 2.0
    q95_m3s: float = 0.4
    eco_flow_m3s: float = 0.2              # flow that must stay in the river
    # --- plant ---
    design_exceedance: float = 0.30        # the design flow is available this share of the time
    penstock_length_m: float = 300.0
    penstock_velocity_ms: float = 3.0      # used to choose the diameter
    penstock_diameter_m: float = 0.0       # 0: chosen from the velocity
    roughness_mm: float = 0.1              # steel, new
    local_loss_k: float = 1.0              # intake, trash rack, bends, valve: sum of K
    turbine: str = "auto"                  # "auto" or a key of hy.TURBINES
    turbine_efficiency: float = 0.0        # 0: the typical best efficiency of the type
    generator_efficiency: float = 0.0      # 0: typical value for the size
    operating_losses: float = 0.05         # outages, part-load efficiency, cleaning: share of energy
    # --- demand and emissions ---
    annual_demand_kwh: float = 0.0         # 0: everything is sold
    grid_ef: float = 0.25
    lifecycle_g_per_kwh: float = 24.0      # hydropower, median of the IPCC AR5 range
    # --- costs ---
    capex_per_kw: float = 6600.0
    om_fraction: float = 0.025             # of the CAPEX per year
    life_years: float = 40.0
    discount_rate: float = 0.05
    retail_price: float = 0.20
    export_price: float = 0.10


@dataclass(frozen=True)
class HydroDesign:
    mu: float
    sigma: float
    design_flow_m3s: float
    river_flow_at_design_m3s: float
    turbine_key: str
    turbine_name: str
    turbine_eff: float
    generator_eff: float
    penstock_diameter_m: float
    velocity_ms: float
    head_loss_m: float
    net_head_m: float
    min_flow_m3s: float
    rated_kw: float
    energy_kwh: float
    full_load_hours: float
    capacity_factor: float
    hours_working: float                   # hours per year with the turbine running
    water_used_fraction: float             # share of the river volume that goes through the turbine
    eco_flow_share: float                  # environmental flow / mean flow
    electricity_coverage: float
    co2_avoided_t_per_year: float
    capex: float
    om_per_year: float
    lcoe: float
    savings_per_year: float
    payback_years: float
    npv: float
    curve: tuple[tuple[float, float, float], ...]   # (exceedance, river flow, turbine flow)


def _check(i: HydroInputs) -> None:
    if i.gross_head_m <= 0:
        raise ValueError("the gross head must be > 0")
    if i.eco_flow_m3s < 0:
        raise ValueError("the environmental flow cannot be negative")
    if not 0.0 < i.design_exceedance < 1.0:
        raise ValueError("the design exceedance must be between 0 and 100 %")
    if i.penstock_length_m < 0 or i.penstock_velocity_ms <= 0 or i.penstock_diameter_m < 0:
        raise ValueError("penstock length, velocity and diameter must be positive")
    if i.turbine != "auto" and i.turbine not in hy.TURBINES:
        raise ValueError(f"unknown turbine {i.turbine!r}")
    if not 0.0 <= i.operating_losses < 1.0:
        raise ValueError("operating losses must be in [0, 1)")
    if i.capex_per_kw < 0 or i.om_fraction < 0 or i.life_years <= 0:
        raise ValueError("costs and lifetime must be positive")


def _net_head(i: HydroInputs, diameter: float, flow: float) -> float:
    return i.gross_head_m - hy.head_loss(flow, diameter, i.penstock_length_m,
                                         i.roughness_mm / 1000.0, i.local_loss_k)


def size_hydro_plant(i: HydroInputs) -> HydroDesign:
    """Size the plant and integrate the yearly energy over the flow-duration curve."""
    _check(i)
    mu, sigma = hy.lognormal_fdc(i.mean_flow_m3s, i.q95_m3s)
    if i.eco_flow_m3s >= i.mean_flow_m3s:
        raise ValueError("the environmental flow must be lower than the mean flow")
    q_river_d = hy.flow_exceeded(i.design_exceedance, mu, sigma)
    q_design = q_river_d - i.eco_flow_m3s
    if q_design <= 0:
        raise ValueError("at the chosen exceedance the river has no water left after the "
                         "environmental flow: choose a higher exceedance (a lower design flow)")
    diameter = i.penstock_diameter_m or hy.penstock_diameter(q_design, i.penstock_velocity_ms)
    velocity = q_design / (3.141592653589793 * diameter ** 2 / 4.0)
    h_loss = i.gross_head_m - _net_head(i, diameter, q_design)
    h_net = i.gross_head_m - h_loss
    if h_net <= 0:
        raise ValueError("the penstock loses all the head: increase the diameter")
    key = i.turbine if i.turbine != "auto" else hy.choose_turbine(h_net, q_design)
    ttype = hy.TURBINES[key]
    eta_t = i.turbine_efficiency or ttype.efficiency
    p_hydraulic = hy.hydraulic_power_kw(q_design, h_net)
    eta_g = i.generator_efficiency or hy.generator_efficiency(p_hydraulic * eta_t)
    rated = p_hydraulic * eta_t * eta_g
    q_min = ttype.min_flow_fraction * q_design

    energy = 0.0
    working = 0.0
    water_total = 0.0
    water_used = 0.0
    curve = []
    dt = hy.HOURS_PER_YEAR / STEPS
    for k in range(STEPS):
        p = (k + 0.5) / STEPS
        q_r = hy.flow_exceeded(p, mu, sigma)
        q_av = max(q_r - i.eco_flow_m3s, 0.0)
        q_t = min(q_av, q_design)
        if q_t < q_min:
            q_t = 0.0
        water_total += q_r
        water_used += q_t
        if q_t > 0.0:
            working += dt
            energy += hy.hydraulic_power_kw(q_t, _net_head(i, diameter, q_t), eta_t * eta_g) * dt
        curve.append((p, q_r, q_t))
    energy *= 1.0 - i.operating_losses

    capex = rated * i.capex_per_kw
    om = capex * i.om_fraction
    savings = eco.annual_savings(energy, i.annual_demand_kwh, i.retail_price, i.export_price)
    net = savings - om
    return HydroDesign(
        mu=mu, sigma=sigma, design_flow_m3s=q_design, river_flow_at_design_m3s=q_river_d,
        turbine_key=key, turbine_name=ttype.name, turbine_eff=eta_t, generator_eff=eta_g,
        penstock_diameter_m=diameter, velocity_ms=velocity, head_loss_m=h_loss, net_head_m=h_net,
        min_flow_m3s=q_min, rated_kw=rated, energy_kwh=energy,
        full_load_hours=energy / rated, capacity_factor=energy / (rated * hy.HOURS_PER_YEAR),
        hours_working=working, water_used_fraction=water_used / water_total,
        eco_flow_share=i.eco_flow_m3s / i.mean_flow_m3s,
        electricity_coverage=(energy / i.annual_demand_kwh) if i.annual_demand_kwh > 0 else 0.0,
        co2_avoided_t_per_year=eco.co2_avoided_kg_per_year(energy, i.grid_ef,
                                                           i.lifecycle_g_per_kwh) / 1000.0,
        capex=capex, om_per_year=om,
        lcoe=eco.lcoe(capex, om, energy, i.discount_rate, i.life_years),
        savings_per_year=savings, payback_years=eco.simple_payback_years(capex, net),
        npv=eco.npv(capex, net, i.discount_rate, i.life_years), curve=tuple(curve))


def exceedance_sweep(i: HydroInputs, points: int = 15) -> list[tuple[float, float, float, float]]:
    """(design exceedance, rated kW, yearly kWh, capacity factor) for design flows from Q10 to Q90.

    Choices where the river has no water left after the environmental flow are skipped.
    """
    out = []
    for k in range(points):
        p = 0.10 + 0.80 * k / (points - 1)
        try:
            d = size_hydro_plant(replace(i, design_exceedance=p))
        except ValueError:
            continue
        out.append((p, d.rated_kw, d.energy_kwh, d.capacity_factor))
    return out
