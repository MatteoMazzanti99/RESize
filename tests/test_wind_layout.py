"""Turbine placement inside a site area, with the wind rose."""

import math

import pytest

from resize_energy.core import wind_wake as ww
from resize_energy.core.wind_design import WindInputs, size_wind_plant
from resize_energy.core.wind_layout import (
    SiteArea,
    initial_layout,
    max_turbines,
    optimise_layout,
    surrogate_loss,
)
from resize_energy.core.wind_rose import rose_from_series

D = 90.0


def _min_dist(pos):
    return min(math.dist(a, b) for i, a in enumerate(pos) for b in pos[i + 1:])


def test_area_corners_and_rotation():
    a = SiteArea(1000, 2000, 0)
    corners = a.corners()
    assert (-500, -1000) in [(round(x), round(y)) for x, y in corners]
    assert a.contains(0, 900) and not a.contains(0, 1100) and not a.contains(600, 0)
    turned = SiteArea(1000, 2000, 90)               # the long side now runs east-west
    assert turned.contains(900, 0) and not turned.contains(0, 900)
    assert a.area_km2 == pytest.approx(2.0)
    with pytest.raises(ValueError):
        SiteArea(0, 100)


def test_initial_layout_fits_or_explains():
    area = SiteArea(1500, 1500)
    pts = initial_layout(10, area, 3 * D)
    assert len(pts) == 10
    with pytest.raises(ValueError, match="too small"):
        initial_layout(500, area, 3 * D)
    assert max_turbines(area, 3 * D) >= 10


@pytest.mark.parametrize("rotation", [0.0, 35.0, 90.0])
def test_optimised_layout_respects_the_area_and_the_spacing(rotation):
    area = SiteArea(1800, 1200, rotation)
    w = ww.rose_weights(270.0, 2.0)
    pos = optimise_layout(9, area, D, 3.0, w, 0.075, steps=1500)
    assert len(pos) == 9
    assert all(area.contains(e, n) for e, n in pos)
    assert _min_dist(pos) >= 3.0 * D - 1e-6


def test_optimiser_is_deterministic_and_beats_a_regular_grid():
    area = SiteArea(2500, 2500)
    w = ww.rose_weights(270.0, 2.0)
    a = optimise_layout(12, area, D, 3.0, w, 0.075, steps=3000)
    b = optimise_layout(12, area, D, 3.0, w, 0.075, steps=3000)
    assert a == b
    grid = ww.grid_layout(12, 3, 5, 7, D, True, 270.0)
    assert surrogate_loss(a, D, 0.075, w) < surrogate_loss(grid, D, 0.075, w)


def test_a_single_turbine_and_a_too_small_site():
    assert len(optimise_layout(1, SiteArea(500, 500), D, 3.0, (1 / 12,) * 12, 0.075)) == 1
    with pytest.raises(ValueError):
        optimise_layout(20, SiteArea(400, 400), D, 3.0, (1 / 12,) * 12, 0.075)
    with pytest.raises(ValueError):
        optimise_layout(2, SiteArea(900, 900), 0.0, 3.0, (1 / 12,) * 12, 0.075)


def _rose():
    speeds = [7.0 + (i % 4) for i in range(9000)]
    dirs = [(270.0 + 40.0 * math.sin(i / 11.0)) % 360 for i in range(9000)]
    return rose_from_series(speeds, dirs)


def test_wake_uses_the_speed_of_each_direction():
    rose = _rose()
    inp = WindInputs(annual_demand_kwh=30e6, mean_speed_ref_ms=6.5, wake_model=True, rose=rose,
                     prevailing_direction_deg=rose.prevailing_deg())
    d = size_wind_plant(inp)
    assert d.wake is not None and d.wake.sector_weights == rose.frequency
    assert 0.0 < d.wake_loss < 0.2


def test_optimised_design_has_fewer_wake_losses_than_the_grid():
    rose = _rose()
    base = WindInputs(annual_demand_kwh=40e6, mean_speed_ref_ms=6.5, rose=rose,
                      prevailing_direction_deg=rose.prevailing_deg(), layout_mode="optimized",
                      site_width_m=2500, site_length_m=2500, min_spacing_d=3.0)
    d = size_wind_plant(base)
    assert d.layout_mode == "optimized" and d.site is not None and d.grid_wake_loss is not None
    assert d.wake_loss < d.grid_wake_loss
    assert d.min_distance_d >= 3.0 - 1e-6
    assert d.array_area_km2 == pytest.approx(6.25)
    assert all(d.site.contains(e, n) for e, n in d.wake.positions)
    assert len(d.wake.positions) == d.n_turbines


def test_optimised_design_explains_a_site_that_is_too_small():
    inp = WindInputs(annual_demand_kwh=40e6, mean_speed_ref_ms=6.5, layout_mode="optimized",
                     site_width_m=300, site_length_m=300)
    with pytest.raises(ValueError, match="too small"):
        size_wind_plant(inp)
    with pytest.raises(ValueError):
        size_wind_plant(WindInputs(annual_demand_kwh=1e6, mean_speed_ref_ms=6.0, layout_mode="x"))


def test_optimised_pieces_for_tutor_report_and_charts():
    from resize_energy.report.charts import wind_charts
    from resize_energy.report.html_report import build_wind_report
    from resize_energy.tutor.checker_wind import check_wind_design
    from resize_energy.tutor.context_wind import build_wind_context
    from resize_energy.tutor.explanations import EXPLANATIONS
    from resize_energy.tutor.worked_wind import wind_worked_example

    rose = _rose()
    inp = WindInputs(annual_demand_kwh=40e6, mean_speed_ref_ms=6.5, rose=rose,
                     prevailing_direction_deg=rose.prevailing_deg(), layout_mode="optimized",
                     site_width_m=2500, site_length_m=2500)
    d = size_wind_plant(inp)
    findings = check_wind_design(inp, d)
    assert all(f.explanation_key in EXPLANATIONS for f in findings if f.explanation_key)
    assert any(f.code == "layout_ground" for f in findings)
    text = wind_worked_example("wind.layout", inp, d)
    assert "regular" in text and any(ch.isdigit() for ch in text)
    assert "measured" in wind_worked_example("wind.rose", inp, d).lower()
    assert "placed by the program" in build_wind_context(inp, d, findings)
    charts = wind_charts(inp, d)
    assert charts["wind_layout_map"].kind == "svg" and "<circle" in charts["wind_layout_map"].svg
    assert charts["wind_rose_polar"].svg.startswith("<svg")
    for theme in ("light", "screen"):
        html = build_wind_report(inp, d, findings, theme=theme)
        assert "placed by the program" in html and "chart:wind_layout_map" in html
