"""Hydropower: flow-duration curve, penstock, turbine choice and the yearly energy."""

import math
from dataclasses import replace

import pytest

from resize_energy.core import hydro as hy
from resize_energy.core.hydro_design import HydroInputs, exceedance_sweep, size_hydro_plant


def test_lognormal_curve_reproduces_the_mean_and_q95():
    mu, sigma = hy.lognormal_fdc(2.0, 0.4)
    assert math.exp(mu + sigma ** 2 / 2) == pytest.approx(2.0)
    assert hy.flow_exceeded(0.95, mu, sigma) == pytest.approx(0.4, rel=1e-3)
    assert hy.flow_exceeded(0.5, mu, sigma) == pytest.approx(math.exp(mu))


def test_flow_exceeded_decreases_with_exceedance():
    mu, sigma = hy.lognormal_fdc(3.0, 0.5)
    flows = [hy.flow_exceeded(p, mu, sigma) for p in (0.05, 0.2, 0.5, 0.8, 0.95)]
    assert flows == sorted(flows, reverse=True)


@pytest.mark.parametrize("mean, q95", [(0, 1), (1, 0), (1, 1), (1, 2)])
def test_bad_flow_data_is_refused(mean, q95):
    with pytest.raises(ValueError):
        hy.lognormal_fdc(mean, q95)


def test_penstock_diameter_and_friction_by_hand():
    d = hy.penstock_diameter(2.0, 3.0)
    assert d == pytest.approx(math.sqrt(4 * 2.0 / (math.pi * 3.0)))
    # laminar flow: f = 64 / Re
    assert hy.friction_factor(1000.0, 0.001) == pytest.approx(0.064)
    # Moody chart: Re = 1e6 and roughness 1e-4 give about 0.0135
    assert 0.0125 < hy.friction_factor(1e6, 1e-4) < 0.0145
    v = 2.0 / (math.pi * d ** 2 / 4)
    f = hy.friction_factor(v * d / hy.NU_WATER, 0.0001 / d)
    expected = (f * 300.0 / d + 1.0) * v ** 2 / (2 * hy.G)
    assert hy.head_loss(2.0, d, 300.0, 0.0001, 1.0) == pytest.approx(expected)
    assert hy.head_loss(0.0, d, 300.0, 0.0001, 1.0) == 0.0


def test_hydraulic_power():
    assert hy.hydraulic_power_kw(1.0, 100.0) == pytest.approx(981.0)
    assert hy.hydraulic_power_kw(1.0, 100.0, 0.9) == pytest.approx(882.9)


@pytest.mark.parametrize("head, flow, expected", [
    (10.0, 5.0, "kaplan"), (10.0, 0.3, "crossflow"), (80.0, 2.0, "francis"),
    (80.0, 0.2, "pelton"), (400.0, 0.5, "pelton"), (200.0, 5.0, "francis"),
])
def test_turbine_choice(head, flow, expected):
    assert hy.choose_turbine(head, flow) == expected


def test_turbine_ranges_come_from_the_esha_table():
    assert (hy.TURBINES["kaplan"].head_min, hy.TURBINES["kaplan"].head_max) == (2.0, 40.0)
    assert (hy.TURBINES["francis"].head_min, hy.TURBINES["francis"].head_max) == (25.0, 350.0)
    assert (hy.TURBINES["pelton"].head_min, hy.TURBINES["pelton"].head_max) == (50.0, 1300.0)


def test_generator_efficiency_follows_the_table():
    assert hy.generator_efficiency(100.0) == pytest.approx(0.95)
    assert hy.generator_efficiency(5.0) == pytest.approx(0.91)
    assert hy.generator_efficiency(5000.0) == pytest.approx(0.97)
    assert 0.94 < hy.generator_efficiency(70.0) < 0.95


