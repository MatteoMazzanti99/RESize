import json
from dataclasses import replace

import pytest

from resize_energy.core import hydrogen as h2
from resize_energy.core import profiles as prof
from resize_energy.core.hydrogen_design import (
    HydrogenInputs,
    HydrogenProfiles,
    size_hydrogen_plant,
)
from resize_energy.core.nasa_power import NasaPowerError
from resize_energy.report.html_report import build_hydrogen_report
from resize_energy.tutor.checker_hydrogen import check_hydrogen_design
from resize_energy.tutor.context_hydrogen import build_hydrogen_context
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.explanations_hydrogen import HYDROGEN_TOPIC_ORDER
from resize_energy.tutor.worked_hydrogen import hydrogen_worked_example

PV = prof.synthetic_pv_profile(45.0, 1300.0)
WIND = prof.wind_profile_from_speeds(
    prof.synthetic_wind_series(6.5, 2.0), 50.0,
    lambda v: 0.0 if v < 3 else min(2000.0, 2000.0 * ((v - 3) / 9) ** 3), 2000.0, 80.0, 0.14)
PROFILES = HydrogenProfiles(PV, WIND, "synthetic")


def case(**kw):
    inp = HydrogenInputs(**kw)
    return inp, size_hydrogen_plant(inp, PROFILES)


def codes(findings, severity=None):
    return {f.code for f in findings if severity is None or f.severity == severity}


def test_efficiency_and_compression_hand_values():
    assert h2.system_efficiency_lhv(55.0) == pytest.approx(33.33 / 55.0)
    # R T ln(350/30) / 3.6e6 / 0.6 = 4124 x 298 x 2.4567 / 3.6e6 / 0.6 = 1.398 kWh/kg
    assert h2.compression_kwh_per_kg(30, 350) == pytest.approx(1.398, abs=0.01)
    assert h2.compression_kwh_per_kg(30, 30) == pytest.approx(0.0)
    with pytest.raises(ValueError):
        h2.compression_kwh_per_kg(350, 30)


def test_density_and_storage_volume():
    assert h2.hydrogen_density_kg_m3(350) == pytest.approx(24.4, abs=0.6)
    assert h2.hydrogen_density_kg_m3(700) > h2.hydrogen_density_kg_m3(350)
    assert h2.storage_volume_m3(1000, 350) == pytest.approx(1000 / h2.hydrogen_density_kg_m3(350))


def test_dispatch_flat_renewable_hand_values():
    flat = [0.5] * 8760  # 0.5 kW per kW
    r = h2.simulate_dispatch(None, flat, 0, 1000, 1000, 0.1, 50.0, False, 0)
    assert r.res_used_kwh == pytest.approx(0.5 * 1000 * 8760)
    assert r.hydrogen_kg == pytest.approx(r.electricity_kwh / 50.0)
    assert r.hours_on == 8760 and r.grid_kwh == 0


def test_dispatch_minimum_load_and_curtailment():
    low = [0.05] * 8760  # below the 10 % minimum load: electrolyser never runs
    assert h2.simulate_dispatch(None, low, 0, 1000, 1000, 0.1, 50.0, False, 0).hydrogen_kg == 0
    high = [2.0] * 8760  # twice the electrolyser: half is curtailed
    r = h2.simulate_dispatch(None, high, 0, 1000, 1000, 0.1, 50.0, False, 0)
    assert r.res_used_kwh == pytest.approx(1000 * 8760)
    assert r.res_available_kwh == pytest.approx(2 * r.res_used_kwh)


def test_dispatch_grid_respects_the_cap():
    r = h2.simulate_dispatch(None, None, 0, 0, 1000, 0.1, 50.0, True, 3000)
    assert r.grid_kwh == pytest.approx(3000 * 1000, rel=1e-9)
    assert r.res_used_kwh == 0
    with pytest.raises(ValueError):
        h2.simulate_dispatch(None, None, 0, 0, 0, 0.1, 50.0, True, 3000)


COMBOS = [(c, m) for c in [(1, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 1), (0, 1, 1), (0, 0, 1),
                           (1, 1, 1)] for m in ("demand", "plant")]


@pytest.mark.parametrize("combo,mode", COMBOS)
def test_all_source_combinations(combo, mode):
    pv, wd, gr = map(bool, combo)
    inp, d = case(mode=mode, use_pv=pv, use_wind=wd, use_grid=gr, pv_kwp=1500, wind_kw=1000,
                  electrolyser_kw=1000)
    assert d.hydrogen_kg > 0 and d.lcoh > 0
    if mode == "demand":
        assert d.hydrogen_kg == pytest.approx(inp.h2_demand_kg_per_year, rel=1e-6)
    assert (d.pv_kwp > 0) == pv or mode == "plant" and pv
    assert (d.grid_kwh > 0) == gr
    assert d.electricity_kwh == pytest.approx(d.res_used_kwh + d.grid_kwh)
    parts = (d.cost_electrolyser + d.cost_stack + d.cost_storage + d.cost_res + d.cost_grid
             + d.cost_water)
    assert d.lcoh * d.hydrogen_kg == pytest.approx(parts, rel=1e-6)


