from resize_energy.core.countries import BOILER_EFFICIENCY, COUNTRIES, get_country


def test_codes_and_names_are_unique():
    assert len({c.code for c in COUNTRIES}) == len(COUNTRIES) >= 15
    assert len({c.name for c in COUNTRIES}) == len(COUNTRIES)


def test_values_are_plausible():
    for c in COUNTRIES:
        assert 0.03 < c.electricity_eur_kwh < 0.6, c.name
        assert 0 < c.export_eur_kwh < c.electricity_eur_kwh, c.name
        assert 0.01 < c.gas_eur_kwh < 0.3, c.name
        assert 20 < c.grid_g_co2_kwh < 900, c.name


def test_conversions_and_note():
    de = get_country("DE")
    assert de.heat_eur_kwh == de.gas_eur_kwh / BOILER_EFFICIENCY
    assert de.grid_kg_co2_kwh == de.grid_g_co2_kwh / 1000
    assert "Germany" in de.note and "Rough estimates" in de.note


def test_italy_and_france_differ_on_carbon():
    assert get_country("FR").grid_g_co2_kwh < get_country("IT").grid_g_co2_kwh / 4
