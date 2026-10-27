"""Borehole heat exchanger (ASHRAE length method): building blocks and the field design."""

import math

import pytest

from resize_energy.core import bhe
from resize_energy.core.bhe_design import BheInputs, size_bhe_field

# Ground and borehole data of a Turin master's-course case (MSc Geothermal Energy report).
TURIN = dict(ground_temp_c=15.7, ground_conductivity=1.7, ground_density=2200.0,
             ground_cp=1091.0, spacing_m=7.0, max_depth_m=400.0, cop_design=3.8,
             cop_seasonal=4.7, eer_design=3.3, eer_seasonal=4.1, grout_conductivity=1.0,
             pipe_conductivity=0.3)


def test_g_function_and_fourier():
    assert bhe.g_function(1.0) == pytest.approx(0.1009)
    assert bhe.g_function(math.e ** 2) == pytest.approx(0.2525)
    assert bhe.g_function(1e-9) == 0.0                  # never negative
    assert bhe.fourier_number(1e-6, 86400.0, 0.2) == pytest.approx(4 * 1e-6 * 86400 / 0.04)
    with pytest.raises(ValueError):
        bhe.g_function(0.0)


def test_ground_resistances_of_the_turin_case():
    alpha = bhe.thermal_diffusivity(1.7, 2200.0, 1091.0)
    assert alpha == pytest.approx(7.0827e-7, rel=1e-4)
    r_ga, r_gm, r_gd = bhe.ground_resistances(1.7, alpha, 0.15)
    assert r_ga == pytest.approx(0.2141, abs=2e-4)
    assert r_gm == pytest.approx(0.2138, abs=2e-4)
    assert r_gd == pytest.approx(0.1040, abs=2e-4)
    # independent evaluation of the three Fourier numbers
    day = 86400.0
    tau_f = (3650 + 30 + 0.25) * day
    g_f = 0.0758 * math.log(4 * alpha * tau_f / 0.0225) + 0.1009
    g_1 = 0.0758 * math.log(4 * alpha * (30.25 * day) / 0.0225) + 0.1009
    assert r_ga == pytest.approx((g_f - g_1) / 1.7)


def test_borehole_resistances():
    r_gr = bhe.grout_resistance(0.15, 0.032, 0.0452, 1.0)
    assert r_gr == pytest.approx(0.0446, abs=3e-4)
    assert bhe.grout_resistance(0.15, 0.032, 0.0452, 2.0) == pytest.approx(r_gr / 2)
    wall_only = bhe.pipe_resistance(0.032, 0.0262, 0.3, 1e9)
    assert wall_only == pytest.approx(math.log(32 / 26.2) / (2 * math.pi * 0.3) / 2, rel=1e-6)
    with pytest.raises(ValueError):
        bhe.grout_resistance(0.15, 0.032, 0.16, 1.0)    # pipes outside the borehole
    with pytest.raises(ValueError):
        bhe.pipe_resistance(0.02, 0.03, 0.4, 500.0)


def test_film_coefficient_regimes():
    laminar = bhe.film_coefficient(1500.0, 30.0, 0.45, 0.0262)
    assert laminar == pytest.approx(4.36 * 0.45 / 0.0262)
    turbulent = bhe.film_coefficient(10000.0, 30.0, 0.45, 0.0262)
    assert turbulent > 5 * laminar
    assert bhe.reynolds(1.0, 0.0262, 0.0045) == pytest.approx(4 / (math.pi * 0.0262 * 0.0045))


def test_penalty_denominator_reproduces_the_report_iteration():
    # The report goes from L = 8387.6 m (penalty 0) to 8873.7 m (penalty -0.783 K) in cooling:
    # same numerator, the denominator t_g - t_fluid - t_p goes from -14.3 to -13.517.
    kwargs = dict(q_annual_w=-1000.0, q_peak_ground_w=-5.0e5, r_ga=0.2141, r_b=0.1,
                  r_gm=0.2138, r_gd=0.104, plf_month=0.5, f_sc=1.05, t_ground=15.7,
                  t_fluid_mean=30.0, heating=False)
    l0 = bhe.required_length(t_penalty=0.0, **kwargs)
    l1 = bhe.required_length(t_penalty=-0.783, **kwargs)
    assert l0 > 0
    assert l1 / l0 == pytest.approx(8873.7 / 8387.6, rel=1e-3)


