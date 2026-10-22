import pytest

from resize_energy.core import pv
from resize_energy.tutor.explanations import EXPLANATIONS


def test_required_peak_power_hand_checked():
    # 4800 kWh / (1600 kWh/m2 * 0.75) = 4.0 kWp
    assert pv.required_peak_power_kwp(4800, 1600, performance_ratio=0.75) == pytest.approx(4.0)


def test_required_peak_power_partial_coverage():
    assert pv.required_peak_power_kwp(4800, 1600, 0.75, coverage=0.5) == pytest.approx(2.0)


@pytest.mark.parametrize("kwargs", [
    {"annual_irradiation_kwh_m2": 0},
    {"annual_irradiation_kwh_m2": 1500, "performance_ratio": 0},
    {"annual_irradiation_kwh_m2": 1500, "coverage": 1.5},
])
def test_required_peak_power_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        pv.required_peak_power_kwp(1000, **kwargs)


def test_voltage_temperature_correction():
    # Voc 40 V, beta -0.28 %/C, at -10 C: 40 * (1 + 0.0028*35) = 43.92 V
    assert pv.module_voltage_at_temperature(40, -0.28, -10) == pytest.approx(43.92)


def test_max_modules_per_string():
    # 1000 V / 43.92 V = 22.77 -> 22
    assert pv.max_modules_per_string(1000, 40, -0.28, -10) == 22


def test_min_modules_per_string():
    # Vmp 33 V at 70 C, beta -0.35 %/C: 33 * (1 - 0.0035*45) = 27.8025 V; 200/27.8025 = 7.19 -> 8
    assert pv.min_modules_per_string(200, 33, -0.35, 70) == 8


def test_dc_ac_ratio():
    assert pv.dc_ac_ratio(12, 10) == pytest.approx(1.2)
    with pytest.raises(ValueError):
        pv.dc_ac_ratio(12, 0)


def test_every_pv_function_has_explanation():
    for key in ("required_peak_power", "max_modules_per_string",
                "min_modules_per_string", "dc_ac_ratio"):
        assert f"pv.{key}" in EXPLANATIONS
