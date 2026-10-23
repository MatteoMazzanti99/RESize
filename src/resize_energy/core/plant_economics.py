"""Cost, savings and carbon of a single plant (photovoltaic or wind), with sensitivity.

Pure calculation, no GUI. Same textbook annuity model as the technology comparison: constant
energy and prices (real terms), annual balance (up to the demand at the retail price, the
rest exported), no taxes, incentives or degradation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from resize_energy.core import economics as eco
from resize_energy.core.sensitivity import Parameter, Sensitivity, one_at_a_time


@dataclass(frozen=True)
class EconomicInputs:
    capex_per_kw: float = 1000.0          # euro per kW (kWp for PV) installed
    om_per_kw_year: float = 15.0          # euro per kW per year
    life_years: float = 25.0
    discount_rate: float = 0.05
    retail_price: float = 0.20            # euro/kWh bought from the grid
    export_price: float = 0.07            # euro/kWh sold to the grid
    grid_ef: float = 0.25                 # kg CO2 per kWh of the grid
    lifecycle_g_per_kwh: float = 45.0     # life-cycle emissions of the plant


@dataclass(frozen=True)
class Economics:
    capex: float
    om_per_year: float
    energy_kwh: float
    self_used_kwh: float
    exported_kwh: float
    lcoe: float
    savings_per_year: float
    net_benefit_per_year: float
    payback_years: float
    discounted_payback_years: float
    npv: float
    co2_avoided_t_per_year: float
    cash: tuple[float, ...]               # cumulative discounted result, year 0 .. life
    sensitivity: Sensitivity | None = None


def _check(power_kw: float, energy_kwh: float, demand_kwh: float, e: EconomicInputs) -> None:
    if power_kw <= 0 or energy_kwh <= 0 or demand_kwh <= 0:
        raise ValueError("power, energy and demand must be > 0")
    if e.capex_per_kw < 0 or e.om_per_kw_year < 0:
        raise ValueError("costs cannot be negative")
    if e.life_years <= 0:
        raise ValueError("the lifetime must be > 0 years")
    if not 0 <= e.discount_rate < 1:
        raise ValueError("the discount rate must be in [0, 1)")
    if e.retail_price <= 0 or e.export_price < 0:
        raise ValueError("the retail price must be > 0 and the export price >= 0")
    if e.grid_ef < 0 or e.lifecycle_g_per_kwh < 0:
        raise ValueError("emission factors cannot be negative")


def evaluate_economics(power_kw: float, energy_kwh: float, demand_kwh: float,
                       e: EconomicInputs) -> Economics:
    _check(power_kw, energy_kwh, demand_kwh, e)
    capex = power_kw * e.capex_per_kw
    om = power_kw * e.om_per_kw_year
    savings = eco.annual_savings(energy_kwh, demand_kwh, e.retail_price, e.export_price)
    net = savings - om
    years = int(math.ceil(e.life_years))
    cash = [-capex] + [
        -capex + net * eco.annuity_factor(e.discount_rate, min(float(y), e.life_years))
        for y in range(1, years + 1)]
    return Economics(
        capex=capex, om_per_year=om, energy_kwh=energy_kwh,
        self_used_kwh=min(energy_kwh, demand_kwh), exported_kwh=max(0.0, energy_kwh - demand_kwh),
        lcoe=eco.lcoe(capex, om, energy_kwh, e.discount_rate, e.life_years),
        savings_per_year=savings, net_benefit_per_year=net,
        payback_years=eco.simple_payback_years(capex, net),
        discounted_payback_years=eco.discounted_payback_years(capex, net, e.discount_rate),
        npv=eco.npv(capex, net, e.discount_rate, e.life_years),
        co2_avoided_t_per_year=eco.co2_avoided_kg_per_year(
            energy_kwh, e.grid_ef, e.lifecycle_g_per_kwh) / 1000.0,
        cash=tuple(cash))


def economics_sensitivity(power_kw: float, energy_kwh: float, demand_kwh: float,
                          e: EconomicInputs) -> Sensitivity:
    """Net present value when each input moves by +/- 20 %."""
    def evaluate(f: dict[str, float]) -> float:
        i = replace(
            e, capex_per_kw=e.capex_per_kw * f.get("capex", 1.0),
            om_per_kw_year=e.om_per_kw_year * f.get("om", 1.0),
            retail_price=e.retail_price * f.get("retail", 1.0),
            export_price=e.export_price * f.get("export", 1.0),
            discount_rate=e.discount_rate * f.get("rate", 1.0),
            life_years=e.life_years * f.get("life", 1.0))
        return evaluate_economics(power_kw, energy_kwh * f.get("energy", 1.0), demand_kwh, i).npv

    params = [Parameter("capex", "Cost of the plant"), Parameter("energy", "Energy produced"),
              Parameter("retail", "Price you pay for electricity"),
              Parameter("export", "Price paid for the surplus"),
              Parameter("om", "Operation and maintenance"), Parameter("rate", "Discount rate"),
              Parameter("life", "Lifetime")]
    return one_at_a_time(evaluate, params, "Net present value", "euro", decimals=0)


def with_sensitivity(econ: Economics, power_kw: float, demand_kwh: float,
                     e: EconomicInputs) -> Economics:
    return replace(econ, sensitivity=economics_sensitivity(power_kw, econ.energy_kwh,
                                                           demand_kwh, e))
