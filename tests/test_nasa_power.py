import io
import json
import urllib.error

import pytest

from resize_energy.core import nasa_power as np_


def sample(speed=5.9, temp=12.3, elev=245.0):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [7.69, 45.07, elev]},
        "properties": {"parameter": {"WS50M": {"JAN": 5.0, "ANN": speed},
                                     "T2M": {"JAN": 1.0, "ANN": temp}}},
    }


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def opener(payload: bytes):
    def _open(request, timeout=0):
        return FakeResponse(payload)
    return _open


def test_url_contains_coordinates_and_parameters():
    url = np_.build_url(45.07, 7.69)
    assert "latitude=45.0700" in url and "longitude=7.6900" in url
    assert "WS50M" in url and "climatology" in url


def test_parse_ok():
    c = np_.parse_climatology(sample())
    assert (c.mean_speed_50m_ms, c.mean_temperature_c, c.elevation_m) == (5.9, 12.3, 245.0)


def test_parse_missing_value_and_optional_fields():
    with pytest.raises(np_.NasaPowerError):
        np_.parse_climatology(sample(speed=-999))
    with pytest.raises(np_.NasaPowerError):
        np_.parse_climatology({"properties": {}})
    c = np_.parse_climatology(sample(temp=-999))
    assert c.mean_temperature_c is None


def test_fetch_with_fake_network():
    c = np_.fetch_wind_climate(45.07, 7.69, urlopen=opener(json.dumps(sample()).encode()))
    assert c.mean_speed_50m_ms == 5.9


def test_fetch_errors_are_readable():
    def boom(request, timeout=0):
        raise urllib.error.URLError("no network")
    with pytest.raises(np_.NasaPowerError) as e:
        np_.fetch_wind_climate(45, 7, urlopen=boom)
    assert "Could not reach" in str(e.value)
    with pytest.raises(np_.NasaPowerError) as e:
        np_.fetch_wind_climate(45, 7, urlopen=opener(b"<html>nope</html>"))
    assert "did not return JSON" in str(e.value)
    with pytest.raises(ValueError):
        np_.build_url(120, 0)
