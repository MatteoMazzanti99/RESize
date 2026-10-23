from dataclasses import replace

import pytest

from resize_energy.core import biomass as bm
from resize_energy.core.biomass_design import (
    BiomassInputs,
    default_efficiencies,
    size_biomass_plant,
)
from resize_energy.core.fuel_library import (
    SOLID_FUELS,
    SUBSTRATES,
    fuel_by_name,
    substrate_by_name,
)
from resize_energy.report.html_report import build_biomass_report
from resize_energy.tutor.checker_biomass import check_biomass_design
from resize_energy.tutor.context_biomass import build_biomass_context
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.explanations_biomass import BIOMASS_TOPIC_ORDER, topics_for
from resize_energy.tutor.worked_biomass import biomass_worked_example


def case(pathway="boiler", **kw):
    th, el = default_efficiencies(pathway)
    inp = replace(BiomassInputs(pathway=pathway, eta_th=th, eta_el=el), **kw)
    return inp, size_biomass_plant(inp)


def codes(findings, severity=None):
    return {f.code for f in findings if severity is None or f.severity == severity}


def test_lhv_as_received_hand_values():
    # chips: 5.15 x 0.70 - 0.6786 x 0.30 = 3.4014 kWh/kg
    assert bm.lhv_as_received(5.15, 0.30) == pytest.approx(3.4014, abs=1e-4)
    assert bm.lhv_as_received(5.15, 0.0) == pytest.approx(5.15)
    assert bm.lhv_as_received(5.15, 0.5) < bm.lhv_as_received(5.15, 0.3)
    with pytest.raises(ValueError):
        bm.lhv_as_received(5.15, 1.0)


def test_load_duration_coverage_properties():
    for lf in (0.1, 0.3, 0.7, 1.0):
        assert bm.covered_fraction(0, lf) == pytest.approx(0)
        assert bm.covered_fraction(1, lf) == pytest.approx(1)
        values = [bm.covered_fraction(x / 20, lf) for x in range(21)]
        assert values == sorted(values)
        assert bm.covered_fraction(0.5, lf) >= 0.5 - 1e-12  # a part-size plant covers more
    assert bm.covered_fraction(0.4, 1.0) == pytest.approx(0.4)  # flat load
    # n = 1/0.25 - 1 = 3; f(0.5) = 4 x 0.5 - 3 x 0.5^(4/3) = 2 - 3 x 0.39685 = 0.80945
    assert bm.covered_fraction(0.5, 0.25) == pytest.approx(0.80945, abs=1e-4)


def test_power_ratio_inverts_the_coverage():
    for lf in (0.15, 0.3, 0.6):
        for c in (0.5, 0.85, 0.95):
            x = bm.power_ratio_for_coverage(c, lf)
            assert bm.covered_fraction(x, lf) == pytest.approx(c, abs=1e-9)
    assert bm.power_ratio_for_coverage(1.0, 0.3) == 1.0


def test_boiler_hand_calculation():
    inp, d = case()
    assert d.load_factor == pytest.approx(2_000_000 / (800 * 8760))
    assert d.heat_useful_kwh == pytest.approx(1_700_000)
    assert d.fuel_energy_kwh == pytest.approx(2_000_000)
    assert d.mass_t_per_year == pytest.approx(2_000_000 / 3.40142 / 1000, rel=1e-4)
    assert d.thermal_power_kw == pytest.approx(d.power_ratio * 800)
    assert d.electric_power_kw == 0 and d.electricity_net_kwh == 0
    # CO2: 1.7 GWh / 0.9 x 0.202 - 2 GWh x 0.02 = 381.56 - 40 = 341.56 t
    assert d.co2_avoided_t_per_year == pytest.approx(341.56, abs=0.01)
    assert d.ash_t_per_year == pytest.approx(d.mass_t_per_year * 0.7 * 0.01)
    assert d.deliveries_per_year == bm.deliveries_per_year(d.mass_t_per_year, 30, 250)


def test_orc_power_follows_the_efficiency_ratio():
    inp, d = case("orc")
    assert d.electric_power_kw == pytest.approx(d.thermal_power_kw * 0.15 / 0.70)
    assert d.electricity_net_kwh == pytest.approx(d.heat_useful_kwh * 0.15 / 0.70)
    assert d.electricity_coverage == pytest.approx(d.electricity_net_kwh / 1_500_000)


