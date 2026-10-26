"""Wind rose: sectors, statistics, persistence and the (mocked) download."""

import json
import math

import pytest

from resize_energy.core import wind_rose as wr
from resize_energy.core.nasa_power import NasaPowerError


def test_sectors_are_centred_on_multiples_of_30():
    assert wr.sector_of(0) == 0 and wr.sector_of(14.9) == 0 and wr.sector_of(15.1) == 1
    assert wr.sector_of(359) == 0 and wr.sector_of(270) == 9 and wr.sector_of(-30) == 11


def test_rose_from_series_by_hand():
    speeds = [4.0] * 3000 + [8.0] * 3000 + [6.0] * 3000
    dirs = [0.0] * 3000 + [270.0] * 3000 + [90.0] * 3000
    rose = wr.rose_from_series(speeds, dirs)
    assert rose.frequency[0] == pytest.approx(1 / 3)
    assert rose.frequency[9] == pytest.approx(1 / 3)
    assert rose.frequency[3] == pytest.approx(1 / 3)
    assert rose.mean_speed_ms == pytest.approx(6.0)
    assert rose.speed_factor[9] == pytest.approx(8 / 6)
    assert rose.speed_factor[0] == pytest.approx(4 / 6)
    assert rose.speed_factor[5] == 0.0              # no hours from there
    # energy share: 8^3 dominates
    share = rose.energy_share()
    assert share[9] == max(share) and sum(share) == pytest.approx(1.0)
    assert 250 < rose.prevailing_deg() < 290


def test_prevailing_direction_wraps_around_north():
    w = [0.0] * 12
    w[11], w[0], w[1] = 1.0, 1.0, 1.0
    assert wr.prevailing_direction(w) == pytest.approx(0.0, abs=1e-6) or \
        wr.prevailing_direction(w) == pytest.approx(360.0, abs=1e-6)


def test_too_few_hours_or_calm_is_refused():
    with pytest.raises(ValueError):
        wr.rose_from_series([5.0] * 100, [0.0] * 100)
    with pytest.raises(ValueError):
        wr.rose_from_series([0.0] * 6000, [0.0] * 6000)
    with pytest.raises(ValueError):
        wr.rose_from_series([5.0] * 6000, [0.0] * 5999)


def test_rose_survives_a_round_trip():
    rose = wr.rose_from_series([5.0 + (i % 5) for i in range(8000)],
                               [float(i % 360) for i in range(8000)], (2019,))
    back = wr.WindRose.from_dict(json.loads(json.dumps(rose.to_dict())))
    assert back.sectors == rose.sectors and back.hours == rose.hours
    assert back.frequency == pytest.approx(rose.frequency, abs=1e-5)
    assert sum(back.frequency) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        wr.WindRose.from_dict({"frequency": [1.0]})


def test_uniform_rose():
    r = wr.uniform_rose(7.0)
    assert r.frequency == (1 / 12,) * 12 and r.speed_factor == (1.0,) * 12


def _answer(n=8760, year=2019, missing=0):
    keys = [f"{year}{h:06d}" for h in range(n)]
    speed = {k: 6.0 + 2.0 * math.sin(i) for i, k in enumerate(keys)}
    direction = {k: (270.0 + 40.0 * math.cos(i / 7.0)) % 360 for i, k in enumerate(keys)}
    for k in list(speed)[:missing]:
        speed[k] = -999.0
    return {"properties": {"parameter": {"WS50M": speed, "WD50M": direction}}}


class _Resp:
    def __init__(self, body: bytes):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_parse_drops_missing_hours():
    v, d = wr.parse_hourly_pairs(_answer(n=2000, missing=500))
    assert len(v) == len(d) == 1500
    with pytest.raises(NasaPowerError):
        wr.parse_hourly_pairs({"properties": {"parameter": {"WS50M": {}}}})


def test_fetch_uses_every_year_and_finds_the_prevailing_wind():
    asked = []

    def fake(request, timeout):
        asked.append(request.full_url)
        return _Resp(json.dumps(_answer(n=4000)).encode())

    rose = wr.fetch_wind_rose(45.0, 7.0, years=(2019, 2020), urlopen=fake)
    assert len(asked) == 2 and "WD50M" in asked[0] and "20200101" in asked[1]
    assert rose.years == (2019, 2020) and rose.hours == 8000
    assert 250 < rose.prevailing_deg() < 290


def test_fetch_survives_one_bad_year_but_not_all():
    calls = {"n": 0}

    def flaky(request, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(b"<html>maintenance</html>")
        return _Resp(json.dumps(_answer(n=6000)).encode())

    rose = wr.fetch_wind_rose(45.0, 7.0, years=(2019, 2020), urlopen=flaky)
    assert rose.years == (2020,)

    def broken(request, timeout):
        raise OSError("offline")

    with pytest.raises(NasaPowerError):
        wr.fetch_wind_rose(45.0, 7.0, urlopen=broken)
    with pytest.raises(ValueError):
        wr.build_url(100.0, 0.0, 2019)
