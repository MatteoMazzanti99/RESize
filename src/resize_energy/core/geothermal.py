"""Building blocks of hydrothermal geothermal sizing: brine heat and exergy, plant efficiency.

Pure functions, no GUI. Temperatures in degC (K where stated), flows in kg/s, power in kW.
"""

from __future__ import annotations

import math

CP_WATER = 4.18            # kJ/(kg K), liquid water below about 150 degC
RHO_WATER = 1000.0         # kg/m3 (about 920-980 at 100-200 degC; the pump estimate is rough)
HOURS_PER_YEAR = 8760.0
KELVIN = 273.15


def thermal_power_kw(flow_kg_s: float, t_in: float, t_out: float) -> float:
    """Heat taken from the brine: P = m cp (T_in - T_out) [kW]."""
    if flow_kg_s < 0:
        raise ValueError("the flow cannot be negative")
    if t_out > t_in:
        raise ValueError("the return temperature must not exceed the production temperature")
    return flow_kg_s * CP_WATER * (t_in - t_out)


def brine_exergy_kj_per_kg(t_brine: float, t_ambient: float) -> float:
    """Specific exergy of liquid brine relative to the ambient: cp [(T - T0) - T0 ln(T / T0)]."""
    if t_brine < t_ambient:
        raise ValueError("the brine must be warmer than the ambient")
    t, t0 = t_brine + KELVIN, t_ambient + KELVIN
    return CP_WATER * ((t - t0) - t0 * math.log(t / t0))


def binary_cycle_efficiency(t_brine: float) -> float:
    """Net thermal efficiency of binary plants: (0.09345 T - 2.32657) % (T in degC).

    Fit of ten operating plants with brine between 103 and 166 degC (MIT, 2006, fig. 7.2).
    """
    if t_brine <= 0:
        raise ValueError("the brine temperature must be > 0")
    return max(0.0, (0.09345 * t_brine - 2.32657) / 100.0)


def pump_power_kw(flow_kg_s: float, pressure_bar: float, efficiency: float) -> float:
    """Electric power to circulate the brine: V dp / eta, with V = m / rho [kW]."""
    if not 0.0 < efficiency <= 1.0:
        raise ValueError("pump efficiency must be in (0, 1]")
    if pressure_bar < 0 or flow_kg_s < 0:
        raise ValueError("pressure and flow cannot be negative")
    return flow_kg_s / RHO_WATER * pressure_bar * 100.0 / efficiency


def well_depth_m(t_reservoir: float, t_surface: float, gradient_k_per_km: float) -> float:
    """Depth at which the rock reaches ``t_reservoir``: (T - T_surface) / gradient."""
    if gradient_k_per_km <= 0:
        raise ValueError("the geothermal gradient must be > 0")
    if t_reservoir <= t_surface:
        raise ValueError("the reservoir must be warmer than the surface")
    return (t_reservoir - t_surface) / gradient_k_per_km * 1000.0
