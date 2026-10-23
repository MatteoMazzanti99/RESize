import math
import xml.etree.ElementTree as ET

import pytest

from resize_energy.core.battery_design import (
    BatteryInputs,
    BatteryProfiles,
    size_battery,
)
from resize_energy.core.biomass_design import (
    BiomassInputs,
    default_efficiencies,
    size_biomass_plant,
)
from resize_energy.core.hydrogen_design import (
    HydrogenInputs,
    HydrogenProfiles,
    size_hydrogen_plant,
)
from resize_energy.core.pv_design import PVInputs, size_pv_system
from resize_energy.core.solar_thermal_design import SolarThermalInputs, size_solar_thermal
from resize_energy.core.wind_design import WindInputs, size_wind_plant
from resize_energy.report import flow_pictures as fp
from resize_energy.report.flow_art import THEMES, Flow, Node, flow_svg, picture_size

SUN = tuple(max(0.0, math.sin(math.pi * ((t % 24) - 6) / 12)) * 0.8 for t in range(8760))


def _pictures():
    out = {}
    i = PVInputs(4500, 1500)
    out["pv"] = fp.pv_picture(i, size_pv_system(i))
    i = WindInputs(900000, 6.5)
    out["wind"] = fp.wind_picture(i, size_wind_plant(i))
    i, p = BatteryInputs(), BatteryProfiles(pv_unit=SUN)
    out["battery"] = fp.battery_picture(i, size_battery(i, p))
    i, p = HydrogenInputs(use_grid=True), HydrogenProfiles(pv_unit=SUN)
    out["hydrogen"] = fp.hydrogen_picture(i, size_hydrogen_plant(i, p))
    for cooling in (0.0, 3000.0):
        i = SolarThermalInputs(cooling_kwh_per_year=cooling)
        out[f"solar{cooling:.0f}"] = fp.solar_picture(i, size_solar_thermal(i))
    for pathway in ("boiler", "orc", "biogas"):
        th, el = default_efficiencies(pathway)
        i = BiomassInputs(pathway=pathway, eta_th=th, eta_el=el)
        out[pathway] = fp.biomass_picture(i, size_biomass_plant(i))
    return out


PICTURES = _pictures()


@pytest.mark.parametrize("name", sorted(PICTURES))
@pytest.mark.parametrize("theme", sorted(THEMES))
def test_every_picture_is_valid_svg(name, theme):
    nodes, flows = PICTURES[name]
    svg = flow_svg(nodes, flows, 0.4, theme)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert "nan" not in svg.lower() and "inf" not in svg.lower()
    for node in nodes:
        assert node.value in svg or node.value.replace("&", "&amp;") in svg
    w, h = picture_size(nodes)
    assert (root.get("width"), root.get("height")) == (str(w), str(h))


def test_the_dots_move_with_the_phase():
    nodes, flows = PICTURES["pv"]
    assert flow_svg(nodes, flows, 0.0) != flow_svg(nodes, flows, 0.5)
    assert flow_svg(nodes, flows, 0.25) == flow_svg(nodes, flows, 1.25)


def test_fork_gives_a_taller_picture():
    assert picture_size(PICTURES["pv"][0])[1] > picture_size(PICTURES["hydrogen"][0])[1]


def test_energy_formatting():
    assert fp.energy(820) == "820 kWh"
    assert fp.energy(4400) == "4.4 MWh"
    assert fp.energy(44000) == "44 MWh"
    assert fp.energy(2.5e6) == "2.50 GWh"
    assert fp.power(2000) == "2.00 MW"


def test_flows_point_to_existing_nodes():
    for nodes, flows in PICTURES.values():
        for f in flows:
            assert 0 <= f.src < len(nodes) and 0 <= f.dst < len(nodes) and f.src != f.dst
        assert all(isinstance(n, Node) for n in nodes)
        assert all(isinstance(f, Flow) for f in flows)