def test_biogas_hand_calculation():
    inp, d = case("biogas")
    gross = 0.85 * 1_500_000 / 0.92
    assert d.electricity_gross_kwh == pytest.approx(gross)
    assert d.ch4_m3_per_year == pytest.approx(gross / 0.38 / 9.97, rel=1e-9)
    assert d.mass_t_per_year == pytest.approx(d.ch4_m3_per_year / 59.5, rel=1e-9)
    assert d.working_volume_m3 == pytest.approx(d.mass_t_per_year / 365 * 45)
    assert d.digester_volume_m3 == pytest.approx(d.working_volume_m3 / 0.9)
    assert d.heat_total_kwh == pytest.approx(gross * 0.45 / 0.38)
    assert d.heat_useful_kwh == pytest.approx(d.heat_total_kwh * 0.75)
    assert d.electric_power_kw == pytest.approx(gross / 8000)
    assert d.substrate_mass_a_t + d.substrate_mass_b_t == pytest.approx(d.mass_t_per_year)
    assert d.crop_hectares == pytest.approx(d.substrate_mass_a_t / 45)  # slurry needs no land
    assert 0 < d.digestate_t_per_year < d.mass_t_per_year
    assert 0.4 < d.ch4_fraction < 0.7


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        case(peak_heat_kw=100)  # load factor above 1
    with pytest.raises(ValueError):
        case(coverage=0)
    with pytest.raises(ValueError):
        case("biogas", annual_electricity_demand_kwh=0)
    with pytest.raises(ValueError):
        case("orc", eta_el=0.0)
    with pytest.raises(ValueError):
        case("biogas", share_b=1.5)


def test_library_is_consistent():
    assert len(SOLID_FUELS) >= 3 and len(SUBSTRATES) >= 4
    assert fuel_by_name(SOLID_FUELS[1].name) is SOLID_FUELS[1]
    assert substrate_by_name(SUBSTRATES[2].name).crop_yield_t_per_ha > 0
    with pytest.raises(KeyError):
        fuel_by_name("nothing")
    for sub in SUBSTRATES:
        assert 0 < sub.ch4_fraction < 1 and 0 < sub.vs_fresh < sub.ts <= 1
    pellets = next(f for f in SOLID_FUELS if "pellet" in f.name.lower())
    assert 4.5 < bm.lhv_as_received(pellets.lhv_dry_kwh_per_kg, pellets.moisture_wb) < 5.0


def test_tutor_pieces_for_every_pathway():
    assert set(topics_for("boiler")) | set(topics_for("biogas")) == set(BIOMASS_TOPIC_ORDER)
    for pathway in ("boiler", "orc", "biogas"):
        inp, d = case(pathway)
        findings = check_biomass_design(inp, d)
        assert all(f.explanation_key in EXPLANATIONS for f in findings if f.explanation_key)
        for key in topics_for(pathway):
            entry = EXPLANATIONS[key]
            assert entry["title"] and entry["formula"] and entry["why"] and entry["assumptions"]
            text = biomass_worked_example(key, inp, d)
            assert text and any(ch.isdigit() for ch in text), (pathway, key)
        assert "RESULTS" in build_biomass_context(inp, d, findings)
        for theme in ("light", "screen"):
            html = build_biomass_report(inp, d, findings, theme=theme)
            assert "Method and formulas" in html and "Design checks" in html
    assert biomass_worked_example("nope", *case()) is None


def test_checks_catch_the_main_problems():
    inp, d = case(fuel=replace(SOLID_FUELS[0], moisture_wb=0.55))
    assert "moisture_high" in codes(check_biomass_design(inp, d), "warning")
    inp, d = case(coverage=1.0, storage_days=1)
    found = codes(check_biomass_design(inp, d), "warning")
    assert {"coverage_high", "storage_short"} <= found
    inp, d = case("biogas", hrt_days=15)
    assert "hrt_low" in codes(check_biomass_design(inp, d), "error")
    inp, d = case("biogas", substrate_b=substrate_by_name("Maize silage"), share_b=0.9,
                  hrt_days=30)
    assert {"olr_high"} & codes(check_biomass_design(inp, d), "error")
    inp, d = case("biogas", operating_hours=5000)
    assert "chp_hours" in codes(check_biomass_design(inp, d), "warning")


def test_substrate_yields_are_plausible_per_kg_of_volatile_solids():
    # Buswell: carbohydrates give at most 0.373 Nm3 CH4 per kg VS, proteins 0.50, fats 1.0.
    # Real substrates sit at roughly 0.15-0.45; values outside would be a typing error.
    for sub in SUBSTRATES:
        per_kg_vs = sub.ch4_m3_per_t / (sub.vs_fresh * 1000.0)
        assert 0.15 < per_kg_vs < 0.45, (sub.name, per_kg_vs)
