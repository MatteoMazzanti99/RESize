import pytest

from resize_energy.core import geo
from resize_energy.core.countries import COUNTRIES

CITIES = {
    "IT": [(45.07, 7.69), (41.9, 12.5), (37.5, 15.1), (40.85, 14.27), (39.2, 9.1), (45.65, 13.78),
           (45.81, 9.08), (35.5, 12.6), (46.5, 13.58)],
    "FR": [(48.85, 2.35), (43.3, 5.4), (45.76, 4.84), (43.7, 7.26), (48.58, 7.75), (50.63, 3.06),
           (42.7, 9.45), (43.6, 1.44)],
    "DE": [(52.52, 13.4), (48.14, 11.58), (50.11, 8.68), (50.78, 6.08)],
    "ES": [(40.4, -3.7), (41.39, 2.17), (37.39, -5.98), (28.1, -15.4), (39.57, 2.65)],
    "GB": [(51.5, -0.12), (55.95, -3.19), (54.6, -5.93)],
    "US": [(40.7, -74.0), (34.05, -118.2), (64.8, -147.7), (21.3, -157.8)],
    "AU": [(-33.9, 151.2), (-37.8, 145.0)],
    "JP": [(35.7, 139.7)], "CN": [(39.9, 116.4)], "IN": [(28.6, 77.2)], "BR": [(-23.5, -46.6)],
    "CA": [(45.4, -75.7), (43.65, -79.4)], "MX": [(19.4, -99.1)],
    "NL": [(52.37, 4.9), (50.85, 5.69)], "PL": [(52.2, 21.0)],
    "AT": [(48.21, 16.37), (47.07, 15.44)], "BE": [(50.85, 4.35)], "CH": [(47.38, 8.54), (46.95, 7.45)],
    "SE": [(59.33, 18.07)], "NO": [(59.91, 10.75)], "FI": [(60.17, 24.94)], "DK": [(55.68, 12.57)],
    "PT": [(38.72, -9.14)], "IE": [(53.35, -6.26)], "GR": [(37.98, 23.73)], "CZ": [(50.08, 14.43)],
    "HU": [(47.5, 19.04)], "RO": [(44.43, 26.1)], "BG": [(42.7, 23.32)], "HR": [(45.81, 15.98)],
    "SI": [(46.06, 14.51)], "SK": [(48.15, 17.11)], "LU": [(49.61, 6.13)], "EE": [(59.44, 24.75)],
    "LV": [(56.95, 24.1)], "LT": [(54.69, 25.28)], "MT": [(35.9, 14.51)], "CY": [(34.68, 33.04)],
    "IS": [(64.15, -21.94)], "RS": [(44.8, 20.46)], "UA": [(50.45, 30.52)], "AR": [(-34.6, -58.4)],
    "ZA": [(-33.9, 18.4)], "KR": [(37.6, 127.0)], "TR": [(41.0, 29.0), (39.9, 32.9)],
}


def test_every_preset_country_has_borders():
    for c in COUNTRIES:
        assert geo.country_name(c.code) != c.code or c.code in geo._load(), c.code
        assert c.code in geo._load()


@pytest.mark.parametrize("code,point", [(c, p) for c, pts in CITIES.items() for p in pts])
def test_cities_are_in_their_country(code, point):
    assert geo.in_country(code, *point) is True


def test_neighbours_across_a_border_are_told_apart():
    # a few kilometres either side of a border: Como/Lugano, Aachen/Maastricht, Kehl/Strasbourg
    assert geo.country_at(45.81, 9.085) == "IT" and geo.country_at(46.005, 8.951) == "CH"
    assert geo.country_at(50.78, 6.08) == "DE" and geo.country_at(50.85, 5.69) == "NL"
    assert geo.country_at(48.58, 7.75) == "FR" and geo.country_at(48.575, 7.82) == "DE"
    assert geo.country_at(46.61, 13.85) == "AT" and geo.country_at(46.5, 13.7) == "SI"


def test_distance_to_the_border():
    assert geo.distance_to_country_km("CH", 45.84, 9.03, 5.0) < 2.5     # right at Chiasso
    assert geo.distance_to_country_km("CH", 52.52, 13.4, 5.0) == float("inf")


def test_clear_and_close_mismatches_are_caught():
    assert geo.in_country("AU", 45.07, 7.69) is False
    assert geo.in_country("FR", 45.07, 7.69) is False        # Turin is not in France
    assert geo.in_country("IT", 46.0, 8.95) is False         # Lugano
    assert geo.in_country("DE", 50.85, 5.69) is False        # Maastricht
    assert geo.in_country("ES", 43.6, 1.44) is False         # Toulouse
    assert geo.in_country("US", 43.65, -79.4) is False       # Toronto


def test_coast_and_sea():
    assert geo.in_country("IT", 43.79, 7.60) is True         # Ventimiglia, on the coast
    assert geo.in_country("FR", 43.775, 7.5) is True         # Menton
    assert geo.in_country("IT", 44.25, 8.9) is True          # 10 km off Genoa (offshore plant)
    assert geo.in_country("IT", 0.0, -30.0) is False         # open Atlantic
    assert geo.country_near(0.0, -30.0) is None


def test_names_and_unknown_codes():
    assert geo.country_name("CH") == "Switzerland"
    assert geo.in_country("XX", 45.0, 7.0) is None
