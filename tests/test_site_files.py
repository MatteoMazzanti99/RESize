"""Site boundary and exclusion zones: files, polygon areas and the optimiser that respects them."""

from __future__ import annotations

import io
import json
import math
import zipfile

import numpy as np
import pytest

from resize_energy.core import site_files as sf
from resize_energy.core.wind_design import TurbineSpec, WindInputs, size_wind_plant
from resize_energy.core.wind_layout import SiteArea, max_turbines, optimise_layout
from resize_energy.report.layout_art import layout_svg

D = 100.0
# a box of about 1.6 km x 1.1 km near Turin
BOX = [[7.0, 45.0], [7.02, 45.0], [7.02, 45.01], [7.0, 45.01], [7.0, 45.0]]
HOLE = [[7.008, 45.003], [7.012, 45.003], [7.012, 45.007], [7.008, 45.007], [7.008, 45.003]]


def geojson(*rings, kind="Polygon") -> bytes:
    return json.dumps({"type": "Feature", "geometry": {"type": kind, "coordinates":
                                                       list(rings) if kind == "Polygon"
                                                       else [list(rings)]}}).encode()


KML = """<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark>
<Polygon><outerBoundaryIs><LinearRing><coordinates>
7.0,45.0,0 7.02,45.0,0 7.02,45.01,0 7.0,45.01,0 7.0,45.0,0</coordinates></LinearRing>
</outerBoundaryIs></Polygon></Placemark></Document></kml>"""


def test_geojson_and_kml_and_kmz_give_the_same_site():
    a = sf.site_from_file(geojson(BOX), "a.geojson")
    b = sf.site_from_file(KML.encode(), "b.kml")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("doc.kml", KML)
    c = sf.site_from_file(buf.getvalue(), "c.kmz")
    for other in (b, c):
        assert other.lat == pytest.approx(a.lat) and other.lon == pytest.approx(a.lon)
        assert np.allclose(other.boundary, a.boundary)
    # centred on the box centre; 0.02 deg of longitude at 45 deg is about 1.57 km
    xs = [p[0] for p in a.boundary]
    ys = [p[1] for p in a.boundary]
    assert max(xs) - min(xs) == pytest.approx(0.02 * sf.M_PER_DEG * math.cos(math.radians(45.005)),
                                              rel=1e-6)
    assert max(ys) - min(ys) == pytest.approx(0.01 * sf.M_PER_DEG, rel=1e-6)
    assert (max(xs) + min(xs)) / 2 == pytest.approx(0.0, abs=1e-6)


def test_holes_are_exclusions_and_the_biggest_polygon_is_the_site():
    s = sf.site_from_file(geojson(BOX, HOLE), "a.geojson")
    assert len(s.exclusions) == 1
    both = json.dumps({"type": "MultiPolygon", "coordinates": [
        [[[7.0, 45.0], [7.001, 45.0], [7.001, 45.001], [7.0, 45.0]]], [BOX]]}).encode()
    assert len(sf.site_from_file(both, "m.geojson").boundary) == 4
    rings = sf.exclusions_from_file(geojson(HOLE), "z.geojson", s.lat, s.lon)
    assert len(rings) == 1 and np.allclose(rings[0], s.exclusions[0])
    assert sf.SiteShape.from_dict(s.to_dict()) == s


@pytest.mark.parametrize("data,name", [(b"not json", "x.geojson"), (b"<kml><oops", "x.kml"),
                                       (json.dumps({"type": "Point", "coordinates": [7, 45]})
                                        .encode(), "x.geojson"),
                                       (b"PK\x03\x04junk", "x.kmz")])
def test_bad_files_give_a_readable_error(data, name):
    with pytest.raises(sf.SiteFileError):
        sf.site_from_file(data, name)


def test_a_huge_polygon_is_refused():
    big = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    with pytest.raises(sf.SiteFileError, match="2 degrees"):
        sf.site_from_file(geojson(big), "big.geojson")


# --- the area ----------------------------------------------------------------------------
SQUARE = ((-1000.0, -1000.0), (1000.0, -1000.0), (1000.0, 1000.0), (-1000.0, 1000.0))
POND = ((-300.0, -300.0), (300.0, -300.0), (300.0, 300.0), (-300.0, 300.0))


