import math
from dataclasses import replace

import pytest

from resize_energy.core import economics as eco
from resize_energy.core import solar_thermal as st
from resize_energy.core.solar_thermal_design import (
    SolarThermalInputs,
    size_solar_thermal,
)
from resize_energy.report.charts import solar_charts
from resize_energy.report.html_report import build_solar_report
from resize_energy.tutor.checker_solar import check_solar_design
from resize_energy.tutor.context_solar import build_solar_context
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.explanations_solar import SOLAR_TOPIC_ORDER
from resize_energy.tutor.worked_solar import solar_worked_example

COOL = SolarThermalInputs(dhw_litres_per_day=0, cooling_kwh_per_year=12000, collector="tube",
                          latitude_deg=38, irradiation_kwh_m2=1750, t_mean_c=17, area_m2=30)


def weather(inp=None):
    inp = inp or SolarThermalInputs()
    return st.synthetic_weather(inp.latitude_deg, inp.irradiation_kwh_m2, inp.t_mean_c,
                                inp.t_season_amp_c)


def test_collector_efficiency_by_hand():
    c = st.COLLECTORS["flat"]
    assert st.collector_efficiency(c, 60, 20, 800) == pytest.approx(
        c.eta0 - c.a1 * 40 / 800 - c.a2 * 1600 / 800)
    assert st.collector_efficiency(c, 100, 0, 100) == 0.0            # never negative
    assert st.collector_efficiency(c, 60, 20, 0) == 0.0


def test_weather_matches_the_requested_irradiation():
    w = weather()
    assert sum(w.g_w_m2) / 1000 == pytest.approx(1400, rel=1e-9)
    assert sum(w.t_amb_c) / 8760 == pytest.approx(12.0, abs=0.3)
    south = st.synthetic_weather(-35, 1500, 16, 8)
    assert south.t_amb_c[196 * 24 + 15] < south.t_amb_c[15 * 24 + 15]   # July is winter there


def test_hot_water_demand_adds_up():
    total = sum(st.dhw_demand_kwh(d, h, 200, 55, 12, 10) for d in range(365) for h in range(24))
    mean_cold = sum(st.mains_temperature(d, 12, 10) for d in range(365)) / 365
    assert total == pytest.approx(365 * 200 * 0.001163 * (55 - mean_cold), rel=1e-6)


def test_adsorption_cop_curve():
    assert st.adsorption_cop(0.55, 59, 60, 80) == 0.0
    assert st.adsorption_cop(0.55, 80, 60, 80) == pytest.approx(0.55)
    assert st.adsorption_cop(0.55, 95, 60, 80) == pytest.approx(0.55)
    assert 0.55 * 0.45 <= st.adsorption_cop(0.55, 61, 60, 80) < 0.55


def _system(area, **kw):
    return st.SolarSystem(area_m2=area, collector=st.COLLECTORS["flat"], store_litres=300,
                          store_ua_w_k=0.16 * math.sqrt(300), dhw_litres_per_day=200, **kw)


def test_energy_balance_closes():
    w = weather()
    for sys_ in (_system(4), _system(12)):
        r = st.simulate(sys_, w, 12, 10)
        stored = r.store_capacity_kwh_k * (r.t_end_c - r.t_start_c)
        assert r.collector_kwh - r.heat_solar_kwh - r.chiller_heat_kwh - r.store_loss_kwh \
            == pytest.approx(stored, abs=1e-6)
        assert r.heat_solar_kwh <= r.heat_demand_kwh + 1e-9


def test_fraction_grows_with_area_and_zero_area_gives_nothing():
    w = weather()
    f = [st.simulate(_system(a), w, 12, 10).heat_fraction for a in (0.001, 2, 4, 8, 16)]
    assert f[0] < 0.01 and f == sorted(f) and f[-1] < 1.0


def test_evacuated_tubes_beat_flat_plate_when_hot_or_cold():
    w = weather()
    flat = st.simulate(_system(4), w, 12, 10)
    tube = st.simulate(replace(_system(4), collector=st.COLLECTORS["tube"]), w, 12, 10)
    assert tube.collector_kwh > flat.collector_kwh


