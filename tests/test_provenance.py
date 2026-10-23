import pytest

pytest.importorskip("PySide6")

from resize_energy.gui.provenance import Row, section_html  # noqa: E402


def test_section_lists_defaults_and_sources():
    rows = [Row("1. Site", "Irradiation", "1,500 kWh/m2", "PVGIS"),
            Row("2. Demand", "Demand", "4,500 kWh", "changed"),
            Row("4. Costs", "Cost per kWp", "1,100 euro", "default")]
    html = section_html(rows)
    assert "Which values to check" in html and "<b>1</b> are still" in html
    assert "PVGIS" in html and "Cost per kWp = 1,100 euro" in html
    assert "Irradiation" not in html.split("Still at the program")[-1]


def test_empty_gives_nothing():
    assert section_html([]) == ""