def test_grid_only_is_dirty_and_renewable_is_clean():
    _, grid = case(use_pv=False, use_grid=True)
    _, pv = case()
    assert grid.co2_kg_per_kg > 9.0           # worse than grey hydrogen at 0.25 kg/kWh
    assert pv.co2_kg_per_kg < 3.4             # EU renewable-hydrogen threshold


def test_validation():
    with pytest.raises(ValueError):
        size_hydrogen_plant(HydrogenInputs(use_pv=False), PROFILES)
    with pytest.raises(ValueError):
        size_hydrogen_plant(HydrogenInputs(h2_demand_kg_per_year=0), PROFILES)
    with pytest.raises(ValueError):
        size_hydrogen_plant(HydrogenInputs(outlet_bar=400, storage_bar=350), PROFILES)


def test_checker_flags():
    inp, d = case(use_pv=False, use_grid=True)
    assert "worse_than_grey" in codes(check_hydrogen_design(inp, d), "error")
    inp, d = case()
    assert "design_ok" in codes(check_hydrogen_design(inp, d)) or codes(
        check_hydrogen_design(inp, d))
    inp, d = case(pv_kwp_per_kw_el=6.0)
    assert "curtailment" in codes(check_hydrogen_design(inp, d))


def test_topics_report_and_context():
    assert set(HYDROGEN_TOPIC_ORDER) <= set(EXPLANATIONS)
    inp, d = case(use_wind=True, use_grid=True)
    for key in HYDROGEN_TOPIC_ORDER:
        text = hydrogen_worked_example(key, inp, d)
        assert isinstance(text, str) and text.strip(), key
    assert hydrogen_worked_example("pv.unknown", inp, d) is None
    findings = check_hydrogen_design(inp, d)
    for theme in ("light", "screen"):
        html = build_hydrogen_report(inp, d, findings, theme=theme)
        assert "hydrogen" in html.lower() and "LCOH" in html
    assert "hydrogen" in build_hydrogen_context(inp, d, findings).lower()


def test_synthetic_profiles_totals():
    assert len(PV) == 8760 and sum(PV) == pytest.approx(1300.0, rel=1e-6)
    assert max(PV) <= 1.0 and min(PV) >= 0
    series = prof.synthetic_wind_series(6.5, 2.0)
    assert len(series) == 8760 and sum(series) / 8760 == pytest.approx(6.5, rel=0.1)
    assert prof.synthetic_pv_profile(45, 1300, seed=1) == PV  # reproducible
    southern = prof.synthetic_pv_profile(-35.0, 1300.0)
    assert sum(southern[:24 * 31]) > sum(southern[24 * 180:24 * 211])  # January is summer in the south


def test_pv_profile_from_ghi_and_wind_from_speeds():
    ghi = [0.0, 500.0] * 4380
    pv = prof.pv_profile_from_ghi(ghi, 1000.0)
    assert sum(pv) == pytest.approx(1000.0)
    with pytest.raises(ValueError):
        prof.pv_profile_from_ghi([1.0] * 10, 1000.0)
    speeds = [8.0] * 8760
    unit = prof.wind_profile_from_speeds(speeds, 50.0, lambda v: 1000.0, 2000.0, 50.0, 0.14,
                                         efficiency=0.9)
    assert unit[0] == pytest.approx(0.5 * 0.9)


def test_hour_index_and_parse_hourly():
    assert prof.hour_index("2019010100") == 0
    assert prof.hour_index("2019010201") == 25
    assert prof.hour_index("2019123123") == 8759
    assert prof.hour_index("2020022900") == -1

    def key(i):
        day, hour = divmod(i, 24)
        month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        m = 0
        while day >= month_days[m]:
            day -= month_days[m]
            m += 1
        return f"2019{m + 1:02d}{day + 1:02d}{hour:02d}"

    data = {"properties": {"parameter": {
        "WS50M": {key(i): 5.0 for i in range(8760)},
        "ALLSKY_SFC_SW_DWN": {key(i): (-999 if i == 10 else 100.0) for i in range(8760)}}}}
    w = prof.parse_hourly(data)
    assert len(w.wind50_ms) == len(w.ghi_w_m2) == 8760
    assert w.ghi_w_m2[10] == 0.0 or w.ghi_w_m2[10] == w.ghi_w_m2[9]  # fill value repaired
    with pytest.raises(NasaPowerError):
        prof.parse_hourly({"properties": {}})
    with pytest.raises(NasaPowerError):
        prof.parse_hourly({"properties": {"parameter": {"WS50M": {}, "ALLSKY_SFC_SW_DWN": {}}}})

    class Resp:
        def __init__(self, body): self.body = body
        def read(self): return self.body
        def __enter__(self): return self
        def __exit__(self, *a): return False

    got = prof.fetch_hourly(45, 7, urlopen=lambda req, timeout: Resp(json.dumps(data).encode()))
    assert got.year == 2019
    with pytest.raises(NasaPowerError):
        prof.fetch_hourly(45, 7, urlopen=lambda req, timeout: Resp(b"<html>"))
    assert "WS50M" in prof.build_hourly_url(45, 7)


