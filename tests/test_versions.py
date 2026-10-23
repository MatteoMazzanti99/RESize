from dataclasses import replace

import pytest

from resize_energy.core import versions as ver
from resize_energy.core.plant_economics import EconomicInputs
from resize_energy.core.pv_design import PVInputs, size_pv_system
from resize_energy.core.solar_thermal_design import SolarThermalInputs, size_solar_thermal
from resize_energy.core.wind_design import WindInputs, size_wind_plant


def test_diff_states_by_value_not_by_text():
    a = [{"demand": {"num": "4500"}, "kind": {"idx": 0, "text": "Flat"}, "on": {"on": False}}]
    b = [{"demand": {"num": "4500,0"}, "kind": {"idx": 1, "text": "Home"}, "on": {"on": True}}]
    labels = {(0, "kind"): "Load type", (0, "on"): "Use wind"}
    changes = ver.diff_states(a, b, labels)
    assert [c.attr for c in changes] == ["kind", "on"]          # 4500 == 4500,0
    assert changes[0].label == "Load type" and changes[0].old == "Flat"
    assert changes[1].new == "yes"


def test_kpis_for_each_design_class():
    pv = size_pv_system(PVInputs(4500, 1500, economics=EconomicInputs()))
    wind = size_wind_plant(WindInputs(3e6, 6.5, economics=EconomicInputs()))
    sol = size_solar_thermal(SolarThermalInputs(), with_sweep=False, with_sensitivity=False)
    for d in (pv, wind, sol):
        k = ver.read_kpis(d)
        assert len(k) >= 5 and all(x.value == x.value for x in k)
    assert [x.unit for x in ver.read_kpis(pv)][2] == "%"
    assert ver.read_kpis(object()) == []
    # without the cost step the economic results are simply missing
    assert len(ver.read_kpis(size_pv_system(PVInputs(4500, 1500)))) == 3


def test_explain_splits_the_difference_and_leaves_the_interaction():
    base = PVInputs(4500, 1500, economics=EconomicInputs())
    new = replace(base, annual_demand_kwh=9000, economics=EconomicInputs(capex_per_kw=900))

    def vals(inp):
        return [k.value for k in ver.read_kpis(size_pv_system(inp))]

    a, b = vals(base), vals(new)
    only_demand = vals(replace(base, annual_demand_kwh=9000))
    only_cost = vals(replace(base, economics=EconomicInputs(capex_per_kw=900)))
    changes = [ver.Change(0, "demand", "Demand", "4500", "9000"),
               ver.Change(1, "capex", "Cost", "1000", "900")]
    effects, rest = ver.explain(a, b, {0: only_demand, 1: only_cost}, changes)
    for k in range(len(a)):
        total = sum(e.deltas[k] for e in effects) + rest[k]
        assert total == pytest.approx(b[k] - a[k])
    assert effects[0].deltas[0] > 0                    # more demand: more kWp
    assert effects[1].deltas[0] == pytest.approx(0)    # a cheaper plant is not a bigger one
    assert effects[1].deltas[-1] > 0                   # ... but its NPV is higher


def test_missing_single_run_is_reported_as_unknown():
    effects, rest = ver.explain([1.0, 2.0], [2.0, 3.0], {0: None}, [ver.Change(0, "x", "X", "1", "2")])
    assert effects[0].deltas == (None, None) and rest == (1.0, 1.0)


def test_html_has_both_versions_and_the_changes():
    pv = size_pv_system(PVInputs(4500, 1500, economics=EconomicInputs()))
    k = ver.read_kpis(pv)
    ch = [ver.Change(0, "demand", "Annual demand", "4500", "9000")]
    html = ver.comparison_html(k, k, ch, [ver.Effect(ch[0], tuple(0.0 for _ in k))],
                               tuple(0.0 for _ in k))
    assert "Compared with version A" in html and "Annual demand: 4500" in html
    assert "Why did it change?" in html
    assert "same as in version A" in ver.comparison_html(k, k, [])
    assert ver.comparison_html(k, k[:2], ch) == ""
