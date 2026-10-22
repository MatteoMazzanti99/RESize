"""First-order photovoltaic sizing functions.

All functions are pure, use SI-based units stated in each docstring, and are covered by
hand-checked unit tests. Detailed hourly simulation (pvlib) will be added on top of these.
"""

from __future__ import annotations

import math


def required_peak_power_kwp(
    annual_demand_kwh: float,
    annual_irradiation_kwh_m2: float,
    performance_ratio: float = 0.80,
    coverage: float = 1.0,
) -> float:
    """Peak power (kWp) needed to cover a fraction of an annual energy demand.

    Formula:  E = P_kWp * H * PR   (STC irradiance = 1 kW/m2)
              P_kWp = coverage * E_demand / (H * PR)

    Args:
        annual_demand_kwh: yearly electricity demand [kWh].
        annual_irradiation_kwh_m2: yearly in-plane irradiation H [kWh/m2].
        performance_ratio: overall PR, typically 0.75-0.85 [-].
        coverage: fraction of the demand to be covered by PV, 0-1 [-].
    """
    if annual_demand_kwh < 0:
        raise ValueError("annual_demand_kwh must be >= 0")
    if annual_irradiation_kwh_m2 <= 0:
        raise ValueError("annual_irradiation_kwh_m2 must be > 0")
    if not 0 < performance_ratio <= 1:
        raise ValueError("performance_ratio must be in (0, 1]")
    if not 0 <= coverage <= 1:
        raise ValueError("coverage must be in [0, 1]")
    return coverage * annual_demand_kwh / (annual_irradiation_kwh_m2 * performance_ratio)


def module_voltage_at_temperature(v_stc: float, temp_coeff_pct_per_c: float, t_c: float) -> float:
    """Module voltage (V) at cell temperature ``t_c`` from its STC value.

    V(T) = V_stc * (1 + beta * (T - 25)),  beta given in %/degC (negative for silicon).
    """
    return v_stc * (1.0 + (temp_coeff_pct_per_c / 100.0) * (t_c - 25.0))


def max_modules_per_string(
    inverter_vdc_max: float,
    voc_stc: float,
    temp_coeff_voc_pct_per_c: float,
    t_min_c: float,
) -> int:
    """Maximum modules in series so that Voc at the coldest temperature stays below Vdc,max."""
    voc_cold = module_voltage_at_temperature(voc_stc, temp_coeff_voc_pct_per_c, t_min_c)
    return math.floor(inverter_vdc_max / voc_cold)


def min_modules_per_string(
    inverter_mppt_vmin: float,
    vmp_stc: float,
    temp_coeff_vmp_pct_per_c: float,
    t_cell_max_c: float,
) -> int:
    """Minimum modules in series so that Vmp at the hottest cell temperature stays above V_MPPT,min."""
    vmp_hot = module_voltage_at_temperature(vmp_stc, temp_coeff_vmp_pct_per_c, t_cell_max_c)
    return math.ceil(inverter_mppt_vmin / vmp_hot)


def max_modules_for_mppt_window(
    inverter_mppt_vmax: float,
    vmp_stc: float,
    temp_coeff_vmp_pct_per_c: float,
    t_min_c: float,
) -> int:
    """Maximum modules in series so that Vmp at the coldest temperature stays in the MPPT window."""
    vmp_cold = module_voltage_at_temperature(vmp_stc, temp_coeff_vmp_pct_per_c, t_min_c)
    return math.floor(inverter_mppt_vmax / vmp_cold)


def dc_ac_ratio(dc_power_kwp: float, inverter_ac_kw: float) -> float:
    """DC/AC (loading) ratio. Typical design range: about 1.1-1.3."""
    if inverter_ac_kw <= 0:
        raise ValueError("inverter_ac_kw must be > 0")
    return dc_power_kwp / inverter_ac_kw
