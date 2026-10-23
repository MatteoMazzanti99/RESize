"""Side-by-side comparison of a photovoltaic and a wind plant sized for the same demand."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from resize_energy.core import economics as eco
from resize_energy.core import pv
from resize_energy.core.wind_design import WindDesign, WindInputs, size_wind_plant


@dataclass(frozen=True)
class CostAssumptions:
    """Prices and costs. The defaults are round placeholders: replace them with local quotes."""

    pv_capex_eur_per_kwp: float = 1000.0
    pv_om_eur_per_kwp_year: float = 15.0
    pv_lifetime_years: float = 25.0
    pv_lifecycle_g_per_kwh: float = 45.0
    wind_capex_eur_per_kw: float = 1500.0
    wind_om_eur_per_kw_year: float = 45.0
    wind_lifetime_years: float = 25.0
    wind_lifecycle_g_per_kwh: float = 11.0
    discount_rate: float = 0.05
    retail_price_eur_per_kwh: float = 0.15
    export_price_eur_per_kwh: float = 0.07
    grid_kg_co2_per_kwh: float = 0.25


@dataclass(frozen=True)
class ComparisonInputs:
    """Same site and demand for both technologies (demand and coverage live in ``wind``)."""

    annual_irradiation_kwh_m2: float
    performance_ratio: float
    wind: WindInputs
    costs: CostAssumptions = field(default_factory=CostAssumptions)

    @property
    def annual_demand_kwh(self) -> float:
        return self.wind.annual_demand_kwh

    @property
    def coverage(self) -> float:
        return self.wind.coverage


@dataclass(frozen=True)
class TechResult:
    """Technical, economic and carbon figures of one technology."""

    name: str
    installed_kw: float
    energy_kwh: float
    coverage: float
    full_load_hours: float
    capex_eur: float
    om_eur_per_year: float
    lifetime_years: float
    lcoe_eur_per_kwh: float
    savings_eur_per_year: float
    net_benefit_eur_per_year: float
    payback_years: float
    discounted_payback_years: float
    npv_eur: float
    co2_avoided_t_per_year: float
    co2_avoided_lifetime_t: float


@dataclass(frozen=True)
class ComparisonResult:
    pv: TechResult
    wind: TechResult
    wind_design: WindDesign
    lowest_lcoe: str
    fastest_payback: str
    highest_npv: str
    most_co2: str


def _tech(name: str, kw: float, energy: float, demand: float, capex_per_kw: float,
          om_per_kw: float, life: float, lifecycle_g: float, c: CostAssumptions) -> TechResult:
    capex = kw * capex_per_kw
    om = kw * om_per_kw
    savings = eco.annual_savings(energy, demand, c.retail_price_eur_per_kwh,
                                 c.export_price_eur_per_kwh)
    net = savings - om
    co2 = eco.co2_avoided_kg_per_year(energy, c.grid_kg_co2_per_kwh, lifecycle_g) / 1000.0
    return TechResult(
        name=name, installed_kw=kw, energy_kwh=energy, coverage=energy / demand,
        full_load_hours=energy / kw, capex_eur=capex, om_eur_per_year=om, lifetime_years=life,
        lcoe_eur_per_kwh=eco.lcoe(capex, om, energy, c.discount_rate, life),
        savings_eur_per_year=savings, net_benefit_eur_per_year=net,
        payback_years=eco.simple_payback_years(capex, net),
        discounted_payback_years=eco.discounted_payback_years(capex, net, c.discount_rate),
        npv_eur=eco.npv(capex, net, c.discount_rate, life),
        co2_avoided_t_per_year=co2, co2_avoided_lifetime_t=co2 * life,
    )


def _best(a: TechResult, b: TechResult, value, lowest: bool = True) -> str:
    va, vb = value(a), value(b)
    if math.isclose(va, vb, rel_tol=1e-9) or (math.isinf(va) and math.isinf(vb)):
        return "tie"
    return (a if (va < vb) == lowest else b).name


def compare_technologies(inp: ComparisonInputs) -> ComparisonResult:
    """Size both plants for the same demand and compute LCOE, payback, NPV and CO2.

    The PV array is sized exactly on the target (no inverter or string limits: use the PV
    module for that); the wind plant uses a whole number of turbines, so it can overshoot.
    """
    c = inp.costs
    if not 0 <= c.discount_rate < 1:
        raise ValueError("discount rate must be in [0, 1)")
    for label, value in (("PV CAPEX", c.pv_capex_eur_per_kwp), ("wind CAPEX",
                         c.wind_capex_eur_per_kw), ("retail price", c.retail_price_eur_per_kwh)):
        if value <= 0:
            raise ValueError(f"{label} must be > 0")
    if inp.annual_irradiation_kwh_m2 <= 0 or not 0 < inp.performance_ratio <= 1:
        raise ValueError("irradiation must be > 0 and performance ratio in (0, 1]")

    kwp = pv.required_peak_power_kwp(inp.annual_demand_kwh, inp.annual_irradiation_kwh_m2,
                                     inp.performance_ratio, inp.coverage)
    pv_energy = kwp * inp.annual_irradiation_kwh_m2 * inp.performance_ratio
    wd = size_wind_plant(inp.wind)

    pv_res = _tech("Photovoltaic", kwp, pv_energy, inp.annual_demand_kwh,
                   c.pv_capex_eur_per_kwp, c.pv_om_eur_per_kwp_year, c.pv_lifetime_years,
                   c.pv_lifecycle_g_per_kwh, c)
    wind_res = _tech("Wind", wd.installed_power_kw, wd.annual_energy_kwh, inp.annual_demand_kwh,
                     c.wind_capex_eur_per_kw, c.wind_om_eur_per_kw_year, c.wind_lifetime_years,
                     c.wind_lifecycle_g_per_kwh, c)
    return ComparisonResult(
        pv=pv_res, wind=wind_res, wind_design=wd,
        lowest_lcoe=_best(pv_res, wind_res, lambda r: r.lcoe_eur_per_kwh),
        fastest_payback=_best(pv_res, wind_res, lambda r: r.payback_years),
        highest_npv=_best(pv_res, wind_res, lambda r: r.npv_eur, lowest=False),
        most_co2=_best(pv_res, wind_res, lambda r: r.co2_avoided_t_per_year, lowest=False),
    )
