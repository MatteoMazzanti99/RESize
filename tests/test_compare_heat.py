"""The comparison of heat technologies and the choice of what to compare."""

from dataclasses import replace

import pytest

from resize_energy.core.comparison import (
    ALL_TECHS,
    ComparisonInputs,
    compare_technologies,
    comparison_sensitivity,
    possible_carriers,
)
from resize_energy.core.comparison_heat import HeatInputs, scaled_heat
from resize_energy.core.wind_design import WindInputs
from resize_energy.report.charts import comparison_charts
from resize_energy.report.html_report import build_comparison_report
from resize_energy.tutor.checker_compare import check_comparison
from resize_energy.tutor.context_compare import build_compare_context
from resize_energy.tutor.worked_compare import compare_worked_example


def heat_case(techs=("biomass", "geothermal", "solar", "bhe"), **kw):
    wind = WindInputs(annual_demand_kwh=10_000_000, mean_speed_ref_ms=6.5)
    inp = ComparisonInputs(1500, 0.8, wind, techs=tuple(techs), carrier="heat",
                           heat=kw.pop("heat", HeatInputs()), **kw)
    return inp, compare_technologies(inp)


def test_possible_carriers_need_two_technologies_each():
    assert possible_carriers(("pv", "wind")) == ("electricity",)
    assert possible_carriers(("hydro", "geothermal")) == ("electricity",)
    assert possible_carriers(("solar", "bhe")) == ("heat",)
    assert possible_carriers(("biomass", "geothermal")) == ("electricity", "heat", "both")
    assert possible_carriers(("pv", "solar")) == ()
    assert possible_carriers(("pv", "wind", "solar", "bhe")) == ("electricity", "heat", "both")
    assert possible_carriers(("pv",)) == ()
    assert set(ALL_TECHS) >= {"solar", "bhe"}


def test_four_heat_technologies_share_one_demand():
    inp, r = heat_case()
    assert [t.key for t in r.techs] == ["biomass", "geothermal", "solar", "bhe"]
    h = inp.heat
    for t in r.techs:
        assert t.product == "heat" and t.capex_eur > 0 and t.lcoe_eur_per_kwh > 0
        assert t.reference_price_eur_per_kwh == pytest.approx(h.costs.gas_heat_eur_per_kwh)
    # boiler, solar and heat pump cover the share asked; the doublet comes in whole well pairs
    for key in ("biomass", "solar", "bhe"):
        assert r.get(key).energy_kwh == pytest.approx(h.coverage * h.annual_heat_kwh, rel=0.01)
    assert r.geothermal.coverage >= h.coverage - 1e-9
    assert r.lowest_lcoe in {t.name for t in r.techs}
    assert inp.annual_demand_kwh == h.annual_heat_kwh and inp.coverage == h.coverage


def test_heat_pump_electricity_is_a_running_cost():
    inp, r = heat_case(("solar", "bhe"))
    bhe, c, h = r.get("bhe"), inp.costs, inp.heat
    drilling_om = r.bhe_design.om_per_year
    elec = bhe.energy_kwh / h.bhe.cop_seasonal * c.retail_price_eur_per_kwh
    assert bhe.om_eur_per_year == pytest.approx(drilling_om + elec)
    # the CO2 of the heat pump is the grid electricity it uses per kWh of heat
    assert bhe.co2_own_kg_per_kwh == pytest.approx(c.grid_kg_co2_per_kwh / h.bhe.cop_seasonal)


def test_gas_is_the_reference_for_savings_and_co2():
    inp, r = heat_case(("biomass", "geothermal"))
    hc = inp.heat.costs
    t = r.get("biomass")
    assert t.savings_eur_per_year == pytest.approx(t.energy_kwh * hc.gas_heat_eur_per_kwh)
    ref_ef = hc.gas_kg_co2_per_kwh_fuel / hc.gas_boiler_efficiency
    assert t.co2_reference_kg_per_kwh == pytest.approx(ref_ef)
    assert t.co2_avoided_t_per_year == pytest.approx(
        t.energy_kwh * (ref_ef - t.co2_own_kg_per_kwh) / 1000)


def test_a_field_too_large_for_the_ground_is_left_out_with_a_note():
    big = HeatInputs(annual_heat_kwh=30_000_000, peak_kw=12_000)
    # one technology only left: that is not a comparison
    with pytest.raises(ValueError, match="fewer than two"):
        heat_case(("biomass", "bhe"), heat=big)
    inp3, r3 = heat_case(("biomass", "solar", "bhe"), heat=big)
    assert {t.key for t in r3.techs} == {"biomass", "solar"}
    assert any("Ground-source heat pump left out" in n for n in r3.notes)
    findings = check_comparison(inp3, r3)
    assert any(f.code == "tech_left_out" for f in findings)


