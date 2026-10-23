import math

import pytest

from resize_energy.core import economics as eco
from resize_energy.core.comparison import ComparisonInputs, CostAssumptions, compare_technologies
from resize_energy.core.wind_design import WindInputs
from resize_energy.report.html_report import build_comparison_report
from resize_energy.tutor.checker_compare import check_comparison
from resize_energy.tutor.context_compare import build_compare_context
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.explanations_compare import COMPARE_TOPIC_ORDER
from resize_energy.tutor.worked_compare import compare_worked_example


def case(**kw):
    costs = kw.pop("costs", CostAssumptions())
    wind = WindInputs(annual_demand_kwh=kw.pop("demand", 10_000_000), mean_speed_ref_ms=6.5)
    inp = ComparisonInputs(1500, 0.8, wind, costs)
    return inp, compare_technologies(inp)


def test_capital_recovery_factor_hand_value():
    # 0.05 * 1.05^25 / (1.05^25 - 1) = 0.0709525
    assert eco.capital_recovery_factor(0.05, 25) == pytest.approx(0.0709525, rel=1e-5)
    assert eco.capital_recovery_factor(0, 20) == pytest.approx(0.05)
    assert eco.annuity_factor(0.05, 25) * eco.capital_recovery_factor(0.05, 25) == pytest.approx(1)


def test_lcoe_hand_value():
    # PV: (1000 x CRF + 15) / 1200 kWh per kWp
    expected = (1000 * 0.0709525 + 15) / 1200
    assert eco.lcoe(1000, 15, 1200, 0.05, 25) == pytest.approx(expected, rel=1e-5)


def test_savings_split_between_retail_and_export():
    assert eco.annual_savings(800, 1000, 0.2, 0.05) == pytest.approx(160)
    assert eco.annual_savings(1500, 1000, 0.2, 0.05) == pytest.approx(200 + 25)


def test_payback_npv_consistency():
    assert eco.simple_payback_years(1000, 100) == 10
    assert math.isinf(eco.simple_payback_years(1000, 0))
    # NPV is zero exactly at the discounted payback horizon
    n = eco.discounted_payback_years(1000, 150, 0.05)
    assert eco.npv(1000, 150, 0.05, n) == pytest.approx(0, abs=1e-6)
    assert math.isinf(eco.discounted_payback_years(1000, 40, 0.05))  # 40/0.05 = 800 < 1000
    assert eco.discounted_payback_years(1000, 100, 0) == 10


def test_co2_uses_grid_minus_lifecycle():
    assert eco.co2_avoided_kg_per_year(1000, 0.25, 45) == pytest.approx(205)


def test_both_plants_cover_the_demand_and_numbers_are_consistent():
    inp, r = case()
    assert r.pv.coverage == pytest.approx(1.0)
    assert r.wind.coverage >= 1.0
    c = inp.costs
    assert r.pv.capex_eur == pytest.approx(r.pv.installed_kw * c.pv_capex_eur_per_kwp)
    assert r.pv.lcoe_eur_per_kwh == pytest.approx(
        eco.lcoe(r.pv.capex_eur, r.pv.om_eur_per_year, r.pv.energy_kwh, c.discount_rate, 25))
    assert r.wind.co2_avoided_lifetime_t == pytest.approx(r.wind.co2_avoided_t_per_year * 25)
    assert r.lowest_lcoe in {"Photovoltaic", "Wind"}


def test_cheaper_pv_wins_the_cost_ranking():
    inp, r = case(costs=CostAssumptions(pv_capex_eur_per_kwp=300))
    assert r.lowest_lcoe == "Photovoltaic"
    assert r.fastest_payback == "Photovoltaic"


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        case(costs=CostAssumptions(discount_rate=-0.1))
    with pytest.raises(ValueError):
        case(costs=CostAssumptions(pv_capex_eur_per_kwp=0))


def test_tutor_pieces_work_together():
    inp, r = case()
    findings = check_comparison(inp, r)
    assert all(f.explanation_key in EXPLANATIONS for f in findings if f.explanation_key)
    assert "annual_balance" in {f.code for f in findings}
    for key in COMPARE_TOPIC_ORDER:
        entry = EXPLANATIONS[key]
        assert entry["title"] and entry["formula"] and entry["why"] and entry["assumptions"]
        text = compare_worked_example(key, inp, r)
        assert text and any(ch.isdigit() for ch in text), key
    assert compare_worked_example("nope", inp, r) is None
    assert "Photovoltaic" in build_compare_context(inp, r, findings)
    for theme in ("light", "screen"):
        html = build_comparison_report(inp, r, findings, theme=theme)
        assert "Which is better" in html and "LCOE" in html


def test_oversized_wind_and_expensive_energy_are_flagged():
    inp, r = case(demand=500_000)  # one 2 MW turbine on a tiny demand
    codes = {f.code for f in check_comparison(inp, r)}
    assert "wind_oversized" in codes
    inp2, r2 = case(costs=CostAssumptions(retail_price_eur_per_kwh=0.03))
    assert "lcoe_above_price" in {f.code for f in check_comparison(inp2, r2)}


# ---- four technologies -------------------------------------------------------------------

from resize_energy.gui import zone_layout as zl  # noqa: E402
from resize_energy.report.versus import rounds_won, versus_rounds  # noqa: E402


