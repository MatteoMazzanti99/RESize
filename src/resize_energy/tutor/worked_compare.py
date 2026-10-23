"""Worked examples of the comparison topics, with the user's own numbers."""

from __future__ import annotations

from resize_energy.core import economics as eco
from resize_energy.core.comparison import ComparisonInputs, ComparisonResult


def _years(value: float) -> str:
    return "never" if value == float("inf") else f"{value:.1f} years"


def compare_worked_example(key: str, inp: ComparisonInputs, r: ComparisonResult) -> str | None:
    c = inp.costs
    d = inp.annual_demand_kwh
    w = inp.wind
    if key == "econ.same_demand":
        return (
            f"Target energy: {inp.coverage:.0%} of {d:,.0f} kWh = {inp.coverage * d:,.0f} kWh\n"
            f"PV: P = {r.pv.installed_kw:,.0f} kWp -> {r.pv.energy_kwh:,.0f} kWh "
            f"({r.pv.coverage:.0%} of the demand)\n"
            f"Wind: {r.wind_design.n_turbines} x {w.turbine.rated_power_kw:,.0f} kW "
            f"-> {r.wind.energy_kwh:,.0f} kWh ({r.wind.coverage:.0%} of the demand)"
        )
    if key == "econ.crf":
        return (
            f"PV:   r = {c.discount_rate:.1%}, n = {c.pv_lifetime_years:.0f} -> CRF = "
            f"{eco.capital_recovery_factor(c.discount_rate, c.pv_lifetime_years):.5f}\n"
            f"Wind: r = {c.discount_rate:.1%}, n = {c.wind_lifetime_years:.0f} -> CRF = "
            f"{eco.capital_recovery_factor(c.discount_rate, c.wind_lifetime_years):.5f}"
        )
    if key == "econ.lcoe":
        out = []
        for t, crf_n in ((r.pv, c.pv_lifetime_years), (r.wind, c.wind_lifetime_years)):
            crf = eco.capital_recovery_factor(c.discount_rate, crf_n)
            out.append(
                f"{t.name}: ({t.capex_eur:,.0f} x {crf:.5f} + {t.om_eur_per_year:,.0f}) / "
                f"{t.energy_kwh:,.0f} = {t.lcoe_eur_per_kwh:.4f} euro/kWh"
            )
        out.append(f"Retail price for comparison: {c.retail_price_eur_per_kwh:.4f} euro/kWh")
        return "\n".join(out)
    if key == "econ.savings":
        out = []
        for t in (r.pv, r.wind):
            useful = min(t.energy_kwh, d)
            surplus = max(0.0, t.energy_kwh - d)
            out.append(
                f"{t.name}: {useful:,.0f} x {c.retail_price_eur_per_kwh:.3f} + {surplus:,.0f} x "
                f"{c.export_price_eur_per_kwh:.3f} = {t.savings_eur_per_year:,.0f} euro/year"
            )
        return "\n".join(out)
    if key == "econ.payback":
        out = []
        for t in (r.pv, r.wind):
            out.append(
                f"{t.name}: net benefit {t.savings_eur_per_year:,.0f} - "
                f"{t.om_eur_per_year:,.0f} = {t.net_benefit_eur_per_year:,.0f} euro/year\n"
                f"  payback = {t.capex_eur:,.0f} / {t.net_benefit_eur_per_year:,.0f} = "
                f"{_years(t.payback_years)}; discounted payback {_years(t.discounted_payback_years)}"
                f"; NPV = {t.npv_eur:,.0f} euro"
            )
        return "\n".join(out)
    if key == "econ.co2":
        out = []
        for t, life in ((r.pv, c.pv_lifecycle_g_per_kwh), (r.wind, c.wind_lifecycle_g_per_kwh)):
            out.append(
                f"{t.name}: {t.energy_kwh:,.0f} x ({c.grid_kg_co2_per_kwh:.3f} - "
                f"{life / 1000:.3f}) = {t.co2_avoided_t_per_year * 1000:,.0f} kg/year = "
                f"{t.co2_avoided_t_per_year:,.0f} t/year ({t.co2_avoided_lifetime_t:,.0f} t over "
                f"{t.lifetime_years:.0f} years)"
            )
        return "\n".join(out)
    return None
