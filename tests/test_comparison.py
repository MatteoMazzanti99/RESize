import math

import pytest

from resize_energy.core import economics as eco
from resize_energy.core.comparison import ComparisonInputs, CostAssumptions, compare_technologies
from resize_energy.core.wind_design import WindInputs
from resize_energy.report.html_report import build_comparison_report
from resize_energy.tutor.checker_compare import check_comparison
from resize_energy.tutor.context_compare import build_compare_context
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.explanations_compare import COMPARE_TOPIC_ORDER
from resize_energy.tutor.worked_compare import compare_worked_example


def case(**kw):
    costs = kw.pop("costs", CostAssumptions())
    wind = WindInputs(annual_demand_kwh=kw.pop("demand", 10_000_000), mean_speed_ref_ms=6.5)
    inp = ComparisonInputs(1500, 0.8, wind, costs)
    return inp, compare_technologies(inp)


def test_capital_recovery_factor_hand_value():
    # 0.05 * 1.05^25 / (1.05^25 - 1) = 0.0709525
    assert eco.capital_recovery_factor(0.05, 25) == pytest.approx(0.0709525, rel=1e-5)
    assert eco.capital_recovery_factor(0, 20) == pytest.approx(0.05)
    assert eco.annuity_factor(0.05, 25) * eco.capital_recovery_factor(0.05, 25) == pytest.approx(1)


def test_lcoe_hand_value():
    # PV: (1000 x CRF + 15) / 1200 kWh per kWp
    expected = (1000 * 0.0709525 + 15) / 1200
    assert eco.lcoe(1000, 15, 1200, 0.05, 25) == pytest.approx(expected, rel=1e-5)


def test_savings_split_between_retail_and_export():
    assert eco.annual_savings(800, 1000, 0.2, 0.05) == pytest.approx(160)
    assert eco.annual_savings(1500, 1000, 0.2, 0.05) == pytest.approx(200 + 25)


def test_payback_npv_consistency():
    assert eco.simple_payback_years(1000, 100) == 10
    assert math.isinf(eco.simple_payback_years(1000, 0))
    # NPV is zero exactly at the discounted payback horizon
    n = eco.discounted_payback_years(1000, 150, 0.05)
    assert eco.npv(1000, 150, 0.05, n) == pytest.approx(0, abs=1e-6)
    assert math.isinf(eco.discounted_payback_years(1000, 40, 0.05))  # 40/0.05 = 800 < 1000
    assert eco.discounted_payback_years(1000, 100, 0) == 10


def test_co2_uses_grid_minus_lifecycle():
    assert eco.co2_avoided_kg_per_year(1000, 0.25, 45) == pytest.approx(205)


def test_both_plants_cover_the_demand_and_numbers_are_consistent():
    inp, r = case()
    assert r.pv.coverage == pytest.approx(1.0)
    assert r.wind.coverage >= 1.0
    c = inp.costs
    assert r.pv.capex_eur == pytest.approx(r.pv.installed_kw * c.pv_capex_eur_per_kwp)
    assert r.pv.lcoe_eur_per_kwh == pytest.approx(
        eco.lcoe(r.pv.capex_eur, r.pv.om_eur_per_year, r.pv.energy_kwh, c.discount_rate, 25))
    assert r.wind.co2_avoided_lifetime_t == pytest.approx(r.wind.co2_avoided_t_per_year * 25)
    assert r.lowest_lcoe in {"Photovoltaic", "Wind"}


def test_cheaper_pv_wins_the_cost_ranking():
    inp, r = case(costs=CostAssumptions(pv_capex_eur_per_kwp=300))
    assert r.lowest_lcoe == "Photovoltaic"
    assert r.fastest_payback == "Photovoltaic"


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        case(costs=CostAssumptions(discount_rate=-0.1))
    with pytest.raises(ValueError):
        case(costs=CostAssumptions(pv_capex_eur_per_kwp=0))


def test_tutor_pieces_work_together():
    inp, r = case()
    findings = check_comparison(inp, r)
    assert all(f.explanation_key in EXPLANATIONS for f in findings if f.explanation_key)
    assert "annual_balance" in {f.code for f in findings}
    for key in COMPARE_TOPIC_ORDER:
        entry = EXPLANATIONS[key]
        assert entry["title"] and entry["formula"] and entry["why"] and entry["assumptions"]
        text = compare_worked_example(key, inp, r)
        assert text and any(ch.isdigit() for ch in text), key
    assert compare_worked_example("nope", inp, r) is None
    assert "Photovoltaic" in build_compare_context(inp, r, findings)
    for theme in ("light", "screen"):
        html = build_comparison_report(inp, r, findings, theme=theme)
        assert "Which is better" in html and "LCOE" in html


def test_oversized_wind_and_expensive_energy_are_flagged():
    inp, r = case(demand=500_000)  # one 2 MW turbine on a tiny demand
    codes = {f.code for f in check_comparison(inp, r)}
    assert "wind_oversized" in codes
    inp2, r2 = case(costs=CostAssumptions(retail_price_eur_per_kwh=0.03))
    assert "lcoe_above_price" in {f.code for f in check_comparison(inp2, r2)}
