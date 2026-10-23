import math
from dataclasses import replace

import pytest

from resize_energy.core import economics as eco
from resize_energy.core.plant_economics import (
    EconomicInputs,
    economics_sensitivity,
    evaluate_economics,
)
from resize_energy.core.pv_design import PVInputs, size_pv_system
from resize_energy.core.wind_design import WindInputs, size_wind_plant
from resize_energy.report.charts import pv_charts, wind_charts
from resize_energy.report.html_report import build_pv_report, build_wind_report
from resize_energy.tutor.checker import check_pv_design
from resize_energy.tutor.checker_wind import check_wind_design
from resize_energy.tutor.context import build_project_context
from resize_energy.tutor.context_wind import build_wind_context
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.worked import worked_example
from resize_energy.tutor.worked_wind import wind_worked_example

E = EconomicInputs()


def pv_case(econ=E, **kw):
    inp = PVInputs(annual_demand_kwh=4500, annual_irradiation_kwh_m2=1500, economics=econ, **kw)
    return inp, size_pv_system(inp)


WIND_E = EconomicInputs(capex_per_kw=1700, om_per_kw_year=45)


def wind_case(econ=WIND_E, **kw):
    inp = WindInputs(annual_demand_kwh=3_000_000, mean_speed_ref_ms=6.5, economics=econ, **kw)
    return inp, size_wind_plant(inp)


def test_hand_calculation():
    r = evaluate_economics(4.0, 4800.0, 6000.0, E)
    assert r.capex == pytest.approx(4000.0)
    assert r.savings_per_year == pytest.approx(4800 * 0.20)          # all used on site
    assert r.net_benefit_per_year == pytest.approx(960 - 60)
    assert r.payback_years == pytest.approx(4000 / 900)
    crf = eco.capital_recovery_factor(0.05, 25)
    assert r.lcoe == pytest.approx((4000 * crf + 60) / 4800)
    assert r.npv == pytest.approx(-4000 + 900 * eco.annuity_factor(0.05, 25))
    assert r.cash[0] == -4000 and r.cash[-1] == pytest.approx(r.npv)
    assert r.co2_avoided_t_per_year == pytest.approx(4800 * (0.25 - 0.045) / 1000)


def test_surplus_is_exported():
    r = evaluate_economics(4.0, 4800.0, 3000.0, E)
    assert r.self_used_kwh == 3000 and r.exported_kwh == 1800
    assert r.savings_per_year == pytest.approx(3000 * 0.20 + 1800 * 0.07)


def test_rejects_bad_numbers():
    with pytest.raises(ValueError):
        evaluate_economics(0, 100, 100, E)
    with pytest.raises(ValueError):
        evaluate_economics(1, 100, 100, replace(E, discount_rate=1.5))
    with pytest.raises(ValueError):
        evaluate_economics(1, 100, 100, replace(E, retail_price=0))


def test_fractional_life_ends_at_npv():
    r = evaluate_economics(4.0, 4800.0, 6000.0, replace(E, life_years=12.5))
    assert len(r.cash) == 14 and r.cash[-1] == pytest.approx(r.npv)


def test_sensitivity_orders_and_flips():
    s = economics_sensitivity(4.0, 4800.0, 6000.0, E)
    swings = [c.swing for c in s.curves]
    assert swings == sorted(swings, reverse=True)
    assert s.base == pytest.approx(evaluate_economics(4.0, 4800.0, 6000.0, E).npv)
    weak = economics_sensitivity(4.0, 4800.0, 6000.0, replace(E, capex_per_kw=3000))
    assert any(min(c.values) < 0 < max(c.values) for c in weak.curves)


def test_pv_and_wind_designs_carry_economics():
    inp, d = pv_case()
    assert d.economics is not None and d.economics.sensitivity is not None
    assert d.economics.capex == pytest.approx(d.dc_power_kwp * 1000)
    assert math.isfinite(d.economics.lcoe)
    winp, wd = wind_case()
    assert wd.economics is not None
    assert wd.economics.capex == pytest.approx(wd.installed_power_kw * 1700)


def test_without_economics_nothing_changes():
    _, d = pv_case(econ=None)
    assert d.economics is None
    _, wd = wind_case(econ=None)
    assert wd.economics is None


def test_tutor_keys_have_digit_examples_in_both_states():
    for key in ("pv.economics", "pv.sensitivity"):
        assert key in EXPLANATIONS
        for econ in (E, None):
            inp, d = pv_case(econ=econ)
            text = worked_example(key, inp, d)
            assert text and any(c.isdigit() for c in text)
    for key in ("wind.economics", "wind.sensitivity"):
        for econ in (EconomicInputs(), None):
            inp, d = wind_case(econ=econ)
            text = wind_worked_example(key, inp, d)
            assert text and any(c.isdigit() for c in text)


def test_checker_and_context():
    inp, d = pv_case()
    findings = check_pv_design(inp, d)
    assert any(f.explanation_key == "pv.economics" for f in findings)
    assert "COSTS AND SAVINGS" in build_project_context(inp, d, findings)
    bad, bd = pv_case(econ=replace(E, capex_per_kw=6000))
    assert any(f.code in ("lcoe_above_retail", "npv_negative")
               for f in check_pv_design(bad, bd))
    winp, wd = wind_case()
    assert any(f.explanation_key.startswith("wind.") and "econom" in f.code or f.code == "economics"
               for f in check_wind_design(winp, wd))
    assert "COSTS AND SAVINGS" in build_wind_context(winp, wd, [])


def test_charts_and_reports_show_economics():
    inp, d = pv_case()
    charts = pv_charts(inp, d)
    assert {"pv_cash", "pv_unit_cost", "pv_sens_swing", "pv_sens_spider"} <= set(charts)
    html = build_pv_report(inp, d, check_pv_design(inp, d))
    assert "Net present value" in html and "Costs, savings and payback" in html
    winp, wd = wind_case()
    assert {"wind_cash", "wind_sens_swing"} <= set(wind_charts(winp, wd))
    assert "Net present value" in build_wind_report(winp, wd, check_wind_design(winp, wd))
    plain, pd = pv_case(econ=None)
    assert "Net present value" not in build_pv_report(plain, pd, check_pv_design(plain, pd))
