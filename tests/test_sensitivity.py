from dataclasses import replace

import pytest

from resize_energy.core import profiles as prof
from resize_energy.core.battery_design import (
    BatteryInputs,
    BatteryProfiles,
    battery_sensitivity,
    size_battery,
)
from resize_energy.core.comparison import (
    ComparisonInputs,
    compare_technologies,
    comparison_sensitivity,
    ranking_changes,
)
from resize_energy.core.hydrogen_design import (
    HydrogenInputs,
    HydrogenProfiles,
    hydrogen_sensitivity,
    size_hydrogen_plant,
)
from resize_energy.core.sensitivity import Parameter, one_at_a_time
from resize_energy.core.wind_design import WindInputs
from resize_energy.report.charts import battery_charts, comparison_charts, hydrogen_charts
from resize_energy.tutor.checker_battery import check_battery_design
from resize_energy.tutor.checker_compare import check_comparison
from resize_energy.tutor.checker_hydrogen import check_hydrogen_design
from resize_energy.tutor.worked_battery import battery_worked_example
from resize_energy.tutor.worked_compare import compare_worked_example
from resize_energy.tutor.worked_hydrogen import hydrogen_worked_example

PV = prof.synthetic_pv_profile(45.0, 1300.0)


def test_engine_on_a_known_function():
    # result = 100 * a + 10 * b: a matters ten times more
    def f(d):
        return 100 * d.get("a", 1.0) + 10 * d.get("b", 1.0)

    s = one_at_a_time(f, [Parameter("b", "B"), Parameter("a", "A")], "x", "u")
    assert s.base == pytest.approx(110)
    assert [c.label for c in s.curves] == ["A", "B"]
    assert s.curves[0].values == pytest.approx((90, 100, 110, 120, 130))
    assert s.curves[0].swing == pytest.approx(40)
    assert s.relative_swing(s.curves[0]) == pytest.approx(20 / 110)


@pytest.mark.parametrize("steps", [(0.1, 0.2), (-1.0, 0.0)])
def test_engine_rejects_bad_steps(steps):
    with pytest.raises(ValueError):
        one_at_a_time(lambda d: 1.0, [Parameter("a", "A")], "x", "u", steps)
    with pytest.raises(ValueError):
        one_at_a_time(lambda d: 1.0, [], "x", "u")


def test_hydrogen_sensitivity_directions():
    inp = HydrogenInputs()
    prof_h = HydrogenProfiles(PV, None, "synthetic")
    s = hydrogen_sensitivity(inp, prof_h)
    assert s.base == pytest.approx(size_hydrogen_plant(inp, prof_h).lcoh)
    by = {c.label: c for c in s.curves}
    assert by["Electrolyser cost per kW"].values[0] < s.base < by["Electrolyser cost per kW"].values[-1]
    assert by["Stack life"].values[0] > by["Stack life"].values[-1]   # longer life, cheaper
    d = replace(size_hydrogen_plant(inp, prof_h), sensitivity=s)
    assert {"h2_sens_swing", "h2_sens_spider"} <= set(hydrogen_charts(inp, d))
    assert hydrogen_worked_example("hydrogen.sensitivity", inp, d)
    assert "sens_top" in {f.code for f in check_hydrogen_design(inp, d)}


def test_battery_sensitivity_can_flip_the_sign():
    inp = BatteryInputs(capex_per_kwh=300.0)
    p = BatteryProfiles(PV, None, "synthetic")
    d = size_battery(inp, p)
    s = battery_sensitivity(inp, p, d.capacity_kwh)
    assert s.base == pytest.approx(d.npv, rel=1e-6)
    by = {c.label: c for c in s.curves}
    assert by["Battery cost per kWh"].values[0] > by["Battery cost per kWh"].values[-1]
    assert by["Price you pay for electricity"].values[-1] > s.base
    d2 = replace(d, sensitivity=s)
    assert {"bat_sens_swing", "bat_sens_spider"} <= set(battery_charts(inp, d2))
    assert battery_worked_example("battery.sensitivity", inp, d2)
    check_battery_design(inp, d2)


def test_comparison_sensitivity_and_ranking():
    inp = ComparisonInputs(1500, 0.8, WindInputs(annual_demand_kwh=1e7, mean_speed_ref_ms=6.5),
                           techs=("pv", "wind", "biomass"))
    sens = comparison_sensitivity(inp)
    assert set(sens) == {"capex", "rate"}
    for data in sens.values():
        for v in data.values():
            assert len(v) == 5 and v[0] < v[-1]       # dearer money or capex, dearer energy
    base = compare_technologies(inp)
    assert sens["capex"]["pv"][2] == pytest.approx(base.pv.lcoe_eur_per_kwh)
    r = replace(base, sensitivity=sens)
    assert {"cmp_sens_capex", "cmp_sens_rate"} <= set(comparison_charts(inp, r))
    assert compare_worked_example("econ.sensitivity", inp, r)
    codes = {f.code for f in check_comparison(inp, r)}
    assert codes & {"ranking_stable", "ranking_unstable"}


def test_ranking_changes_detects_a_crossing():
    data = {"capex": {"a": (1.0, 1.1, 1.2, 1.3, 1.4), "b": (1.3, 1.3, 1.3, 1.3, 1.3)}}
    assert ranking_changes(data) == ["capital costs"]
    flat = {"rate": {"a": (1, 1, 1, 1, 1), "b": (2, 2, 2, 2, 2)}}
    assert ranking_changes(flat) == []