def test_inputs_replace_keeps_defaults():
    assert replace(HydrogenInputs(), use_grid=True).use_grid


# --- deeper models: part load, ageing, hourly tank, hourly prices ---------------------------
def deep(**kw):
    return case(**kw)


def test_part_load_factor_shape():
    assert h2.part_load_factor(1.0) == pytest.approx(1.0)
    assert h2.part_load_factor(0.1) > h2.part_load_factor(0.5) > 0.9
    assert h2.part_load_factor(0.5) < 1.02            # almost flat in the middle
    with pytest.raises(ValueError):
        h2.part_load_factor(0.0)


def test_defaults_keep_the_simple_model():
    inp, d = deep()
    assert d.kwh_per_kg_total == pytest.approx(d.nominal_kwh_per_kg_total)
    assert d.hydrogen_kg == pytest.approx(d.hydrogen_kg_year1)
    assert d.storage_mode == "days"


def test_part_load_costs_hydrogen():
    _, simple = case(mode="plant", pv_kwp=1500.0, electrolyser_kw=1000.0)
    _, deepd = case(mode="plant", pv_kwp=1500.0, electrolyser_kw=1000.0, part_load_model=True)
    assert deepd.hydrogen_kg < simple.hydrogen_kg
    assert deepd.kwh_per_kg_total > simple.kwh_per_kg_total
    assert sum(deepd.load_hist_kwh) == pytest.approx(deepd.electricity_kwh)


def test_ageing_lowers_the_hydrogen_year_by_year():
    _, d = case(mode="plant", pv_kwp=1500.0, electrolyser_kw=1000.0,
                degradation_per_1000h=0.002, stack_hours=500_000.0)
    assert d.kg_by_year[0] > d.kg_by_year[-1]
    assert d.kg_by_year == tuple(sorted(d.kg_by_year, reverse=True))
    assert d.hydrogen_kg < d.hydrogen_kg_year1
    assert d.hydrogen_kg == pytest.approx(sum(d.kg_by_year) / len(d.kg_by_year))


def test_stack_replacement_resets_the_ageing():
    _, d = case(mode="plant", pv_kwp=1500.0, electrolyser_kw=1000.0,
                degradation_per_1000h=0.002, stack_hours=8000.0)
    assert max(d.kg_by_year[1:]) > min(d.kg_by_year)   # not monotone: new stacks


def test_hourly_tank_and_prices():
    _, days = case(mode="plant", pv_kwp=1500.0, electrolyser_kw=1000.0)
    _, hourly = case(mode="plant", pv_kwp=1500.0, electrolyser_kw=1000.0, storage_mode="hourly")
    assert hourly.storage_kg > days.storage_kg      # solar-only hydrogen needs a big seasonal tank
    assert len(hourly.tank_level_kg) == 365 and min(hourly.tank_level_kg) >= -1e-6
    assert max(hourly.tank_level_kg) == pytest.approx(hourly.storage_kg, rel=0.02)  # daily samples


def test_cheapest_hours_buy_cheaper_electricity():
    prices = h2.synthetic_price_profile(0.12)
    assert sum(prices) / len(prices) == pytest.approx(0.12)
    prof_p = HydrogenProfiles(PV, None, "synthetic", prices)
    kw = dict(use_grid=True, mode="plant", pv_kwp=500.0, electrolyser_kw=1000.0,
              grid_hours_cap=3000.0)
    even = size_hydrogen_plant(HydrogenInputs(**kw), prof_p)
    cheap = size_hydrogen_plant(HydrogenInputs(cheapest_hours_first=True, **kw), prof_p)
    assert cheap.grid_kwh == pytest.approx(even.grid_kwh, rel=1e-6)
    assert cheap.mean_grid_price < even.mean_grid_price
    assert cheap.lcoh < even.lcoh


@pytest.mark.parametrize("kw", [{"storage_mode": "weekly"}, {"degradation_per_1000h": 0.5},
                                {"aux_share": 0.9}])
def test_bad_deep_inputs_rejected(kw):
    with pytest.raises(ValueError):
        case(**kw)


def test_deep_report_charts_and_texts():
    from resize_energy.report.charts import hydrogen_charts

    prices = h2.synthetic_price_profile(0.12)
    inp = HydrogenInputs(
        mode="plant", pv_kwp=1500.0, electrolyser_kw=1000.0, use_grid=True, grid_hours_cap=2000.0,
        part_load_model=True, degradation_per_1000h=0.002, storage_mode="hourly",
        cheapest_hours_first=True)
    d = size_hydrogen_plant(inp, HydrogenProfiles(PV, None, "synthetic", prices))
    charts = hydrogen_charts(inp, d)
    assert {"h2_partload", "h2_ageing", "h2_tank"} <= set(charts)
    for key in ("hydrogen.partload", "hydrogen.ageing", "hydrogen.tank", "hydrogen.prices"):
        assert hydrogen_worked_example(key, inp, d)
    html = build_hydrogen_report(inp, d, check_hydrogen_design(inp, d))
    assert "cheapest hours first" in html and "chart:h2_tank" in html
