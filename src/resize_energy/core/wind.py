"""First-order wind resource and energy-yield functions.

Pure functions, SI units stated in each docstring, covered by hand-checked tests.
The wind speed distribution is a Weibull with shape ``k`` and scale ``A`` [m/s].
"""

from __future__ import annotations

import math
from collections.abc import Callable

RHO_STANDARD = 1.225  # kg/m3, sea level, 15 degC (power curves are given at this density)
HOURS_PER_YEAR = 8760.0
BETZ_LIMIT = 16.0 / 27.0  # 0.593


def weibull_scale_from_mean(mean_speed_ms: float, k: float) -> float:
    """Weibull scale A [m/s] giving a mean wind speed.

    Formula:  v_mean = A * Gamma(1 + 1/k)   ->   A = v_mean / Gamma(1 + 1/k)
    """
    if mean_speed_ms <= 0:
        raise ValueError("mean_speed_ms must be > 0")
    if k <= 0:
        raise ValueError("k must be > 0")
    return mean_speed_ms / math.gamma(1.0 + 1.0 / k)


def weibull_cdf(v: float, k: float, scale: float) -> float:
    """Probability that the wind speed is below ``v``:  F(v) = 1 - exp(-(v/A)^k)."""
    if v <= 0:
        return 0.0
    return 1.0 - math.exp(-((v / scale) ** k))


def shear_power_law(v_ref_ms: float, h_ref_m: float, h_m: float, alpha: float = 0.14) -> float:
    """Wind speed at height ``h_m`` from a measurement at ``h_ref_m`` (power law).

    Formula:  v(h) = v_ref * (h / h_ref)^alpha
    alpha: about 0.10 over water, 0.14 open flat land, 0.20-0.30 forest or town.
    """
    if h_ref_m <= 0 or h_m <= 0:
        raise ValueError("heights must be > 0")
    return v_ref_ms * (h_m / h_ref_m) ** alpha


def air_density(elevation_m: float = 0.0, temperature_c: float = 15.0) -> float:
    """Air density [kg/m3] from elevation and mean temperature (ideal gas, standard pressure).

    Formula:  p = 101325 * (1 - 2.25577e-5 * z)^5.25588 ,   rho = p / (R * T) ,  R = 287.05
    """
    pressure = 101325.0 * (1.0 - 2.25577e-5 * elevation_m) ** 5.25588
    return pressure / (287.05 * (temperature_c + 273.15))


def swept_area_m2(rotor_diameter_m: float) -> float:
    """Rotor swept area A = pi * D^2 / 4  [m2]."""
    return math.pi * rotor_diameter_m**2 / 4.0


def wind_power_density_w_m2(rho: float, v_ms: float) -> float:
    """Power in the wind per unit rotor area: 0.5 * rho * v^3  [W/m2]."""
    return 0.5 * rho * v_ms**3


def power_coefficient_at_rated(
    rated_power_kw: float, rotor_diameter_m: float, rated_speed_ms: float, rho: float = RHO_STANDARD
) -> float:
    """Cp implied by the rated point:  Cp = P_rated / (0.5 * rho * A * v_rated^3).

    The peak Cp of real machines is 0.40-0.50, but at the rated wind speed the blades are
    already pitching out of the wind, so Cp there is typically 0.25-0.40. It can never exceed
    the Betz limit 16/27 = 0.593.
    """
    available_w = 0.5 * rho * swept_area_m2(rotor_diameter_m) * rated_speed_ms**3
    return rated_power_kw * 1000.0 / available_w


def generic_power_kw(
    v_ms: float,
    rated_power_kw: float,
    cut_in_ms: float,
    rated_speed_ms: float,
    cut_out_ms: float,
    rho: float = RHO_STANDARD,
) -> float:
    """Simple power curve of a pitch-regulated turbine at air density ``rho``.

    Below rated the power follows the cube of the wind speed measured from cut-in:
        P = P_rated * (v^3 - v_ci^3) / (v_r^3 - v_ci^3)
    then it is flat at P_rated until cut-out. At density ``rho`` the curve is read at the
    density-equivalent speed v * (rho / 1.225)^(1/3), a common first-order correction.
    """
    if v_ms >= cut_out_ms or v_ms < 0:
        return 0.0
    v_eq = v_ms * (rho / RHO_STANDARD) ** (1.0 / 3.0)
    if v_eq <= cut_in_ms:
        return 0.0
    if v_eq >= rated_speed_ms:
        return rated_power_kw
    return rated_power_kw * (v_eq**3 - cut_in_ms**3) / (rated_speed_ms**3 - cut_in_ms**3)


def annual_energy_kwh(
    power_kw: Callable[[float], float], k: float, scale: float, step_ms: float = 0.1,
    v_max_ms: float = 40.0,
) -> float:
    """Gross yearly energy of one turbine [kWh] from a power curve and a Weibull climate.

    Formula:  E = 8760 * sum_i P(v_i) * [F(v_i + dv/2) - F(v_i - dv/2)]
    where F is the Weibull cumulative distribution (exact probability of each speed bin).
    """
    total = 0.0
    n = int(round(v_max_ms / step_ms))
    for i in range(n + 1):
        v = i * step_ms
        p = power_kw(v)
        if p <= 0:
            continue
        prob = weibull_cdf(v + step_ms / 2, k, scale) - weibull_cdf(max(0.0, v - step_ms / 2), k, scale)
        total += p * prob
    return HOURS_PER_YEAR * total


def capacity_factor(energy_kwh: float, rated_power_kw: float) -> float:
    """Capacity factor CF = E / (P_rated * 8760)  [-]."""
    return energy_kwh / (rated_power_kw * HOURS_PER_YEAR)


def required_turbines(
    annual_demand_kwh: float, energy_per_turbine_kwh: float, coverage: float = 1.0
) -> int:
    """Number of identical turbines to cover a fraction of the demand (rounded up)."""
    if energy_per_turbine_kwh <= 0:
        raise ValueError("energy_per_turbine_kwh must be > 0")
    return max(1, math.ceil(coverage * annual_demand_kwh / energy_per_turbine_kwh - 1e-9))


def array_area_km2(n_turbines: int, rotor_diameter_m: float, crosswind_d: float = 5.0,
                   downwind_d: float = 7.0) -> float:
    """Land needed with spacing ``crosswind_d`` x ``downwind_d`` rotor diameters  [km2].

    Each turbine takes crosswind_d * downwind_d * D^2 (typical 5-9 D across, 7-12 D along
    the prevailing wind, to keep wake losses moderate).
    """
    return n_turbines * crosswind_d * downwind_d * rotor_diameter_m**2 / 1e6
