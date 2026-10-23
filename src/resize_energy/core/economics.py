"""Simple economics and carbon accounting used to compare technologies.

Pure functions, no GUI. Money is in euro, energy in kWh, time in years. The model is the
textbook annuity one: constant yearly energy, constant yearly costs, constant prices (real
terms), no taxes, no incentives, no degradation, no financing structure.
"""

from __future__ import annotations

import math


def capital_recovery_factor(rate: float, years: float) -> float:
    """CRF = r (1 + r)^n / ((1 + r)^n - 1): yearly payment per euro of capital over n years."""
    if years <= 0:
        raise ValueError("lifetime must be > 0 years")
    if rate < 0:
        raise ValueError("discount rate must be >= 0")
    if rate == 0:
        return 1.0 / years
    growth = (1.0 + rate) ** years
    return rate * growth / (growth - 1.0)


def annuity_factor(rate: float, years: float) -> float:
    """Present value of 1 euro per year for n years (the inverse of the CRF)."""
    return 1.0 / capital_recovery_factor(rate, years)


def lcoe(capex: float, om_per_year: float, energy_kwh_per_year: float, rate: float,
         years: float) -> float:
    """Levelised cost of energy [euro/kWh] = (CAPEX x CRF + O&M) / yearly energy."""
    if energy_kwh_per_year <= 0:
        raise ValueError("yearly energy must be > 0")
    return (capex * capital_recovery_factor(rate, years) + om_per_year) / energy_kwh_per_year


def annual_savings(energy_kwh: float, demand_kwh: float, retail_price: float,
                   export_price: float) -> float:
    """Yearly value of the energy: up to the demand at the retail price, the rest exported.

    Annual balance only (like net metering): the hour-by-hour match is not modelled.
    """
    useful = min(energy_kwh, demand_kwh)
    surplus = max(0.0, energy_kwh - demand_kwh)
    return useful * retail_price + surplus * export_price


def simple_payback_years(capex: float, net_benefit_per_year: float) -> float:
    """CAPEX / (yearly savings - O&M); infinity when the plant never pays back."""
    return capex / net_benefit_per_year if net_benefit_per_year > 0 else math.inf


def discounted_payback_years(capex: float, net_benefit_per_year: float, rate: float) -> float:
    """Years until the discounted cash flow repays CAPEX; infinity if it never does."""
    if net_benefit_per_year <= 0:
        return math.inf
    if rate == 0:
        return capex / net_benefit_per_year
    x = capex * rate / net_benefit_per_year
    return -math.log(1.0 - x) / math.log(1.0 + rate) if x < 1.0 else math.inf


def npv(capex: float, net_benefit_per_year: float, rate: float, years: float) -> float:
    """Net present value over the lifetime: -CAPEX + net benefit x annuity factor."""
    return -capex + net_benefit_per_year * annuity_factor(rate, years)


def co2_avoided_kg_per_year(energy_kwh: float, grid_kg_per_kwh: float,
                            lifecycle_g_per_kwh: float) -> float:
    """Grid emissions displaced minus the plant's own life-cycle emissions [kg CO2 / year]."""
    return energy_kwh * (grid_kg_per_kwh - lifecycle_g_per_kwh / 1000.0)