def test_chiller_needs_a_hot_tank():
    d = size_solar_thermal(COOL)
    r = d.run
    assert 0 < r.cooling_solar_kwh < r.cooling_demand_kwh
    mean_cop = r.cooling_solar_kwh / r.chiller_heat_kwh
    assert 0.2 < mean_cop <= COOL.cop_nominal
    weak = size_solar_thermal(replace(COOL, cop_nominal=0.3))
    assert weak.run.cooling_solar_kwh < r.cooling_solar_kwh


def test_design_economics_by_hand():
    inp = SolarThermalInputs()
    d = size_solar_thermal(inp)
    c = st.COLLECTORS["flat"]
    capex = 4 * c.cost_per_m2 + d.store_litres * 1.8 + 1500
    assert d.capex == pytest.approx(capex)
    assert d.savings_per_year == pytest.approx(d.run.heat_solar_kwh * 0.11)
    net = d.savings_per_year - 0.015 * capex
    assert d.npv == pytest.approx(eco.npv(capex, net, 0.05, 20))
    assert d.payback_years == pytest.approx(capex / net)
    assert d.co2_avoided_t == pytest.approx(d.run.heat_solar_kwh * 0.23 / 1000)


def test_target_mode_reaches_the_fraction_or_says_so():
    d = size_solar_thermal(replace(SolarThermalInputs(), mode="target", target_fraction=0.5))
    assert d.target_reached and d.run.solar_fraction >= 0.5 - 1e-9
    assert size_solar_thermal(replace(SolarThermalInputs(), mode="given", area_m2=d.area_m2 * 0.9)
                              ).run.solar_fraction < 0.5 + 0.02
    nope = size_solar_thermal(replace(SolarThermalInputs(), mode="target", target_fraction=0.97))
    assert not nope.target_reached


def test_sweep_and_sensitivity():
    d = size_solar_thermal(SolarThermalInputs())
    fr = [f for _, f, _, _ in d.sweep]
    yields = [y for _, _, y, _ in d.sweep]
    assert fr == sorted(fr) and yields == sorted(yields, reverse=True)
    sw = [c.swing for c in d.sensitivity.curves]
    assert sw == sorted(sw, reverse=True) and d.sensitivity.base == pytest.approx(d.npv)


@pytest.mark.parametrize("bad", [
    dict(dhw_litres_per_day=0), dict(irradiation_kwh_m2=0), dict(area_m2=0),
    dict(collector="nope"), dict(discount_rate=1.2), dict(t_drive_min_c=90),
    dict(mode="target", target_fraction=1.0)])
def test_rejects_bad_inputs(bad):
    with pytest.raises(ValueError):
        size_solar_thermal(replace(SolarThermalInputs(), **bad))


def test_tutor_layer_for_heat_cool_and_both():
    both = replace(SolarThermalInputs(), cooling_kwh_per_year=6000, collector="tube", area_m2=15)
    for inp in (SolarThermalInputs(), COOL, both):
        d = size_solar_thermal(inp)
        findings = check_solar_design(inp, d)
        assert findings and all(f.explanation_key in EXPLANATIONS for f in findings)
        for key in SOLAR_TOPIC_ORDER:
            text = solar_worked_example(key, inp, d)
            assert text and any(ch.isdigit() for ch in text), key
        assert {"solar_balance", "solar_efficiency", "solar_cash", "solar_sens_swing"} \
            <= set(solar_charts(inp, d))
        html = build_solar_report(inp, d, findings)
        assert "Net present value" not in html and "solar fraction" in html
        assert "SOLAR" in build_solar_context(inp, d, findings).upper()
    assert "solar_cooling" in solar_charts(COOL, size_solar_thermal(COOL))
    assert "solar_monthly" not in solar_charts(COOL, size_solar_thermal(COOL))


def test_checker_flags_oversizing_and_unglazed_cooling():
    big = replace(SolarThermalInputs(), area_m2=40)
    codes = {f.code for f in check_solar_design(big, size_solar_thermal(big))}
    assert "stagnation" in codes or "fraction_too_high" in codes
    bad = replace(COOL, collector="unglazed")
    assert "unglazed_cooling" in {f.code for f in check_solar_design(bad, size_solar_thermal(bad))}
