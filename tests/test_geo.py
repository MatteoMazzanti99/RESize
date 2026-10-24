import pytest

from resize_energy.core import geo
from resize_energy.core.countries import COUNTRIES

CITIES = {
    "IT": [(45.07, 7.69), (41.9, 12.5), (37.5, 15.1), (40.85, 14.27), (39.2, 9.1), (45.65, 13.78)],
    "FR": [(48.85, 2.35), (43.3, 5.4), (45.76, 4.84), (43.7, 7.26), (48.58, 7.75), (50.63, 3.06)],
    "DE": [(52.52, 13.4), (48.14, 11.58), (50.11, 8.68)],
    "ES": [(40.4, -3.7), (41.39, 2.17), (37.39, -5.98), (28.1, -15.4), (39.57, 2.65)],
    "GB": [(51.5, -0.12), (55.95, -3.19), (54.6, -5.93)],
    "US": [(40.7, -74.0), (34.05, -118.2), (64.8, -147.7), (21.3, -157.8)],
    "AU": [(-33.9, 151.2), (-37.8, 145.0)],
    "JP": [(35.7, 139.7)], "CN": [(39.9, 116.4)], "IN": [(28.6, 77.2)], "BR": [(-23.5, -46.6)],
    "CA": [(45.4, -75.7)], "MX": [(19.4, -99.1)], "NL": [(52.37, 4.9)], "PL": [(52.2, 21.0)],
    "ZA": [(-33.9, 18.4)], "KR": [(37.6, 127.0)], "TR": [(41.0, 29.0), (39.9, 32.9)],
}


def test_every_preset_country_has_boxes():
    assert {c.code for c in COUNTRIES} == set(geo.BOXES)


@pytest.mark.parametrize("code,point", [(c, p) for c, pts in CITIES.items() for p in pts])
def test_cities_are_in_their_country(code, point):
    assert geo.in_country(code, *point) is True


def test_clear_mismatches_are_caught():
    assert geo.in_country("AU", 45.07, 7.69) is False
    assert geo.in_country("US", 45.07, 7.69) is False
    assert geo.in_country("IT", 40.4, -3.7) is False      # Madrid
    assert geo.in_country("FR", 45.07, 7.69) is False      # Turin is not in France
    assert geo.in_country("ES", 43.6, 1.44) is False       # Toulouse
    assert geo.in_country("JP", 52.52, 13.4) is False


def test_countries_at():
    assert "IT" in geo.countries_at(45.07, 7.69)
    assert geo.countries_at(-33.9, 151.2) == ["AU"]
    assert geo.countries_at(0.0, -30.0) == []              # open sea
