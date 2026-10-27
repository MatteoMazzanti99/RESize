"""Worked examples of the comparison topics, with the user's own numbers."""

from __future__ import annotations

from resize_energy.core import economics as eco
from resize_energy.core.comparison import ComparisonInputs, ComparisonResult, ranking_changes


def _years(value: float) -> str:
    return "never" if value == float("inf") else f"{value:.1f} years"


def compare_worked_example(key: str, inp: ComparisonInputs, r: ComparisonResult) -> str | None:
    c = inp.costs
    d = inp.annual_demand_kwh
    if key == "econ.same_demand":
        out = [f"Target energy: {inp.coverage:.0%} of {d:,.0f} kWh = {inp.coverage * d:,.0f} kWh"]
        for t in r.techs:
            extra = ""
            if t.key == "wind" and r.wind_design is not None:
                extra = (f" ({r.wind_design.n_turbines} x "
                         f"{inp.wind.turbine.rated_power_kw:,.0f} kW turbines)")
            if t.key == "hydro":
                extra = " (the river decides, not the demand)"
            if t.key == "geothermal" and r.geothermal_design is not None:
                extra = f" ({r.geothermal_design.wells_pairs} well pair(s))"
            if t.key == "hydrogen":
                extra = f" (hydrogen, {t.energy_kwh / 33.33:,.0f} kg at 33.33 kWh/kg)"
            out.append(f"{t.name}: {t.installed_kw:,.0f} kW -> {t.energy_kwh:,.0f} kWh "
                       f"({t.coverage:.0%} of the demand){extra}")
        return "\n".join(out)
    if key == "econ.crf":
        return "\n".join(
            f"{t.name}: r = {c.discount_rate:.1%}, n = {t.lifetime_years:.0f} -> CRF = "
            f"{eco.capital_recovery_factor(c.discount_rate, t.lifetime_years):.5f}"
            for t in r.techs)
    if key == "econ.lcoe":
        out = []
        for t in r.techs:
            if t.key == "hydrogen" and r.hydrogen_design is not None:
                out.append(f"{t.name}: LCOH {r.hydrogen_design.lcoh:.2f} euro/kg / 33.33 kWh/kg "
                           f"= {t.lcoe_eur_per_kwh:.4f} euro/kWh (full cost build-up in the "
                           "hydrogen flow)")
                continue
            crf = eco.capital_recovery_factor(c.discount_rate, t.lifetime_years)
            out.append(
                f"{t.name}: ({t.capex_eur:,.0f} x {crf:.5f} + {t.om_eur_per_year:,.0f}) / "
                f"{t.energy_kwh:,.0f} = {t.lcoe_eur_per_kwh:.4f} euro/kWh")
        out.append("Reference prices: " + ", ".join(
            f"{t.name} {t.reference_price_eur_per_kwh:.4f}" for t in r.techs) + " euro/kWh")
        return "\n".join(out)
    if key == "econ.savings":
        out = []
        for t in r.techs:
            if t.product == "hydrogen":
                out.append(f"{t.name}: {t.energy_kwh:,.0f} x {t.reference_price_eur_per_kwh:.4f} "
                           f"= {t.savings_eur_per_year:,.0f} euro/year (hydrogen not bought)")
                continue
            useful = min(t.energy_kwh, d)
            surplus = max(0.0, t.energy_kwh - d)
            out.append(
                f"{t.name}: {useful:,.0f} x {c.retail_price_eur_per_kwh:.3f} + {surplus:,.0f} x "
                f"{c.export_price_eur_per_kwh:.3f} = {t.savings_eur_per_year:,.0f} euro/year"
            )
        return "\n".join(out)
    if key == "econ.payback":
        out = []
        for t in r.techs:
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
        for t in r.techs:
            out.append(
                f"{t.name}: {t.energy_kwh:,.0f} x ({t.co2_reference_kg_per_kwh:.3f} - "
                f"{t.co2_own_kg_per_kwh:.3f}) = {t.co2_avoided_t_per_year * 1000:,.0f} kg/year = "
                f"{t.co2_avoided_t_per_year:,.0f} t/year ({t.co2_avoided_lifetime_t:,.0f} t over "
                f"{t.lifetime_years:.0f} years)"
            )
        return "\n".join(out)
    if key == "econ.sensitivity":
        if not r.sensitivity:
            return ("Not computed here; base cost of one kWh: " + ", ".join(
                f"{t.name} {t.lcoe_eur_per_kwh:.3f}" for t in r.techs) + " euro/kWh.")
        out = []
        for name, label in (("capex", "capital costs"), ("rate", "discount rate")):
            data = r.sensitivity.get(name, {})
            for t in r.techs:
                if t.key in data:
                    v = data[t.key]
                    out.append(f"{label}: {t.name} {v[0]:.3f} -> {v[-1]:.3f} euro/kWh "
                               f"(-20 % to +20 %)")
        changes = ranking_changes(r.sensitivity)
        out.append("The ranking changes with " + " and ".join(changes) + "." if changes
                   else "The ranking by cost does not change within +/- 20 %.")
        return "\n".join(out)
    return None
