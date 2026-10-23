import pytest

from resize_energy.core import battery as bat
from resize_energy.core import profiles as prof
from resize_energy.core.battery_design import BatteryInputs, BatteryProfiles, size_battery
from resize_energy.report.charts import battery_charts
from resize_energy.report.html_report import build_battery_report
from resize_energy.tutor.checker_battery import check_battery_design
from resize_energy.tutor.context_battery import build_battery_context
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.explanations_battery import BATTERY_TOPIC_ORDER
from resize_energy.tutor.worked_battery import battery_worked_example

PV = prof.synthetic_pv_profile(45.0, 1300.0)
PROFILES = BatteryProfiles(PV, None, "synthetic")


def case(**kw):
    inp = BatteryInputs(**kw)
    return inp, size_battery(inp, PROFILES)


@pytest.mark.parametrize("kind", list(bat.LOAD_KINDS))
def test_load_profile_sums_to_the_demand(kind):
    load = bat.load_profile(5000.0, kind)
    assert len(load) == bat.HOURS and sum(load) == pytest.approx(5000.0)
    assert min(load) > 0


def test_residential_load_peaks_in_the_evening():
    load = bat.load_profile(5000.0, "residential")
    assert load[20] > load[3] * 2   # 20:00 vs 03:00 of the first day


def test_energy_balance_closes():
    gen = [3.0 if 8 <= t % 24 < 16 else 0.0 for t in range(bat.HOURS)]
    load = bat.load_profile(4000.0, "residential")
    run = bat.simulate_battery(gen, load, 5.0, 2.5)
    # production = direct + charge + export ; load = direct + discharge + import
    assert run.generation_kwh == pytest.approx(run.direct_kwh + run.charge_kwh + run.export_kwh)
    assert run.load_kwh == pytest.approx(run.direct_kwh + run.discharge_kwh + run.import_kwh)
    assert run.discharge_kwh < run.charge_kwh   # the round trip loses energy
    assert max(run.soc) <= 5.0 * 0.9 * 0.9 + 1e-9


def test_no_battery_means_no_storage():
    inp, d = case(mode="given", capacity_kwh=0.0)
    assert d.battery_kwh == 0 and d.self_sufficiency == pytest.approx(d.self_sufficiency_without)
    assert d.npv == 0


def test_bigger_battery_never_lowers_self_sufficiency():
    _, d = case()
    ss = [p.self_sufficiency for p in d.sweep]
    assert ss == sorted(ss)
    assert ss[-1] > ss[0]


def test_perfect_battery_hand_case():
    # 1 kW from 0 to 12, load 1 kW from 12 to 24, a battery of 12 kWh and ideal cells
    gen = [1.0 if (t % 24) < 12 else 0.0 for t in range(bat.HOURS)]
    load = [1.0 if (t % 24) >= 12 else 0.0 for t in range(bat.HOURS)]
    run = bat.simulate_battery(gen, load, 12.0, 1.0, 1.0, 1.0, 1.0, 0.0)
    assert bat.self_sufficiency(run) == pytest.approx(1.0)
    assert bat.self_consumption(run) == pytest.approx(1.0)


def test_modes():
    _, given = case(mode="given", capacity_kwh=8.0)
    assert given.capacity_kwh == 8.0
    _, target = case(mode="target", target_self_sufficiency=0.6)
    assert target.self_sufficiency >= 0.6
    _, best = case(mode="optimal")
    assert best.npv >= max(p.npv for p in best.sweep if p.capacity_kwh > 0) - 1e-6


def test_unreachable_target_explains_itself():
    with pytest.raises(ValueError, match="self-sufficiency"):
        case(mode="target", target_self_sufficiency=0.99)


@pytest.mark.parametrize("kw", [
    {"use_pv": False}, {"annual_demand_kwh": 0}, {"c_rate": 0}, {"retail_price": 0},
    {"mode": "target", "target_self_sufficiency": 1.5}, {"discount_rate": 1.0},
])
def test_bad_inputs_are_rejected(kw):
    with pytest.raises(ValueError):
        case(**kw)


def test_cheap_battery_with_big_price_gap_pays_back():
    _, d = case(capex_per_kwh=150.0, capex_per_kw=20.0, retail_price=0.40, export_price=0.03)
    assert d.npv > 0 and d.payback_years < d.life_years


def test_checks_context_report_and_charts():
    inp, d = case()
    findings = check_battery_design(inp, d)
    assert "npv_negative" in {f.code for f in findings}
    assert "synthetic_profile" in {f.code for f in findings}
    assert "PROJECT: battery" in build_battery_context(inp, d, findings)
    html = build_battery_report(inp, d, findings)
    assert "Design checks" in html and "chart:bat_sweep" in html
    for name, spec in battery_charts(inp, d).items():
        assert spec.series and all(len(s.values) for s in spec.series), name
    for key in BATTERY_TOPIC_ORDER:
        assert key in EXPLANATIONS
        assert battery_worked_example(key, inp, d)


def test_cycle_limited_life():
    _, d = case(cycle_life=600.0)
    assert d.life_limit == "cycles" and d.life_years < 15
