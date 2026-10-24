"""The default costs written in the sources table are the ones the program really uses."""

import pytest

from resize_energy.core.battery_design import BatteryInputs
from resize_energy.core.comparison import CostAssumptions
from resize_energy.core.hydrogen_design import HydrogenInputs
from resize_energy.core.plant_economics import EconomicInputs
from resize_energy.core.solar_thermal import COLLECTORS
from resize_energy.core.solar_thermal_design import SolarThermalInputs
from resize_energy.tutor.bibliography import REFS
from resize_energy.tutor.cost_sources import COSTS, TOPIC_COSTS, costs_html
from resize_energy.tutor.explanations import EXPLANATIONS


def _code_values():
    b, c, h, s = BatteryInputs(), CostAssumptions(), HydrogenInputs(), SolarThermalInputs()
    return {
        "pv_capex": {c.pv_capex_eur_per_kwp, h.pv_capex_per_kwp, 1100.0},   # 1,100: the PV cost step
        "pv_om": {c.pv_om_eur_per_kwp_year, h.pv_om_per_kwp, 15.0},
        "pv_life": {c.pv_lifetime_years},
        "wind_capex": {c.wind_capex_eur_per_kw, h.wind_capex_per_kw, 1700.0},  # 1,700: the wind cost step
        "wind_om": {c.wind_om_eur_per_kw_year, h.wind_om_per_kw},
        "wind_life": {EconomicInputs().life_years},
        "bio_capex": {c.bio_capex_eur_per_kwe},
        "bio_om": {c.bio_om_eur_per_kwe_year},
        "batt_kwh": {b.capex_per_kwh},
        "batt_kw": {b.capex_per_kw},
        "batt_om": {b.om_fraction * 100},
        "batt_life": {b.calendar_life_years},
        "h2_capex": {h.electrolyser_capex_per_kw, c.h2_electrolyser_capex_eur_per_kw},
        "h2_stack_hours": {h.stack_hours},
        "h2_stack_share": {h.stack_cost_fraction},
        "h2_kwh": {h.kwh_per_kg_stack},
        "h2_om": {h.electrolyser_om_fraction},
        "h2_storage": {h.storage_capex_per_kg},
        "solar_flat": {COLLECTORS["flat"].cost_per_m2},
        "solar_other": {COLLECTORS["tube"].cost_per_m2, COLLECTORS["unglazed"].cost_per_m2,
                        s.store_cost_per_litre, s.fixed_cost, s.chiller_cost_per_kw},
    }


@pytest.mark.parametrize("key", sorted(COSTS))
def test_the_defaults_in_the_table_are_the_ones_in_the_program(key):
    in_code = _code_values()[key]
    for value in COSTS[key].defaults:
        assert any(abs(value - x) < 1e-9 for x in in_code), (key, value, in_code)


def test_every_source_exists_and_every_verdict_is_known():
    for c in COSTS.values():
        assert c.verdict in ("within", "below", "above", "none")
        for ref, _where in c.refs:
            assert ref in REFS
        if c.verdict != "none":
            assert c.refs, f"{c.key}: a verdict without a source"


def test_costs_appear_with_their_topics():
    for topic, names in TOPIC_COSTS.items():
        assert topic in EXPLANATIONS and all(n in COSTS for n in names)
        assert "where they come from" in costs_html(topic)
    assert costs_html("pv.irradiation") == ""