def test_design_numbers_are_consistent():
    inp = HydroInputs()
    d = size_hydro_plant(inp)
    # design flow: river flow at the exceedance minus the environmental flow
    assert d.design_flow_m3s == pytest.approx(d.river_flow_at_design_m3s - inp.eco_flow_m3s)
    assert d.net_head_m == pytest.approx(inp.gross_head_m - d.head_loss_m)
    assert d.rated_kw == pytest.approx(
        hy.hydraulic_power_kw(d.design_flow_m3s, d.net_head_m, d.turbine_eff * d.generator_eff))
    assert d.energy_kwh < d.rated_kw * hy.HOURS_PER_YEAR
    assert d.capacity_factor == pytest.approx(d.energy_kwh / (d.rated_kw * 8760))
    assert d.velocity_ms == pytest.approx(inp.penstock_velocity_ms)
    assert 0.0 < d.water_used_fraction < 1.0
    assert d.turbine_key in hy.TURBINES


def test_energy_is_the_integral_of_the_curve():
    inp = HydroInputs(operating_losses=0.0, penstock_length_m=0.0, local_loss_k=0.0)
    d = size_hydro_plant(inp)
    dt = 8760 / len(d.curve)
    energy = sum(hy.hydraulic_power_kw(q_t, inp.gross_head_m, d.turbine_eff * d.generator_eff) * dt
                 for _, _, q_t in d.curve)
    assert d.energy_kwh == pytest.approx(energy, rel=1e-9)


def test_more_environmental_flow_means_less_energy():
    base = size_hydro_plant(HydroInputs(eco_flow_m3s=0.1))
    more = size_hydro_plant(HydroInputs(eco_flow_m3s=0.5))
    assert more.energy_kwh < base.energy_kwh


def test_a_thin_penstock_costs_head():
    wide = size_hydro_plant(HydroInputs(penstock_diameter_m=1.5))
    thin = size_hydro_plant(HydroInputs(penstock_diameter_m=0.7))
    assert thin.head_loss_m > wide.head_loss_m
    assert thin.energy_kwh < wide.energy_kwh


def test_turbine_stops_below_its_minimum_flow():
    d = size_hydro_plant(HydroInputs())
    assert all(q == 0.0 or q >= d.min_flow_m3s - 1e-12 for _, _, q in d.curve)
    assert all(q <= d.design_flow_m3s + 1e-12 for _, _, q in d.curve)


def test_economics():
    inp = HydroInputs(annual_demand_kwh=1_000_000.0)
    d = size_hydro_plant(inp)
    assert d.capex == pytest.approx(d.rated_kw * inp.capex_per_kw)
    assert d.om_per_year == pytest.approx(d.capex * inp.om_fraction)
    assert d.electricity_coverage == pytest.approx(d.energy_kwh / 1_000_000.0)
    # 1 GWh at the retail price, the rest exported
    expected = 1_000_000.0 * inp.retail_price + (d.energy_kwh - 1_000_000.0) * inp.export_price
    assert d.savings_per_year == pytest.approx(expected)
    # carbon: grid factor minus the life-cycle emissions of the plant
    assert d.co2_avoided_t_per_year == pytest.approx(
        d.energy_kwh * (inp.grid_ef - inp.lifecycle_g_per_kwh / 1000.0) / 1000.0)


def test_the_sweep_has_the_design_point_and_skips_impossible_ones():
    inp = HydroInputs()
    sweep = exceedance_sweep(inp)
    assert len(sweep) >= 10
    assert [s[1] for s in sweep] == sorted((s[1] for s in sweep), reverse=True)  # power falls
    big_eco = exceedance_sweep(replace(inp, eco_flow_m3s=1.0))
    assert len(big_eco) < len(sweep)


@pytest.mark.parametrize("change", [
    {"gross_head_m": 0}, {"eco_flow_m3s": -1}, {"design_exceedance": 0}, {"design_exceedance": 1},
    {"turbine": "nope"}, {"operating_losses": 1.0}, {"eco_flow_m3s": 5.0},
    {"design_exceedance": 0.99, "eco_flow_m3s": 1.0},
])
def test_bad_inputs_are_refused(change):
    with pytest.raises(ValueError):
        size_hydro_plant(replace(HydroInputs(), **change))
