"""Geothermal: brine heat and exergy, plant efficiency, heat and power sizing."""

import math
from dataclasses import replace

import pytest

from resize_energy.core import biomass as bm
from resize_energy.core import geothermal as geo
from resize_energy.core.geothermal_design import GeothermalInputs, plant_type, size_geothermal_plant


def test_thermal_power_by_hand():
    assert geo.thermal_power_kw(50.0, 90.0, 45.0) == pytest.approx(50 * 4.18 * 45)
    with pytest.raises(ValueError):
        geo.thermal_power_kw(1.0, 40.0, 90.0)


def test_exergy_is_zero_at_ambient_and_matches_a_hand_value():
    assert geo.brine_exergy_kj_per_kg(15.0, 15.0) == pytest.approx(0.0)
    t, t0 = 473.15, 288.15
    assert geo.brine_exergy_kj_per_kg(200.0, 15.0) == pytest.approx(
        4.18 * ((t - t0) - t0 * math.log(t / t0)))
    # the 200 degC single-flash plant of the MIT report: about 54 kW per kg/s at 31 % utilization
    assert 0.312 * geo.brine_exergy_kj_per_kg(200.0, 15.0) == pytest.approx(54.0, rel=0.03)
    with pytest.raises(ValueError):
        geo.brine_exergy_kj_per_kg(10.0, 15.0)


def test_binary_efficiency_correlation():
    assert geo.binary_cycle_efficiency(130.0) == pytest.approx((0.09345 * 130 - 2.32657) / 100)
    # 130 degC in, 35 degC out: about 40 kW per kg/s read from the MIT figure 7.3
    power = geo.binary_cycle_efficiency(130.0) * geo.thermal_power_kw(1.0, 130.0, 35.0)
    assert power == pytest.approx(40.0, rel=0.05)
    assert geo.binary_cycle_efficiency(20.0) == 0.0


def test_pumping_power_by_hand():
    # 50 kg/s = 0.05 m3/s; 20 bar = 2 MPa; efficiency 0.65 -> 153.8 kW
    assert geo.pump_power_kw(50.0, 20.0, 0.65) == pytest.approx(0.05 * 2000.0 / 0.65)
    with pytest.raises(ValueError):
        geo.pump_power_kw(1.0, 1.0, 0.0)


def test_well_depth():
    assert geo.well_depth_m(102.0, 12.0, 30.0) == pytest.approx(3000.0)
    with pytest.raises(ValueError):
        geo.well_depth_m(10.0, 12.0, 30.0)


def test_heat_design_follows_the_load_duration_curve():
    inp = GeothermalInputs()
    d = size_geothermal_plant(inp)
    p_pair = 50.0 * 4.18 * (90.0 - 45.0) * 0.95
    assert d.heat_per_pair_kw == pytest.approx(p_pair)
    assert d.power_ratio == pytest.approx(d.wells_pairs * p_pair / inp.peak_heat_kw)
    lf = inp.annual_heat_demand_kwh / (inp.peak_heat_kw * 8760)
    assert d.heat_kwh == pytest.approx(
        bm.covered_fraction(d.power_ratio, lf) * inp.annual_heat_demand_kwh * inp.availability)
    assert d.coverage == pytest.approx(d.heat_kwh / inp.annual_heat_demand_kwh)
    assert d.depth_m == pytest.approx((90.0 - 12.0) / 30.0 * 1000.0)
    assert d.capex == pytest.approx(d.wells_pairs * (2 * d.depth_m * 1500.0 + p_pair * 250.0))
    assert d.spf > 20


def test_heat_wells_are_added_when_the_coverage_needs_them():
    small = size_geothermal_plant(replace(GeothermalInputs(), flow_per_well_kg_s=15.0))
    big = size_geothermal_plant(replace(GeothermalInputs(), flow_per_well_kg_s=100.0))
    assert small.wells_pairs > big.wells_pairs >= 1


def test_power_binary_by_hand():
    inp = GeothermalInputs(pathway="power", reservoir_temp_c=150.0)
    d = size_geothermal_plant(inp)
    assert d.plant == "binary"
    gross = geo.binary_cycle_efficiency(150.0) * 50.0 * 4.18 * (150.0 - 70.0)
    pump = 50.0 / 1000.0 * 2000.0 / 0.65
    assert d.net_kw == pytest.approx(d.wells_pairs * (gross - pump))
    assert d.electricity_kwh == pytest.approx(d.net_kw * inp.operating_hours)
    assert d.capex == pytest.approx(d.net_kw * inp.capex_per_kw_el)
    assert d.co2_avoided_t_per_year == pytest.approx(
        d.electricity_kwh * (inp.grid_ef - inp.lifecycle_g_per_kwh / 1000.0) / 1000.0)


def test_power_flash_uses_the_exergy():
    inp = GeothermalInputs(pathway="power", reservoir_temp_c=200.0)
    assert plant_type(inp) == "flash"
    d = size_geothermal_plant(inp)
    gross = 0.31 * 50.0 * geo.brine_exergy_kj_per_kg(200.0, 12.0)
    pump = 50.0 / 1000.0 * 2000.0 / 0.65
    assert d.net_kw == pytest.approx(d.wells_pairs * (gross * 0.95 - pump))


def test_plant_choice_and_hotter_means_more_power():
    cold = size_geothermal_plant(GeothermalInputs(pathway="power", reservoir_temp_c=120.0,
                                                  annual_electricity_demand_kwh=1e6))
    hot = size_geothermal_plant(GeothermalInputs(pathway="power", reservoir_temp_c=160.0,
                                                 annual_electricity_demand_kwh=1e6))
    assert hot.net_kw > cold.net_kw
    assert plant_type(GeothermalInputs(plant="binary", reservoir_temp_c=220.0)) == "binary"


@pytest.mark.parametrize("change", [
    {"pathway": "x"}, {"plant": "x"}, {"flow_per_well_kg_s": 0}, {"reservoir_temp_c": 5.0},
    {"coverage": 0.0}, {"availability": 0.0}, {"return_temp_c": 95.0},
    {"annual_heat_demand_kwh": 0}, {"peak_heat_kw": 100.0},
])
def test_bad_heat_inputs_are_refused(change):
    with pytest.raises(ValueError):
        size_geothermal_plant(replace(GeothermalInputs(), **change))


@pytest.mark.parametrize("change", [
    {"annual_electricity_demand_kwh": 0}, {"operating_hours": 9000.0},
    {"reinjection_temp_c": 160.0}, {"pump_pressure_bar": 500.0},
])
def test_bad_power_inputs_are_refused(change):
    with pytest.raises(ValueError):
        size_geothermal_plant(replace(GeothermalInputs(pathway="power", reservoir_temp_c=150.0),
                                      **change))
