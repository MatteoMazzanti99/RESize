"""Plain-text summary of a technology comparison for the AI tutor."""

from __future__ import annotations

from resize_energy.core.comparison import ComparisonInputs, ComparisonResult
from resize_energy.tutor.checker import Finding

_SEVERITY = {"error": "ERROR", "warning": "WARNING", "info": "NOTE", "ok": "OK"}


def _years(v: float) -> str:
    return "never" if v == float("inf") else f"{v:.1f} y"


def build_compare_context(inp: ComparisonInputs, r: ComparisonResult,
                          findings: list[Finding]) -> str:
    c = inp.costs
    names = ", ".join(t.name for t in r.techs)
    lines = [
        f"PROJECT: comparison of {names} for the same energy target (RESize)",
        "",
        "INPUTS",
        f"- Energy demand {inp.annual_demand_kwh:,.0f} kWh/year, coverage {inp.coverage:.0%}",
        f"- Irradiation {inp.annual_irradiation_kwh_m2:,.0f} kWh/m2, PR "
        f"{inp.performance_ratio:.2f}; wind {inp.wind.mean_speed_ref_ms:.2f} m/s at "
        f"{inp.wind.ref_height_m:.0f} m, turbine {inp.wind.turbine.name} "
        f"({inp.wind.turbine.rated_power_kw:,.0f} kW)",
        f"- PV: {c.pv_capex_eur_per_kwp:,.0f} euro/kWp, O&M {c.pv_om_eur_per_kwp_year:,.0f} "
        f"euro/kWp/y, life {c.pv_lifetime_years:.0f} y, {c.pv_lifecycle_g_per_kwh:.0f} g/kWh",
        f"- Wind: {c.wind_capex_eur_per_kw:,.0f} euro/kW, O&M {c.wind_om_eur_per_kw_year:,.0f} "
        f"euro/kW/y, life {c.wind_lifetime_years:.0f} y, {c.wind_lifecycle_g_per_kwh:.0f} g/kWh",
        f"- Biogas CHP: {c.bio_capex_eur_per_kwe:,.0f} euro/kWe, O&M "
        f"{c.bio_om_eur_per_kwe_year:,.0f} euro/kWe/y, feedstock {c.bio_feedstock_eur_per_t:,.0f} "
        f"euro/t, life {c.bio_lifetime_years:.0f} y, {c.bio_lifecycle_g_per_kwh:.0f} g/kWh",
        f"- Hydrogen: electrolyser {c.h2_electrolyser_capex_eur_per_kw:,.0f} euro/kW; reference "
        f"{c.h2_reference_price_eur_per_kg:.2f} euro/kg and "
        f"{c.h2_reference_kg_co2_per_kg:.1f} kg CO2/kg",
        f"- Discount rate {c.discount_rate:.1%}; retail {c.retail_price_eur_per_kwh:.3f}, export "
        f"{c.export_price_eur_per_kwh:.3f} euro/kWh; grid {c.grid_kg_co2_per_kwh:.3f} kg CO2/kWh",
        "(only the technologies listed in RESULTS were compared)",
        "",
        "RESULTS",
    ]
    for t in r.techs:
        lines.append(
            f"- {t.name}: {t.installed_kw:,.0f} kW, {t.energy_kwh:,.0f} kWh/y {t.product} "
            f"({t.coverage:.0%} of demand), CAPEX {t.capex_eur:,.0f}, LCOE "
            f"{t.lcoe_eur_per_kwh:.4f} euro/kWh, payback {_years(t.payback_years)}, NPV "
            f"{t.npv_eur:,.0f}, CO2 avoided {t.co2_avoided_t_per_year:,.0f} t/y")
    lines += [
        f"- Lowest LCOE: {r.lowest_lcoe}; fastest payback: {r.fastest_payback}; highest NPV: "
        f"{r.highest_npv}; most CO2 avoided: {r.most_co2}",
        "",
        "CHECKS",
    ]
    lines += [f"- [{_SEVERITY[f.severity]}] {f.message}" for f in findings]
    return "\n".join(lines)
