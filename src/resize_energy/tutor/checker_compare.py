"""Sanity checks of a technology comparison."""

from __future__ import annotations

from resize_energy.core.comparison import ComparisonInputs, ComparisonResult, ranking_changes
from resize_energy.tutor.checker import Finding


def check_comparison(inp: ComparisonInputs, r: ComparisonResult) -> list[Finding]:
    out: list[Finding] = []
    c = inp.costs
    for t in r.techs:
        if t.lcoe_eur_per_kwh >= t.reference_price_eur_per_kwh:
            what = {"electricity": "buying electricity", "heat": "burning gas for the same heat",
                    }.get(t.product, "buying hydrogen made from natural gas")
            out.append(Finding(
                "warning", "lcoe_above_price",
                f"{t.name}: the LCOE ({t.lcoe_eur_per_kwh:.3f} euro/kWh) is not below the "
                f"reference price ({t.reference_price_eur_per_kwh:.3f}): producing costs more "
                f"than {what}.", "econ.lcoe"))
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
    for note in r.notes:
        out.append(Finding("warning", "tech_left_out", note, "econ.same_demand"))
    if inp.carrier == "heat":
        out += _heat_findings(inp, r)
    wind = r.wind
    if wind is not None and wind.coverage > 1.5:
        out.append(Finding(
            "warning", "wind_oversized",
            f"The wind plant produces {wind.coverage:.0%} of the demand: one turbine is large "
            "for this load and the surplus is valued at the export price. Pick a smaller "
            "turbine, or read the LCOE (independent of size) rather than the payback.",
            "econ.same_demand"))
    hydro = r.hydro
    if hydro is not None:
        out.append(Finding(
            "info", "hydro_not_sized_on_demand",
            f"The hydropower plant is not sized on your demand: it takes the water of the "
            f"river you described and covers {hydro.coverage:.0%} of the demand. Compare its "
            "cost of one kWh with the others; its payback depends on how much of the energy "
            "you use yourself.", "econ.same_demand"))
    geo = r.geothermal
    if geo is not None and geo.coverage > 1.5:
        out.append(Finding(
            "warning", "geothermal_oversized",
            f"The geothermal plant produces {geo.coverage:.0%} of the demand: wells come in "
            "pairs and one pair is large for this load; the surplus is valued at the export "
            "price. Read the cost of one kWh rather than the payback.", "econ.same_demand"))
    if c.export_price_eur_per_kwh > c.retail_price_eur_per_kwh:
        out.append(Finding(
            "info", "export_above_retail",
            "The export price is above the retail price: unusual, check the two values.",
            "econ.savings"))
    if r.hydrogen is not None and len(r.techs) > 1:
        out.append(Finding(
            "info", "mixed_products",
            "Hydrogen is an energy carrier, not electricity: its energy is the lower heating "
            "value of the hydrogen and it is compared with hydrogen made from natural gas, not "
            "with the grid. Producing hydrogen from electricity always costs more than using "
            "that electricity directly; read it as the cost of a molecule you need.",
            "econ.same_demand"))
        if r.hydrogen_design is not None and r.hydrogen_design.profile_source == "synthetic":
            out.append(Finding(
                "info", "synthetic_profile",
                "The hydrogen plant is simulated on an invented hourly year with the yearly "
                "totals of your site: use the hydrogen flow with real hourly data for a better "
                "estimate.", "econ.same_demand"))
    if r.biomass is not None and inp.carrier != "heat":
        out.append(Finding(
            "info", "heat_not_credited",
            "Biogas also produces heat: here only the electricity is valued, so the biomass "
            "result is conservative. Use the biomass flow to value the heat.",
            "econ.savings"))
    out.append(Finding(
        "info", "annual_balance",
        "Annual balance only: the hour-by-hour match of production and consumption (and the "
        "effect of storage) is not modelled, so savings are an upper estimate.",
        "econ.savings"))
    if r.sensitivity:
        changes = ranking_changes(r.sensitivity)
        if changes:
            out.append(Finding(
                "warning", "ranking_unstable",
                "The order of the technologies by cost of energy changes if " +
                " or ".join(changes) + " move by 20 %: the winner depends on numbers you "
                "cannot know well. Look at the other criteria too.", "econ.sensitivity"))
        else:
            out.append(Finding(
                "info", "ranking_stable",
                "The order by cost of energy does not change when capital costs or the "
                "discount rate move by 20 %.", "econ.sensitivity"))
    if not any(f.severity in ("warning", "error") for f in out):
        out.insert(0, Finding("ok", "economics_ok",
                              "Every technology has an LCOE below its reference price and a "
                              "positive NPV with these assumptions.", "econ.lcoe"))
    return out


def _heat_findings(inp: ComparisonInputs, r: ComparisonResult) -> list[Finding]:
    out: list[Finding] = []
    for t in r.techs:
        if t.key == "geothermal" and t.coverage > 1.15 * inp.coverage:
            out.append(Finding(
                "info", "geothermal_pairs",
                f"The geothermal plant covers {t.coverage:.0%} of the heat, more than the "
                f"{inp.coverage:.0%} asked: wells come in pairs and one pair is a large step. "
                "The extra heat is not sold here, so read the cost of one kWh of heat.",
                "econ.same_demand"))
    if r.solar_design is not None:
        out.append(Finding(
            "info", "solar_flat_load",
            "The solar field is sized on a flat, hot-water type load. Space heating peaks in "
            "winter when the sun is weakest, so for a heating load the real solar share would "
            "be lower: use the solar thermal flow for a detailed case.", "econ.same_demand"))
    bhe = r.bhe_design
    if bhe is not None:
        out.append(Finding(
            "info", "heat_pump_electricity",
            "The heat pump runs on electricity: its cost and emissions use the retail price "
            "and the grid emission factor, so its result depends on the grid you are in.",
            "econ.lcoe"))
        if getattr(bhe, "warnings", ()):
            out.append(Finding(
                "warning", "bhe_ground_warnings",
                "Ground-source heat pump: " + "; ".join(bhe.warnings) + ". A heating-only field "
                "cools the ground year after year: check it in the ground-source flow.",
                "econ.same_demand"))
    return out
