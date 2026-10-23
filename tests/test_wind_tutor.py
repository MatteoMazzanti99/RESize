from resize_energy.core.wind_design import TurbineSpec, WindInputs, size_wind_plant
from resize_energy.report.html_report import build_wind_report
from resize_energy.tutor.checker_wind import check_wind_design
from resize_energy.tutor.context_wind import build_wind_context
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.explanations_wind import WIND_TOPIC_ORDER
from resize_energy.tutor.worked_wind import wind_worked_example


def case(**kw):
    d = dict(annual_demand_kwh=10_000_000, mean_speed_ref_ms=6.5)
    d.update(kw)
    inp = WindInputs(**d)
    return inp, size_wind_plant(inp)


def codes(findings, severity=None):
    return {f.code for f in findings if severity is None or f.severity == severity}


def test_every_wind_topic_has_text_and_a_worked_example():
    inp, d = case()
    for key in WIND_TOPIC_ORDER:
        entry = EXPLANATIONS[key]
        assert entry["title"] and entry["formula"] and entry["why"] and entry["assumptions"]
        example = wind_worked_example(key, inp, d)
        assert example and any(ch.isdigit() for ch in example), key
    assert wind_worked_example("nope", inp, d) is None


def test_default_design_has_no_errors_and_findings_point_to_known_topics():
    inp, d = case()
    findings = check_wind_design(inp, d)
    assert not codes(findings, "error")
    assert all(f.explanation_key in EXPLANATIONS for f in findings if f.explanation_key)


def test_poor_resource_is_an_error():
    inp, d = case(mean_speed_ref_ms=3.5)
    assert "resource" in codes(check_wind_design(inp, d), "error")


def test_inconsistent_datasheet_trips_betz():
    inp, d = case(turbine=TurbineSpec(rated_power_kw=6000, rotor_diameter_m=60, rated_speed_ms=11))
    assert "betz" in codes(check_wind_design(inp, d), "error")


def test_hub_lower_than_the_blade_is_an_error_and_low_clearance_a_warning():
    inp, d = case(turbine=TurbineSpec(hub_height_m=40, rotor_diameter_m=90))
    assert "tip_clearance" in codes(check_wind_design(inp, d), "error")
    inp, d = case(turbine=TurbineSpec(hub_height_m=60, rotor_diameter_m=90))
    assert "tip_clearance" in codes(check_wind_design(inp, d), "warning")


def test_one_turbine_for_a_tiny_demand_is_flagged():
    inp, d = case(annual_demand_kwh=200_000)
    assert d.n_turbines == 1
    assert "oversized" in codes(check_wind_design(inp, d), "warning")


def test_tight_spacing_is_flagged():
    inp, d = case(crosswind_spacing_d=2, downwind_spacing_d=4)
    assert "spacing" in codes(check_wind_design(inp, d), "warning")


def test_context_and_report_contain_the_numbers():
    inp, d = case()
    findings = check_wind_design(inp, d)
    ctx = build_wind_context(inp, d, findings)
    assert f"{d.n_turbines} (" in ctx and "DESIGN CHECKS" in ctx and "wind plant" in ctx
    light = build_wind_report(inp, d, findings)
    dark = build_wind_report(inp, d, findings, theme="dark")
    for html in (light, dark):
        assert "Method and formulas" in html and "With your numbers" in html
        assert f"{d.capacity_factor_net:.1%}" in html
    assert "#E8EEF8" in dark and "#E8EEF8" not in light