def test_errors_are_readable():
    wind = WindInputs(annual_demand_kwh=1e7, mean_speed_ref_ms=6.5)
    mk = lambda **kw: ComparisonInputs(  # noqa: E731
        1500, 0.8, wind, techs=("biomass", "solar"), carrier="heat", heat=HeatInputs(**kw))
    with pytest.raises(ValueError, match="peak"):
        compare_technologies(mk(annual_heat_kwh=1e7, peak_kw=100))
    with pytest.raises(ValueError, match="coverage|share"):
        compare_technologies(mk(coverage=0.0))
    with pytest.raises(ValueError, match="two"):
        compare_technologies(replace(mk(), techs=("biomass",)))
    with pytest.raises(ValueError, match="unknown"):
        compare_technologies(replace(mk(), techs=("biomass", "pv")))


def test_the_electricity_comparison_is_unchanged():
    wind = WindInputs(annual_demand_kwh=10_000_000, mean_speed_ref_ms=6.5)
    inp = ComparisonInputs(1500, 0.8, wind, techs=("pv", "wind"))
    assert inp.carrier == "electricity" and inp.annual_demand_kwh == 10_000_000
    r = compare_technologies(inp)
    assert [t.product for t in r.techs] == ["electricity", "electricity"]
    assert r.notes == ()


def test_scaled_capital_costs_move_every_heat_technology():
    inp, base = heat_case(("biomass", "solar", "geothermal"))
    scaled = replace(inp, heat=scaled_heat(inp.heat, 1.2))
    up = compare_technologies(scaled)
    for key in ("biomass", "solar", "geothermal"):
        assert up.get(key).capex_eur > base.get(key).capex_eur
    sens = comparison_sensitivity(inp)
    assert set(sens["capex"]) == {"biomass", "solar", "geothermal"}
    for values in sens["capex"].values():
        assert values[-1] > values[0]


def test_report_charts_tutor_follow_the_heat():
    inp, r = heat_case(("biomass", "geothermal", "solar"))
    r = replace(r, sensitivity=comparison_sensitivity(inp))
    findings = check_comparison(inp, r)
    html = build_comparison_report(inp, r, findings)
    assert "Technology comparison (heat)" in html and "Cost of heat (LCOH)" in html
    assert "Reference: heat from a gas boiler" in html and "Which is better" in html
    charts = comparison_charts(inp, r)
    assert {"cmp_lcoe", "cmp_cash"} <= set(charts)
    assert any(label == "gas heat" for _, label in charts["cmp_lcoe"].vlines)
    assert any(f.code == "solar_flat_load" for f in findings)
    ctx = build_compare_context(inp, r, findings)
    assert "heat demand" in ctx.lower() and "LCOH" in ctx
    assert "gas heat not bought" in compare_worked_example("econ.savings", inp, r)
    assert "Target heat" in compare_worked_example("econ.same_demand", inp, r)


def test_project_file_keeps_the_kind_of_comparison():
    from resize_energy.core import project_file as pf

    text = pf.dumps(pf.Project(tech="compare", compare_techs=("biomass", "solar"),
                               compare_carrier="heat"))
    project = pf.loads(text)
    assert project.compare_carrier == "heat" and project.compare_techs == ("biomass", "solar")
    old = pf.loads(text.replace('"compare_carrier": "heat",', ""))
    assert old.compare_carrier == "electricity"
    with pytest.raises(pf.ProjectError):
        pf.loads(text.replace('"heat"', '"steam"'))


def test_line_source_penalty_matches_the_pair_by_pair_sum():
    import math

    from resize_energy.core import bhe

    def brute(n, cols, spacing, alpha, cond, years, q):
        t = years * 365 * 86400
        pos = [((k // cols) * spacing, (k % cols) * spacing) for k in range(n)]
        total = sum(
            bhe.exp_integral_e1(((pos[a][0] - pos[b][0]) ** 2 + (pos[a][1] - pos[b][1]) ** 2)
                                / (4 * alpha * t))
            for a in range(n) for b in range(n) if a != b)
        return q / (4 * math.pi * cond) * total / n

    for n, cols in ((2, 1), (7, 3), (12, 4), (13, 5), (31, 1), (30, 6)):
        assert bhe.line_source_penalty(n, cols, 6.0, 8e-7, 1.8, 10, 20) == pytest.approx(
            brute(n, cols, 6.0, 8e-7, 1.8, 10, 20), rel=1e-9)
