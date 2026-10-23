from resize_energy.core.pv_design import InverterSpec, PVInputs, size_pv_system
from resize_energy.report.html_report import build_pv_report
from resize_energy.tutor.checker import check_pv_design
from resize_energy.tutor.explanations import EXPLANATIONS, TOPIC_ORDER
from resize_energy.tutor.explanations_biomass import BIOMASS_TOPIC_ORDER
from resize_energy.tutor.explanations_compare import COMPARE_TOPIC_ORDER
from resize_energy.tutor.explanations_hydrogen import HYDROGEN_TOPIC_ORDER
from resize_energy.tutor.explanations_wind import WIND_TOPIC_ORDER
from resize_energy.tutor.why_html import explanation_html
from resize_energy.tutor.worked import worked_example


def case(**kw):
    defaults = dict(annual_demand_kwh=4500, annual_irradiation_kwh_m2=1500, performance_ratio=0.8)
    defaults.update(kw)
    inp = PVInputs(**defaults)
    return inp, size_pv_system(inp)


def test_topic_order_covers_exactly_the_explanations():
    orders = [set(TOPIC_ORDER), set(WIND_TOPIC_ORDER), set(COMPARE_TOPIC_ORDER),
              set(BIOMASS_TOPIC_ORDER), set(HYDROGEN_TOPIC_ORDER)]
    assert set().union(*orders) == set(EXPLANATIONS)
    assert sum(len(o) for o in orders) == len(set().union(*orders))  # no key in two modules
    assert len(TOPIC_ORDER) == len(set(TOPIC_ORDER))


def test_every_entry_has_the_required_fields():
    for key, entry in EXPLANATIONS.items():
        for field in ("title", "formula", "why", "assumptions"):
            assert entry.get(field), f"{key} lacks {field}"


def test_every_topic_has_a_worked_example():
    inp, design = case()
    for key in TOPIC_ORDER:
        text = worked_example(key, inp, design)
        assert isinstance(text, str) and text.strip(), key


def test_unknown_topic_has_no_worked_example():
    inp, design = case()
    assert worked_example("pv.does_not_exist", inp, design) is None


def test_worked_numbers_match_hand_calculation():
    inp, design = case()
    assert "3.75 kWp" in worked_example("pv.required_peak_power", inp, design)
    assert "= 10" in worked_example("pv.required_peak_power", inp, design)
    # Voc(-10) = 37.5 * (1 + 0.0027 * 35) = 41.04 V; floor(1000 / 41.04) = 24
    text = worked_example("pv.max_modules_per_string", inp, design)
    assert "41.04 V" in text and "= 24" in text
    # Vmp(-10) = 31.5 * (1 + 0.0034 * 35) = 35.25 V; floor(800 / 35.25) = 22
    text = worked_example("pv.mppt_window_cold", inp, design)
    assert "35.25 V" in text and "= 22" in text
    # Vmp(70) = 31.5 * (1 - 0.0034 * 45) = 26.68 V; ceil(200 / 26.68) = 8
    text = worked_example("pv.min_modules_per_string", inp, design)
    assert "26.68 V" in text and "= 8" in text
    assert "10 in series x 1 in parallel = 10 modules" in worked_example(
        "pv.string_layout", inp, design)
    assert "4.10 kWp / 4.0 kW" in worked_example("pv.dc_ac_ratio", inp, design)
    assert "4,920 kWh" in worked_example("pv.annual_energy", inp, design)


def test_worked_example_for_infeasible_design_says_so():
    inp, design = case(inverter=InverterSpec(mppt_vmin_v=500, mppt_vmax_v=520))
    assert "No valid string length" in worked_example("pv.string_layout", inp, design)


def test_checker_explanation_keys_exist():
    scenarios = [
        case(),
        case(inverter=InverterSpec(p_ac_kw=10.0)),
        case(inverter=InverterSpec(mppt_vmin_v=500, mppt_vmax_v=520)),
        case(annual_demand_kwh=60000),
        case(performance_ratio=0.95),
    ]
    for inp, design in scenarios:
        for finding in check_pv_design(inp, design):
            if finding.explanation_key:
                assert finding.explanation_key in EXPLANATIONS


def test_explanation_html_contains_parts_and_escapes():
    html = explanation_html("pv.dc_ac_ratio", worked="a < b\nsecond line")
    assert "DC/AC ratio" in html
    assert "<b>Formula</b>" in html and "<b>Why</b>" in html
    assert "With your numbers" in html
    assert "a &lt; b<br>second line" in html
    assert "Assumptions" in html


def test_explanation_html_without_worked_and_unknown_key():
    assert "With your numbers" not in explanation_html("pv.dc_ac_ratio")
    assert "No explanation" in explanation_html("pv.nope")


def test_report_includes_user_numbers_in_method_section():
    inp, design = case()
    html = build_pv_report(inp, design, check_pv_design(inp, design))
    assert "With your numbers" in html
    assert "3.75 kWp" in html
    assert "41.04 V" in html
    assert "IEC 62548" in html
