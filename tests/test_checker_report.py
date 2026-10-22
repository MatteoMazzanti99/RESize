from resize_energy.core.pv_design import InverterSpec, ModuleSpec, PVInputs, size_pv_system
from resize_energy.report.html_report import build_pv_report
from resize_energy.tutor.checker import check_pv_design


def run(**kw):
    defaults = dict(annual_demand_kwh=4500, annual_irradiation_kwh_m2=1500, performance_ratio=0.8)
    defaults.update(kw)
    inp = PVInputs(**defaults)
    design = size_pv_system(inp)
    return inp, design, check_pv_design(inp, design)


def codes(findings, severity):
    return {f.code for f in findings if f.severity == severity}


def test_default_design_has_no_errors_or_warnings():
    _, _, findings = run()
    assert not codes(findings, "error")
    assert not codes(findings, "warning")
    assert "dc_ac" in codes(findings, "ok")


def test_oversized_inverter_is_flagged():
    _, _, findings = run(inverter=InverterSpec(p_ac_kw=10.0))
    assert "dc_ac" in codes(findings, "warning")


def test_infeasible_string_window_is_an_error():
    _, _, findings = run(inverter=InverterSpec(mppt_vmin_v=500, mppt_vmax_v=520))
    assert "string_window" in codes(findings, "error")


def test_capped_array_warns_about_low_coverage():
    _, _, findings = run(annual_demand_kwh=60000, inverter=InverterSpec(p_ac_kw=20))
    assert "coverage_low" in codes(findings, "warning")


def test_unusual_performance_ratio_warns():
    _, _, findings = run(performance_ratio=0.95)
    assert "pr_range" in codes(findings, "warning")


def test_report_contains_sections_and_escapes_html():
    module = ModuleSpec(name="<b>Evil</b> module")
    inp, design, findings = run(module=module)
    html = build_pv_report(inp, design, findings, site_note="Turin & surroundings")
    assert "Preliminary PV sizing report" in html
    assert "&lt;b&gt;Evil&lt;/b&gt; module" in html
    assert "<b>Evil</b>" not in html
    assert "Turin &amp; surroundings" in html
    assert "Design checks" in html
    assert "DISCLAIMER" in html
    assert "DC/AC" in html
