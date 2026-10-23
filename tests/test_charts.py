import math

import pytest

from resize_energy.core import profiles as prof
from resize_energy.core.biomass_design import (
    BiomassInputs,
    default_efficiencies,
    size_biomass_plant,
)
from resize_energy.core.comparison import ComparisonInputs, compare_technologies
from resize_energy.core.hydrogen_design import (
    HydrogenInputs,
    HydrogenProfiles,
    size_hydrogen_plant,
)
from resize_energy.core.pv_design import PVInputs, size_pv_system
from resize_energy.core.wind_design import WindInputs, size_wind_plant
from resize_energy.report.charts import (
    biomass_charts,
    comparison_charts,
    hydrogen_charts,
    nice_ticks,
    pv_charts,
    unit_for,
    wind_charts,
)
from resize_energy.report.html_report import (
    build_biomass_report,
    build_comparison_report,
    build_hydrogen_report,
    build_pv_report,
    build_wind_report,
)
from resize_energy.tutor.checker import check_pv_design
from resize_energy.tutor.checker_biomass import check_biomass_design
from resize_energy.tutor.checker_compare import check_comparison
from resize_energy.tutor.checker_hydrogen import check_hydrogen_design
from resize_energy.tutor.checker_wind import check_wind_design


def _valid(charts):
    assert charts
    for name, spec in charts.items():
        assert spec.title and spec.series, name
        for s in spec.series:
            assert not any(math.isnan(v) for v in s.values), name
            if spec.kind in ("bars", "hbars", "stack"):
                assert len(s.values) == len(spec.categories), name
                if s.colors:
                    assert len(s.colors) == len(s.values), name
            if s.x is not None:
                assert len(s.x) == len(s.values), name


def test_nice_ticks_and_units():
    assert nice_ticks(0, 87) == [0, 20, 40, 60, 80, 100]
    t = nice_ticks(-3.2, 10.5)
    assert t[0] <= -3.2 and t[-1] >= 10.5 and len(t) < 12
    assert nice_ticks(0, 0)[-1] > 0
    assert unit_for([2e7]) == (1e6, "GWh")
    assert unit_for([2e4]) == (1e3, "MWh")
    assert unit_for([120.0]) == (1.0, "kWh")


def test_pv_and_wind_charts_and_reports():
    pi = PVInputs(annual_demand_kwh=4500, annual_irradiation_kwh_m2=1500, performance_ratio=0.8)
    pd = size_pv_system(pi)
    charts = pv_charts(pi, pd)
    _valid(charts)
    html = build_pv_report(pi, pd, check_pv_design(pi, pd), theme="screen")
    assert all(f'src="chart:{n}"' in html for n in charts) and "In short" in html
    wi = WindInputs(annual_demand_kwh=1e7, mean_speed_ref_ms=6.5)
    wd = size_wind_plant(wi)
    charts = wind_charts(wi, wd)
    _valid(charts)
    # the distribution covers (almost) the whole year
    assert sum(charts["wind_distribution"].series[0].values) == pytest.approx(100, abs=2.0)
    html = build_wind_report(wi, wd, check_wind_design(wi, wd))
    assert all(f'src="chart:{n}"' in html for n in charts)


@pytest.mark.parametrize("pathway", ["boiler", "orc", "biogas"])
def test_biomass_charts(pathway):
    th, el = default_efficiencies(pathway)
    bi = BiomassInputs(pathway=pathway, eta_th=th, eta_el=el)
    bd = size_biomass_plant(bi)
    charts = biomass_charts(bi, bd)
    _valid(charts)
    html = build_biomass_report(bi, bd, check_biomass_design(bi, bd))
    assert all(f'src="chart:{n}"' in html for n in charts)
    if pathway == "biogas":
        flow = charts["bio_flow"].series[0].values
        assert flow[0] > flow[1] > flow[2]    # methane > electricity > net electricity


def test_hydrogen_charts():
    hi = HydrogenInputs(use_grid=True)
    hd = size_hydrogen_plant(hi, HydrogenProfiles(prof.synthetic_pv_profile(45, 1300)))
    charts = hydrogen_charts(hi, hd)
    _valid(charts)
    assert len(hd.monthly_res_kwh) == 12
    assert sum(hd.monthly_res_kwh) == pytest.approx(hd.res_used_kwh)
    assert sum(hd.monthly_grid_kwh) == pytest.approx(hd.grid_kwh)
    cost = charts["h2_cost"].series[0].values
    assert sum(cost) == pytest.approx(hd.lcoh)
    html = build_hydrogen_report(hi, hd, check_hydrogen_design(hi, hd))
    assert all(f'src="chart:{n}"' in html for n in charts)


def test_comparison_charts_handle_never():
    wi = WindInputs(annual_demand_kwh=1e7, mean_speed_ref_ms=6.5)
    inp = ComparisonInputs(1500, 0.8, wi, techs=("pv", "wind", "biomass", "hydrogen"))
    r = compare_technologies(inp)
    charts = comparison_charts(inp, r)
    _valid(charts)
    assert math.isinf(max(charts["cmp_payback"].series[0].values))   # a technology never pays
    cash = charts["cmp_cash"].series
    assert len(cash) == 4 and all(s.values[0] < 0 for s in cash)     # starts with the CAPEX
    html = build_comparison_report(inp, r, check_comparison(inp, r))
    assert all(f'src="chart:{n}"' in html for n in charts)
