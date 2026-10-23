import math

import pytest

from resize_energy.core import wind
from resize_energy.core.wind_design import TurbineSpec, WindInputs, size_wind_plant


def test_weibull_scale_rayleigh():
    # k = 2: Gamma(1.5) = sqrt(pi)/2 -> A = mean * 2 / sqrt(pi)
    assert wind.weibull_scale_from_mean(7.0, 2.0) == pytest.approx(7.0 * 2 / math.sqrt(math.pi))


def test_weibull_cdf_at_scale_is_63_percent():
    assert wind.weibull_cdf(8.0, 2.5, 8.0) == pytest.approx(1 - math.exp(-1))
    assert wind.weibull_cdf(0.0, 2.0, 8.0) == 0.0


def test_shear_power_law():
    assert wind.shear_power_law(6.0, 50, 100, 0.14) == pytest.approx(6.0 * 2**0.14)
    assert wind.shear_power_law(6.0, 80, 80) == pytest.approx(6.0)


def test_air_density_standard_and_altitude():
    assert wind.air_density(0, 15) == pytest.approx(1.225, abs=0.001)
    assert wind.air_density(1500, 15) == pytest.approx(1.022, abs=0.005)  # thinner air up high


def test_cp_of_a_typical_machine_is_below_betz():
    cp = wind.power_coefficient_at_rated(2000, 90, 12)
    assert 0.2 < cp < wind.BETZ_LIMIT
    # hand check: 0.5 * 1.225 * (pi*45^2) * 12^3 = 6.733e6 W -> 2e6/6.733e6
    assert cp == pytest.approx(2.0e6 / (0.5 * 1.225 * math.pi * 45**2 * 12**3))


def test_generic_curve_shape():
    p = lambda v, rho=1.225: wind.generic_power_kw(v, 2000, 3, 12, 25, rho)  # noqa: E731
    assert p(2.9) == 0 and p(3.0) == 0
    assert p(12) == 2000 and p(20) == 2000
    assert p(25) == 0 and p(30) == 0
    assert p(7.5) == pytest.approx(2000 * (7.5**3 - 27) / (12**3 - 27))
    assert p(8, rho=1.0) < p(8)  # thinner air gives less power below rated


def test_energy_of_a_step_curve_matches_the_analytic_value():
    k, a = 2.0, 8.0
    step = lambda v: 1000.0 if 4.0 <= v < 20.0 else 0.0  # noqa: E731
    expected = 8760 * 1000 * (math.exp(-((4 / a) ** k)) - math.exp(-((20 / a) ** k)))
    # the 0.1 m/s grid puts the edges at bin centres: agreement within 1 %
    assert wind.annual_energy_kwh(step, k, a, step_ms=0.05) == pytest.approx(expected, rel=1e-2)


def test_capacity_factor_and_turbine_count():
    assert wind.capacity_factor(8760 * 500, 2000) == pytest.approx(0.25)
    assert wind.required_turbines(10_000_000, 4_000_000) == 3
    assert wind.required_turbines(8_000_000, 4_000_000) == 2
    assert wind.required_turbines(1, 4_000_000) == 1
    assert wind.required_turbines(10_000_000, 4_000_000, coverage=0.5) == 2


def test_array_area():
    # 4 turbines, D = 100 m, 5D x 7D -> 4 * 35 * 1e4 m2 = 1.4 km2
    assert wind.array_area_km2(4, 100) == pytest.approx(1.4)


def test_validation_errors():
    with pytest.raises(ValueError):
        wind.weibull_scale_from_mean(0, 2)
    with pytest.raises(ValueError):
        wind.required_turbines(100, 0)


def base(**kw):
    d = dict(annual_demand_kwh=10_000_000, mean_speed_ref_ms=6.5)
    d.update(kw)
    return WindInputs(**d)


def test_design_is_consistent():
    d = size_wind_plant(base())
    assert d.mean_speed_hub_ms == pytest.approx(6.5 * (80 / 50) ** 0.14)
    assert 0.15 < d.capacity_factor_net < 0.45
    assert d.net_energy_per_turbine_kwh == pytest.approx(d.gross_energy_per_turbine_kwh * 0.97 * 0.90)
    assert d.annual_energy_kwh >= 10_000_000 * 0.999       # covers the demand
    assert d.annual_energy_kwh - 10_000_000 < d.net_energy_per_turbine_kwh  # not one turbine too many
    assert d.installed_power_kw == d.n_turbines * 2000
    assert d.tip_clearance_m == pytest.approx(35.0)
    assert d.specific_power_w_m2 == pytest.approx(2e6 / (math.pi * 45**2))


def test_faster_wind_means_more_energy_and_fewer_turbines():
    slow = size_wind_plant(base(mean_speed_ref_ms=5.0))
    fast = size_wind_plant(base(mean_speed_ref_ms=8.0))
    assert fast.capacity_factor_net > slow.capacity_factor_net
    assert fast.n_turbines < slow.n_turbines


def test_lower_rated_speed_raises_capacity_factor():
    # same power, rotor sized so that rated power is reached earlier -> more full-load hours
    late = size_wind_plant(base(turbine=TurbineSpec(rated_speed_ms=13.0)))
    early = size_wind_plant(base(turbine=TurbineSpec(rated_speed_ms=10.5)))
    assert early.capacity_factor_net > late.capacity_factor_net
    assert early.cp_rated > late.cp_rated


def test_inconsistent_turbine_speeds_are_rejected():
    with pytest.raises(ValueError):
        size_wind_plant(base(turbine=TurbineSpec(cut_in_ms=13, rated_speed_ms=12)))
    with pytest.raises(ValueError):
        size_wind_plant(base(annual_demand_kwh=0))