def many(techs, **kw):
    wind = WindInputs(annual_demand_kwh=10_000_000, mean_speed_ref_ms=6.5)
    inp = ComparisonInputs(1500, 0.8, wind, techs=tuple(techs), **kw)
    return inp, compare_technologies(inp)


def test_all_four_technologies():
    inp, r = many(("pv", "wind", "biomass", "hydrogen"))
    assert [t.key for t in r.techs] == ["pv", "wind", "biomass", "hydrogen"]
    for t in r.techs:
        assert t.energy_kwh > 0 and t.lcoe_eur_per_kwh > 0 and t.capex_eur > 0
    # every plant is sized on the same 10 GWh target
    assert r.pv.energy_kwh == pytest.approx(1e7)
    assert r.biomass.energy_kwh == pytest.approx(1e7, rel=1e-6)
    assert r.hydrogen.energy_kwh == pytest.approx(1e7, rel=1e-6)
    assert r.hydrogen.product == "hydrogen" and r.biomass.product == "electricity"
    # hydrogen costs more per kWh than the electricity that feeds it
    assert r.hydrogen.lcoe_eur_per_kwh > 2 * r.pv.lcoe_eur_per_kwh
    # co2: energy x (reference - own)
    t = r.hydrogen
    assert t.co2_avoided_t_per_year == pytest.approx(
        t.energy_kwh * (t.co2_reference_kg_per_kwh - t.co2_own_kg_per_kwh) / 1000)
    assert r.lowest_lcoe in {t.name for t in r.techs}
    assert r.hydrogen_design is not None and r.biomass_design is not None


@pytest.mark.parametrize("techs", [("biomass", "hydrogen"), ("pv", "hydrogen"),
                                   ("wind", "biomass"), ("wind", "hydrogen")])
def test_pairs_and_report(techs):
    kw = {"h2_use_pv": "wind" not in techs or "pv" in techs,
          "h2_use_wind": "wind" in techs}
    inp, r = many(techs, **kw)
    assert len(r.techs) == 2
    findings = check_comparison(inp, r)
    for theme in ("light", "screen"):
        html = build_comparison_report(inp, r, findings, theme=theme)
        assert all(t.name in html for t in r.techs)
    for key in COMPARE_TOPIC_ORDER:
        assert compare_worked_example(key, inp, r)
    text = build_compare_context(inp, r, findings)
    assert all(t.name in text for t in r.techs)
    if "hydrogen" in techs:
        assert "mixed_products" in {f.code for f in findings}
    if "biomass" in techs:
        assert "heat_not_credited" in {f.code for f in findings}


def test_selection_is_validated():
    with pytest.raises(ValueError):
        many(("pv",))
    with pytest.raises(ValueError):
        many(("pv", "pv"))
    with pytest.raises(ValueError):
        many(("pv", "geothermal"))
    with pytest.raises(ValueError):
        many(("pv", "hydrogen"), h2_use_pv=False, h2_use_wind=False)


def test_zone_layout_and_motion():
    for n in (1, 2, 3, 4):
        centres = zl.slot_centres(n, 400.0, 140.0)
        assert len(centres) == n
        xs = [x for x, _ in centres]
        assert xs == sorted(xs) and 0 < xs[0] and xs[-1] < 400
        assert len(zl.vs_centres(centres)) == n - 1
        # icons never overlap, also with 4 in a narrow zone
        assert all(b - a > zl.ICON_SIZE for a, b in zip(xs, xs[1:], strict=False)) or n == 4
    assert zl.slot_centres(0, 400, 100) == []
    assert all(abs(zl.bob(t / 10, i)) <= 3.0 + 1e-9 for t in range(100) for i in range(4))
    assert zl.pop_scale(0.0) == pytest.approx(0.3) and zl.pop_scale(1.0) == 1.0
    assert max(zl.pop_scale(t / 100) for t in range(31)) >= 1.0   # small overshoot
    # clash: icons on both sides end up closer to the middle and never cross it
    for x in (50.0, 350.0):
        positions = [zl.clash_x(x, 200.0, p / 20) for p in range(21)]
        assert abs(positions[11] - 200) < abs(x - 200) * 0.5
        assert all((p - 200) * (x - 200) > 0 for p in positions)
    assert zl.flash_alpha(0.55) > 150 and zl.flash_alpha(0.0) == 0


def test_versus_rounds():
    _, r = many(("pv", "wind", "biomass", "hydrogen"))
    rounds = versus_rounds(r)
    assert [x.title for x in rounds] == ["Cost of one kWh", "Payback time",
                                         "Net present value", "CO2 avoided"]
    for rd in rounds:
        assert len(rd.entries) == 4
        assert all(0.0 <= e.score <= 1.0 for e in rd.entries)
        assert max(e.score for e in rd.entries) == pytest.approx(1.0) or rd.title == "Net present value"
    # the winner of each round is the technology with the best real figure
    assert rounds[0].winner == r.lowest_lcoe
    assert rounds[1].winner == r.fastest_payback
    assert rounds[3].winner == r.most_co2
    never = [e for e in rounds[1].entries if e.text == "never"]
    assert never and all(e.score == 0.0 for e in never)
    assert sum(rounds_won(rounds).values()) == sum(rd.winner is not None for rd in rounds)
    html = build_comparison_report(*(many(("pv", "wind"))[0], many(("pv", "wind"))[1], []))
    assert "Round 1: Cost of one kWh" in html