def test_wrong_sign_of_the_temperature_difference_is_refused():
    with pytest.raises(ValueError):
        bhe.required_length(1.0, 1.0, 0.2, 0.1, 0.2, 0.1, 0.5, 1.05, 15.0, 20.0, 0.0)


def test_neighbour_counts():
    assert bhe.neighbour_counts(9, 3) == (1, 4, 4, 0)
    assert bhe.neighbour_counts(4, 4) == (0, 0, 2, 2)    # a line of four
    assert bhe.neighbour_counts(1, 1) == (0, 0, 0, 0)
    assert sum(bhe.neighbour_counts(23, 5)) == 23
    assert bhe.temperature_penalty(9, 3, 1.0) == pytest.approx((1 + 2 + 1) / 9)
    with pytest.raises(ValueError):
        bhe.neighbour_counts(0, 3)


def test_theta_p1_sign_and_scale():
    drift = bhe.theta_p1(-3.7e10, 2.4e6, 7.0, 400.0)
    assert drift < 0                                     # heat stored: the ground warms
    assert drift == pytest.approx(-3.7e10 / (2.4e6 * 49 * 400))


def _turin(**over):
    d = dict(TURIN, heating_kwh_per_year=450_000.0, heating_peak_kw=400.0,
             cooling_kwh_per_year=300_000.0, cooling_peak_kw=450.0)
    d.update(over)
    return BheInputs(**d)


def test_field_design_is_governed_by_cooling_and_converges():
    d = size_bhe_field(_turin())
    assert d.governing == "cooling"
    assert d.length_cooling_m > d.length_heating_m > 0
    assert d.total_length_m == pytest.approx(d.length_cooling_m)
    assert d.boreholes == math.ceil(d.total_length_m / 400.0)
    assert d.depth_m == pytest.approx(d.total_length_m / d.boreholes)
    assert d.depth_m <= 400.0
    assert d.penalty_c < 0                               # cooling-dominated: the ground warms
    assert d.length_first_m < d.total_length_m           # the penalty lengthens the field
    assert d.steps[-1].error < 1e-3 and not d.warnings[1:]
    assert d.rows * d.columns >= d.boreholes
    assert d.area_needed_m2 == pytest.approx(d.boreholes * 49.0)
    assert d.capex == pytest.approx(d.total_length_m * 60.0)


def test_more_load_needs_more_boreholes():
    small = size_bhe_field(_turin())
    big = size_bhe_field(_turin(cooling_peak_kw=700.0, cooling_kwh_per_year=450_000.0))
    assert big.total_length_m > small.total_length_m


def test_balanced_loads_have_a_small_penalty():
    # extracted 450 MWh x (1 - 1/4.7) = injected E x (1 + 1/4.1) at E = 284.6 MWh
    balanced = size_bhe_field(_turin(cooling_kwh_per_year=284_600.0))
    cooling_heavy = size_bhe_field(_turin(cooling_kwh_per_year=380_000.0))
    assert abs(balanced.q_annual_w) < 100.0
    assert abs(balanced.penalty_c) < 0.05
    assert cooling_heavy.penalty_c < balanced.penalty_c
    assert cooling_heavy.total_length_m > balanced.total_length_m
    assert size_bhe_field(_turin(cooling_kwh_per_year=200_000.0)).q_annual_w > 0


def test_exponential_integral():
    assert bhe.exp_integral_e1(0.1) == pytest.approx(1.822924, abs=1e-5)
    assert bhe.exp_integral_e1(1.0) == pytest.approx(0.219384, abs=1e-5)
    assert bhe.exp_integral_e1(2.5) == pytest.approx(0.024915, abs=1e-5)
    with pytest.raises(ValueError):
        bhe.exp_integral_e1(0.0)


def test_line_source_penalty():
    alpha = 7.08e-7
    assert bhe.line_source_penalty(1, 1, 7.0, alpha, 1.7, 10.0, 5.0) == 0.0
    pair = bhe.line_source_penalty(2, 2, 7.0, alpha, 1.7, 10.0, 5.0)
    expect = 5.0 / (4 * math.pi * 1.7) * bhe.exp_integral_e1(49 / (4 * alpha * 10 * 365 * 86400))
    assert pair == pytest.approx(expect)
    big = bhe.line_source_penalty(25, 5, 7.0, alpha, 1.7, 10.0, 5.0)
    assert big > pair                                    # more neighbours, more interference
    wide = bhe.line_source_penalty(25, 5, 14.0, alpha, 1.7, 10.0, 5.0)
    assert wide < big
    assert bhe.line_source_penalty(25, 5, 7.0, alpha, 1.7, 10.0, -5.0) == pytest.approx(-big)


