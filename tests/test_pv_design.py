import pytest

from resize_energy.core import pv
from resize_energy.core.pv_design import InverterSpec, PVInputs, size_pv_system


def base(**kw):
    defaults = dict(annual_demand_kwh=4500, annual_irradiation_kwh_m2=1500, performance_ratio=0.8)
    defaults.update(kw)
    return PVInputs(**defaults)


def test_max_modules_for_mppt_window():
    # Vmp cold = 31.5 * (1 + 0.0034 * 35) = 35.2485 V; 800 / 35.2485 = 22.7 -> 22
    assert pv.max_modules_for_mppt_window(800, 31.5, -0.34, -10) == 22


def test_default_design_hand_checked():
    d = size_pv_system(base())
    assert d.target_kwp == pytest.approx(3.75)            # 4500 / (1500 * 0.8)
    assert d.modules_target == 10                          # ceil(3750 / 410)
    assert (d.n_series_min, d.n_series_max) == (8, 22)
    assert d.string_capacity == 2                          # floor(26 / 13.9) = 1 per MPPT, x2
    assert d.feasible
    assert (d.n_series, d.n_parallel, d.n_modules) == (10, 1, 10)
    assert d.dc_power_kwp == pytest.approx(4.1)
    assert d.dc_ac_ratio == pytest.approx(4.1 / 4.0)
    assert d.annual_energy_kwh == pytest.approx(4.1 * 1500 * 0.8)
    assert d.achieved_coverage == pytest.approx(4920 / 4500)
    assert d.voc_cold_string_v == pytest.approx(10 * 41.04375)


def test_larger_plant_uses_two_strings_and_prefers_longer_string_on_tie():
    d = size_pv_system(base(annual_demand_kwh=20000))
    assert d.modules_target == 41
    assert (d.n_series, d.n_parallel, d.n_modules) == (21, 2, 42)


def test_array_is_capped_by_inverter_current():
    d = size_pv_system(base(annual_demand_kwh=60000))
    assert d.n_parallel == d.string_capacity == 2
    assert d.n_modules == 44
    assert d.achieved_coverage < 0.5


def test_infeasible_when_mppt_window_too_narrow():
    inverter = InverterSpec(mppt_vmin_v=500, mppt_vmax_v=520)
    d = size_pv_system(base(inverter=inverter))
    assert not d.feasible
    assert d.n_series_min > d.n_series_max


def test_partial_coverage_scales_target():
    d = size_pv_system(base(coverage=0.5))
    assert d.target_kwp == pytest.approx(1.875)
