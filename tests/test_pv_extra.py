import pytest

from resize_energy.core import pv_extra as x
from resize_energy.core.pv_design import PVInputs, size_pv_system
from resize_energy.report.charts import pv_charts
from resize_energy.report.html_report import build_pv_report
from resize_energy.tutor.checker import check_pv_design
from resize_energy.tutor.explanations import EXPLANATIONS, TOPIC_ORDER
from resize_energy.tutor.worked import worked_example


def test_sun_at_noon_matches_geometry():
    el, az = x.sun_position(172, 12.5, 45.0)          # about the June solstice
    assert el == pytest.approx(90 - 45 + 23.45, abs=1.5)
    assert abs(az) < 20
    el_w, _ = x.sun_position(355, 12.5, 45.0)         # December
    assert el_w == pytest.approx(90 - 45 - 23.45, abs=1.5)


def test_shading_is_zero_without_obstacle_and_grows_with_height():
    assert x.shading_loss(45, 0, -60, 60) == 0.0
    low = x.shading_loss(45, 10, -60, 60)
    high = x.shading_loss(45, 40, -60, 60)
    assert 0 < low < high < 0.65          # beam share caps the loss
    assert x.shading_loss(45, 30, 100, 170) < x.shading_loss(45, 30, -60, 60)


def test_shading_validation():
    for args in ((45, 95, -60, 60), (45, 10, 60, -60), (120, 10, -60, 60)):
        with pytest.raises(ValueError):
            x.shading_loss(*args)


def test_monthly_energy_sums_and_has_a_summer_peak():
    m = x.monthly_energy_kwh(45, 5000)
    assert sum(m) == pytest.approx(5000) and len(m) == 12
    assert max(m) / min(m) > 2.5 and m.index(max(m)) in (4, 5, 6, 7)
    south = x.monthly_energy_kwh(-35, 5000)
    assert south.index(max(south)) in (10, 11, 0, 1)


def test_shading_raises_the_required_array():
    base = PVInputs(annual_demand_kwh=4500, annual_irradiation_kwh_m2=1500)
    shaded = PVInputs(annual_demand_kwh=4500, annual_irradiation_kwh_m2=1500, shading_loss=0.15)
    d0, d1 = size_pv_system(base), size_pv_system(shaded)
    assert d1.target_kwp == pytest.approx(d0.target_kwp / 0.85)
    assert d1.performance_ratio_effective == pytest.approx(0.8 * 0.85)
    with pytest.raises(ValueError):
        size_pv_system(PVInputs(annual_demand_kwh=4500, annual_irradiation_kwh_m2=1500,
                                shading_loss=0.95))


def test_report_texts_and_charts_include_the_new_topics():
    inp = PVInputs(annual_demand_kwh=4500, annual_irradiation_kwh_m2=1500, shading_loss=0.12)
    d = size_pv_system(inp)
    charts = pv_charts(inp, d)
    assert {"pv_energy", "pv_voltage", "pv_monthly", "pv_battery"} <= set(charts)
    assert "shading_high" in {f.code for f in check_pv_design(inp, d)}
    for key in ("pv.shading", "pv.monthly", "pv.battery"):
        assert key in TOPIC_ORDER and key in EXPLANATIONS
        assert worked_example(key, inp, d)
    html = build_pv_report(inp, d, check_pv_design(inp, d))
    assert "Shading loss" in html and "chart:pv_battery" in html