def test_storage_method_of_the_course():
    d = size_bhe_field(_turin(cooling_kwh_per_year=270_000.0, penalty_method="storage"))
    assert d.penalty_c > 0 and d.boreholes >= 1
    with pytest.raises(ValueError):
        size_bhe_field(_turin(penalty_method="magic"))


def test_heating_only_field():
    d = size_bhe_field(_turin(cooling_kwh_per_year=0.0, cooling_peak_kw=0.0))
    assert d.length_cooling_m == 0.0
    assert d.governing == "heating"
    assert d.q_ground_cooling_w == 0.0
    assert d.total_length_m == pytest.approx(d.length_heating_m)


def test_area_check_and_depth_cap():
    d = size_bhe_field(_turin(available_area_m2=500.0))
    assert d.fits_area is False
    assert any("m2" in w for w in d.warnings)
    deep = size_bhe_field(_turin(max_depth_m=100.0))
    assert deep.depth_m <= 100.0
    assert deep.boreholes > d.boreholes
    assert size_bhe_field(_turin()).fits_area is None


def test_fixed_columns():
    d = size_bhe_field(_turin(columns=3))
    assert d.columns == 3
    assert d.rows == math.ceil(d.boreholes / 3)


@pytest.mark.parametrize("bad", [
    dict(heating_kwh_per_year=0.0, cooling_kwh_per_year=0.0),
    dict(heating_peak_kw=10.0),                          # too low for 450 MWh
    dict(cop_design=0.9),
    dict(fluid_in_heating_c=1.0, fluid_out_heating_c=2.0),
    dict(fluid_in_cooling_c=33.0, fluid_out_cooling_c=32.0),
    dict(spacing_m=0.0),
    dict(drilling_eur_per_m=-1.0),
])
def test_invalid_inputs_are_refused(bad):
    with pytest.raises(ValueError):
        size_bhe_field(_turin(**bad))


# --- tutor, report and pictures (all Qt-free) ---------------------------------------------------
def test_every_topic_has_a_worked_example_with_the_users_numbers():
    from resize_energy.tutor.explanations_bhe import BHE_TOPIC_ORDER
    from resize_energy.tutor.worked_bhe import bhe_worked_example

    inp = _turin()
    d = size_bhe_field(inp)
    for key in BHE_TOPIC_ORDER:
        text = bhe_worked_example(key, inp, d)
        assert text and text.strip(), key
    assert f"{d.boreholes}" in bhe_worked_example("bhe.field", inp, d)
    assert "governs" in bhe_worked_example("bhe.length", inp, d)
    assert bhe_worked_example("bhe.nothing", inp, d) is None


def test_checker_context_report_and_picture():
    from resize_energy.report.charts_bhe import bhe_charts
    from resize_energy.report.flow_pictures import bhe_picture
    from resize_energy.report.html_report_bhe import build_bhe_report
    from resize_energy.tutor.checker_bhe import check_bhe_design
    from resize_energy.tutor.context_bhe import build_bhe_context

    inp = _turin(cooling_kwh_per_year=150_000.0)
    d = size_bhe_field(inp)
    findings = check_bhe_design(inp, d)
    assert findings and all(f.message for f in findings)
    assert any(f.code == "imbalance" for f in findings)       # 150 MWh of cooling: unbalanced
    for theme in ("light", "screen"):
        html = build_bhe_report(inp, d, findings, theme=theme)
        assert "Method and formulas" in html and "Kavanaugh" in html and "bhe_lengths" in html
        assert f"{d.boreholes} x" in html
    assert set(bhe_charts(inp, d)) >= {"bhe_lengths", "bhe_balance"}
    assert "ground-source" in build_bhe_context(inp, d, findings)
    nodes, flows = bhe_picture(inp, d)
    assert len(nodes) == 3 and len(flows) == 2


def test_checker_flags_a_laminar_flow_and_a_missing_area():
    from resize_energy.tutor.checker_bhe import check_bhe_design

    inp = _turin(available_area_m2=300.0, spacing_m=4.0)
    findings = check_bhe_design(inp, size_bhe_field(inp))
    codes = {f.code for f in findings}
    assert {"area", "spacing_close"} <= codes
