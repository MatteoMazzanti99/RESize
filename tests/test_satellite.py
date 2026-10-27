"""Satellite tiles under the layout map: tile maths, download (mocked) and the SVG."""

from __future__ import annotations

import io
import math
import re

from resize_energy.core import satellite as sat
from resize_energy.report.layout_art import layout_svg, layout_window

PIL = __import__("pytest").importorskip("PIL.Image")


def _jpeg(colour=(60, 120, 60)) -> bytes:
    buf = io.BytesIO()
    PIL.new("RGB", (256, 256), colour).save(buf, "JPEG")
    return buf.getvalue()


class _Resp:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def read(self) -> bytes:
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


WINDOW = (-900.0, 900.0, -700.0, 700.0)


def test_tile_size_in_metres_matches_the_mercator_scale():
    z = sat.choose_zoom(45.0, 7.0, WINDOW)
    assert 1 <= z <= sat.MAX_ZOOM
    assert len(sat.tile_grid(45.0, 7.0, WINDOW, z)) <= sat.MAX_TILES
    # one zoom level sharper would need too many tiles
    if z < sat.MAX_ZOOM:
        assert len(sat.tile_grid(45.0, 7.0, WINDOW, z + 1)) > sat.MAX_TILES
    assert math.isclose(sat.metres_per_pixel(0.0, 0), 156543.03392)
    assert math.isclose(sat.metres_per_pixel(60.0, 3), 156543.03392 * 0.5 / 8, rel_tol=1e-9)


def test_tiles_cover_the_window(tmp_path):
    calls = []

    def fake(req, timeout=0):
        calls.append(req.full_url)
        return _Resp(_jpeg())

    s = sat.fetch_satellite(45.07, 7.69, WINDOW, urlopen=fake, cache_dir=tmp_path)
    assert s.ok and len(s.tiles) == len(calls)
    assert min(t.west_m for t in s.tiles) <= WINDOW[0]
    assert max(t.west_m + t.size_m for t in s.tiles) >= WINDOW[1]
    assert max(t.north_m for t in s.tiles) >= WINDOW[3]
    assert min(t.north_m - t.size_m for t in s.tiles) <= WINDOW[2]
    # the second call reads the cache: no download
    again = sat.fetch_satellite(45.07, 7.69, WINDOW, urlopen=fake, cache_dir=tmp_path)
    assert again.ok and len(calls) == len(s.tiles)


def test_a_failed_download_gives_a_note_not_an_exception(tmp_path):
    def broken(req, timeout=0):
        raise OSError("no network")

    s = sat.fetch_satellite(45.0, 7.0, WINDOW, urlopen=broken, cache_dir=tmp_path)
    assert not s.ok and "could not be downloaded" in s.note

    def html(req, timeout=0):
        return _Resp(b"<html>blocked</html>")

    assert not sat.fetch_satellite(45.0, 7.0, WINDOW, urlopen=html, cache_dir=tmp_path).ok
    assert not sat.fetch_satellite(89.0, 7.0, WINDOW, cache_dir=tmp_path).ok


def test_map_with_satellite_embeds_the_tiles_and_the_credit(tmp_path):
    s = sat.fetch_satellite(45.07, 7.69, WINDOW, urlopen=lambda r, timeout=0: _Resp(_jpeg()),
                            cache_dir=tmp_path)
    pos = [(-300.0, 0.0), (0.0, 100.0), (300.0, 0.0)]
    outline = [(-600, -400), (600, -400), (600, 400), (-600, 400)]
    plain = layout_svg("t", pos, 100.0, [0.95] * 3, outline, 270.0, 0.075)
    aerial = layout_svg("t", pos, 100.0, [0.95] * 3, outline, 270.0, 0.075, satellite=s)
    assert "<image" not in plain
    assert aerial.count("<image") == len(s.tiles)
    assert "data:image/jpeg;base64," in aerial and "Esri" in aerial
    assert re.search(r'<clipPath id="mapclip">', aerial)
    assert "</svg>" in aerial and aerial.count("<svg") == 1
    x_lo, x_hi, y_lo, y_hi = layout_window(pos, 100.0, outline, 270.0)
    assert x_lo < -600 and x_hi > 600 and y_lo < -400 and y_hi > 400


def test_the_picture_never_shows_in_the_legend_strip(tmp_path):
    """Whatever the renderer does with clip-path, white masks keep the legend readable."""
    s = sat.fetch_satellite(45.07, 7.69, WINDOW, urlopen=lambda r, timeout=0: _Resp(_jpeg()),
                            cache_dir=tmp_path)
    svg = layout_svg("t", [(0.0, 0.0)], 100.0, [0.95], None, 270.0, 0.075, satellite=s)
    last_image = svg.rindex("<image")
    legend = svg.index("keeps its energy")
    masks = [m.start() for m in re.finditer(r'fill="white"/>', svg)]
    assert len([m for m in masks if m > last_image]) >= 4 and last_image < legend


def test_the_picture_survives_a_project_file(tmp_path):
    from resize_energy.core import project_file as pf

    s = sat.fetch_satellite(45.07, 7.69, WINDOW, urlopen=lambda r, timeout=0: _Resp(_jpeg()),
                            cache_dir=tmp_path)
    again = sat.Satellite.from_dict(s.to_dict())
    assert again == s and again.covers(45.07, 7.69, WINDOW)
    assert not again.covers(46.0, 7.69, WINDOW)                       # another site
    assert not again.covers(45.07, 7.69, (-9000.0, 9000.0, -700.0, 700.0))   # a wider map
    project = pf.Project("wind", [{"_satellite": {"sat": s.to_dict()}}])
    back = pf.loads(pf.dumps(project))
    assert sat.Satellite.from_dict(back.pages[0]["_satellite"]["sat"]) == s
    import pytest
    with pytest.raises(ValueError):
        sat.Satellite.from_dict({"lat": 1, "lon": 2, "tiles": [{"w": 0}]})