def test_polygon_area_exclusions_and_setback():
    plain = SiteArea.from_polygon(SQUARE)
    assert plain.area_km2 == pytest.approx(4.0, rel=0.02)
    holed = SiteArea.from_polygon(SQUARE, (POND,))
    assert holed.area_km2 == pytest.approx(4.0 - 0.36, rel=0.03)
    padded = SiteArea.from_polygon(SQUARE, (POND,), setback_m=100.0)
    assert padded.usable_area_km2() < holed.area_km2
    assert holed.contains(800.0, 800.0) and not holed.contains(0.0, 0.0)
    assert not holed.contains(1200.0, 0.0)
    assert not padded.contains(950.0, 0.0) and padded.contains(850.0, 0.0)
    assert not padded.contains(350.0, 0.0)          # 50 m from the pond, inside the setback
    assert holed.corners() == list(SQUARE)


def test_a_concave_polygon():
    ell = ((0.0, 0.0), (2000.0, 0.0), (2000.0, 500.0), (500.0, 500.0), (500.0, 2000.0),
           (0.0, 2000.0))
    a = SiteArea.from_polygon(ell)
    assert a.contains(1000.0, 200.0) and a.contains(200.0, 1000.0)
    assert not a.contains(1000.0, 1000.0)
    assert a.area_km2 == pytest.approx(2000 * 500 / 1e6 + 500 * 1500 / 1e6, rel=0.03)


def test_the_optimiser_keeps_out_of_the_zones_and_inside_the_boundary():
    area = SiteArea.from_polygon(SQUARE, (POND,), setback_m=60.0)
    weights = tuple([1.0 if i == 9 else 0.1 for i in range(12)])      # mostly west wind
    pos = optimise_layout(8, area, D, 3.0, weights, 0.075, steps=1500)
    assert len(pos) == 8
    for e, n in pos:
        assert area.contains(e, n)
        assert not (abs(e) < 300 and abs(n) < 300)
        assert max(abs(e), abs(n)) <= 1000.0 - 60.0 + 1e-6
    d = min(math.dist(a, b) for i, a in enumerate(pos) for b in pos[i + 1:])
    assert d >= 3.0 * D - 1e-6


def test_too_small_a_polygon_says_so():
    tiny = SiteArea.from_polygon(((0.0, 0.0), (400.0, 0.0), (400.0, 400.0), (0.0, 400.0)))
    assert max_turbines(tiny, 300.0) < 6
    with pytest.raises(ValueError, match="too small"):
        optimise_layout(6, tiny, D, 3.0, tuple([1.0] * 12), 0.075, steps=100)


def test_the_design_uses_the_imported_site():
    turbine = TurbineSpec(rated_power_kw=2000.0, rotor_diameter_m=D)
    inp = WindInputs(annual_demand_kwh=15_000_000, mean_speed_ref_ms=7.0, turbine=turbine,
                     layout_mode="optimized", site_polygon=SQUARE, site_exclusions=(POND,),
                     setback_m=50.0, min_spacing_d=3.0)
    d = size_wind_plant(inp)
    assert d.site is not None and d.site.is_polygon
    for e, n in d.wake.positions:
        assert d.site.contains(e, n)
    assert d.array_area_km2 == pytest.approx(d.site.area_km2)
    # the report, the map and the checks know about the polygon
    from resize_energy.report.charts import wind_charts
    from resize_energy.report.html_report import build_wind_report
    from resize_energy.tutor.checker_wind import check_wind_design
    from resize_energy.tutor.worked_wind import wind_worked_example

    html = build_wind_report(inp, d, check_wind_design(inp, d))
    assert "imported boundary" in html and "exclusion zone" in html
    svg = wind_charts(inp, d)["wind_layout_map"].svg
    assert svg.count("<polygon") >= len(d.wake.positions) + 2
    assert "excluded" in svg
    assert "Imported site" in wind_worked_example("wind.layout", inp, d)


def test_the_map_draws_the_zones():
    pos = [(-700.0, 0.0), (700.0, 0.0)]
    plain = layout_svg("t", pos, D, [0.9, 0.95], list(SQUARE), 270.0, 0.075)
    with_zone = layout_svg("t", pos, D, [0.9, 0.95], list(SQUARE), 270.0, 0.075,
                           exclusions=(POND,))
    assert "excluded" not in plain and "excluded" in with_zone
    assert with_zone.count("<polygon") == plain.count("<polygon") + 1


def test_distance_helpers():
    from resize_energy.core.wind_layout import _dist_to_ring, _in_ring

    pts = np.array([[0.0, 0.0], [1500.0, 0.0], [1000.0, 0.0]])
    assert list(_in_ring(pts, SQUARE))[:2] == [True, False]
    assert _dist_to_ring(np.array([[0.0, 0.0]]), SQUARE)[0] == pytest.approx(1000.0)
