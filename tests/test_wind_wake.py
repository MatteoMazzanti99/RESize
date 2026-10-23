import math

import pytest

from resize_energy.core import wind
from resize_energy.core import wind_wake as ww
from resize_energy.core.wind_design import TurbineSpec, WindInputs, size_wind_plant
from resize_energy.report.charts import wind_charts
from resize_energy.report.html_report import build_wind_report
from resize_energy.tutor.checker_wind import check_wind_design
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.explanations_wind import WIND_TOPIC_ORDER
from resize_energy.tutor.worked_wind import wind_worked_example

T = TurbineSpec()


def power(v):
    return wind.generic_power_kw(v, T.rated_power_kw, T.cut_in_ms, T.rated_speed_ms,
                                 T.cut_out_ms, 1.225)


def eff(n, per_row, cross=5, down=7, conc=1.0, prevailing=270.0, stagger=True):
    pos = ww.grid_layout(n, per_row, cross, down, 90.0, stagger, prevailing)
    return ww.wake_efficiency(pos, power, 90.0, 7.0, 2.0, 3.0, 12.0, 25.0, 0.075,
                              ww.rose_weights(prevailing, conc))


def test_rose_weights():
    uniform = ww.rose_weights(270, 0)
    assert all(w == pytest.approx(1 / 12) for w in uniform)
    peaked = ww.rose_weights(270, 2)
    assert sum(peaked) == pytest.approx(1.0) and peaked.index(max(peaked)) == 9   # 270 deg


def test_overlap_fraction_limits():
    assert ww._overlap_fraction(100, 45, 0) == 1.0
    assert ww._overlap_fraction(100, 45, 200) == 0.0
    assert 0 < ww._overlap_fraction(100, 45, 90) < 1


def test_single_turbine_has_no_wake():
    assert eff(1, 1).array_efficiency == pytest.approx(1.0)


def test_wider_spacing_means_less_loss():
    assert eff(12, 4, 5, 7).array_efficiency < eff(12, 4, 8, 12).array_efficiency < 1.0


def test_more_turbines_more_loss_and_no_loss_in_front_row():
    small, big = eff(6, 3), eff(24, 6)
    assert big.array_efficiency < small.array_efficiency
    assert min(big.turbine_efficiency) < max(big.turbine_efficiency) <= 1.0 + 1e-9


def test_layout_orientation_follows_the_prevailing_wind():
    # rows across a wind from the west: with the wind from the west the loss is the same
    # as with the same layout turned to a wind from the north
    west = eff(12, 4, prevailing=270, conc=2)
    north = eff(12, 4, prevailing=0, conc=2)
    assert west.array_efficiency == pytest.approx(north.array_efficiency, abs=0.005)


def test_wrong_orientation_costs_more():
    pos = ww.grid_layout(12, 4, 5, 7, 90.0, True, 270.0)
    aligned = ww.wake_efficiency(pos, power, 90.0, 7.0, 2.0, 3, 12, 25, 0.075,
                                 ww.rose_weights(270, 3))
    turned = ww.wake_efficiency(pos, power, 90.0, 7.0, 2.0, 3, 12, 25, 0.075,
                                ww.rose_weights(0, 3))
    assert math.isfinite(turned.array_efficiency)
    assert aligned.array_efficiency != pytest.approx(turned.array_efficiency, abs=1e-4)


def test_bad_decay_rejected():
    with pytest.raises(ValueError):
        ww.wake_efficiency([(0, 0)], power, 90.0, 7.0, 2.0, 3, 12, 25, 0.5, (1.0,))


def test_design_with_wake_needs_more_turbines_and_reports_it():
    base = size_wind_plant(WindInputs(annual_demand_kwh=60e6, mean_speed_ref_ms=6.5))
    wk = size_wind_plant(WindInputs(annual_demand_kwh=60e6, mean_speed_ref_ms=6.5,
                                    wake_model=True))
    assert wk.n_turbines >= base.n_turbines
    assert 0.02 < wk.wake_loss < 0.2
    assert wk.annual_energy_kwh >= 60e6 * 0.999 or wk.achieved_coverage >= 1.0 - 1e-6
    assert wk.rows * wk.turbines_per_row >= wk.n_turbines
    assert len(wk.wake.turbine_efficiency) == wk.n_turbines


def test_texts_charts_and_report():
    inp = WindInputs(annual_demand_kwh=60e6, mean_speed_ref_ms=6.5, wake_model=True,
                     other_losses=0.10)
    d = size_wind_plant(inp)
    assert {"wind_wake_rose", "wind_wake_turbines"} <= set(wind_charts(inp, d))
    for key in ("wind.wake", "wind.rose"):
        assert key in WIND_TOPIC_ORDER and key in EXPLANATIONS
        assert wind_worked_example(key, inp, d)
    findings = check_wind_design(inp, d)
    assert "double_count" in {f.code for f in findings}
    assert "Jensen" in build_wind_report(inp, d, findings)
