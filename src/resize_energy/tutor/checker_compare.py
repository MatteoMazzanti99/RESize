"""Sanity checks of a technology comparison."""

from __future__ import annotations

from resize_energy.core.comparison import ComparisonInputs, ComparisonResult
from resize_energy.tutor.checker import Finding


def check_comparison(inp: ComparisonInputs, r: ComparisonResult) -> list[Finding]:
    out: list[Finding] = []
    c = inp.costs
    for t in (r.pv, r.wind):
        if t.lcoe_eur_per_kwh >= c.retail_price_eur_per_kwh:
            out.append(Finding(
                "warning", "lcoe_above_price",
                f"{t.name}: the LCOE ({t.lcoe_eur_per_kwh:.3f} euro/kWh) is not below the retail "
                f"price ({c.retail_price_eur_per_kwh:.3f}): producing costs more than buying.",
                "econ.lcoe"))
        if t.npv_eur < 0:
            out.append(Finding(
                "warning", "negative_npv",
                f"{t.name}: negative net present value ({t.npv_eur:,.0f} euro): with these "
                "prices the project does not earn the discount rate.", "econ.payback"))
        elif t.payback_years > 0.8 * t.lifetime_years:
            out.append(Finding(
                "warning", "slow_payback",
                f"{t.name}: payback of {t.payback_years:.0f} years is close to the lifetime "
                f"({t.lifetime_years:.0f} years).", "econ.payback"))
    if r.wind.coverage > 1.5:
        out.append(Finding(
            "warning", "wind_oversized",
            f"The wind plant produces {r.wind.coverage:.0%} of the demand: one turbine is large "
            "for this load and the surplus is valued at the export price. Pick a smaller "
            "turbine, or read the LCOE (independent of size) rather than the payback.",
            "econ.same_demand"))
    if c.export_price_eur_per_kwh > c.retail_price_eur_per_kwh:
        out.append(Finding(
            "info", "export_above_retail",
            "The export price is above the retail price: unusual, check the two values.",
            "econ.savings"))
    out.append(Finding(
        "info", "annual_balance",
        "Annual balance only: the hour-by-hour match of production and consumption (and the "
        "effect of storage) is not modelled, so savings are an upper estimate.",
        "econ.savings"))
    if not any(f.severity in ("warning", "error") for f in out):
        out.insert(0, Finding("ok", "economics_ok",
                              "Both technologies have an LCOE below the retail price and a "
                              "positive NPV with these assumptions.", "econ.lcoe"))
    return out
