"""The energy-flow picture of each technology, from its inputs and design (Qt-free)."""

from __future__ import annotations

from resize_energy.core.battery_design import BatteryDesign, BatteryInputs
from resize_energy.core.biomass_design import BiomassDesign, BiomassInputs
from resize_energy.core.hydrogen_design import HydrogenDesign, HydrogenInputs
from resize_energy.core.pv_design import PVDesign, PVInputs
from resize_energy.core.solar_thermal_design import SolarThermalDesign, SolarThermalInputs
from resize_energy.core.wind_design import WindDesign, WindInputs
from resize_energy.report.flow_art import Flow, Node

Picture = tuple[list[Node], list[Flow]]


def energy(kwh: float) -> str:
    kwh = abs(kwh)
    if kwh >= 1e6:
        return f"{kwh / 1e6:.2f} GWh"
    if kwh >= 1e4:
        return f"{kwh / 1e3:.0f} MWh"
    if kwh >= 1e3:
        return f"{kwh / 1e3:.1f} MWh"
    return f"{kwh:.0f} kWh"


def power(kw: float) -> str:
    return f"{kw / 1000:.2f} MW" if kw >= 1000 else f"{kw:.1f} kW"


def _share(part: float, whole: float) -> float:
    return max(0.0, min(1.0, part / whole)) if whole > 0 else 0.0


def _to_house_and_grid(produced: float, demand: float, src: int) -> tuple[list[Node], list[Flow]]:
    """The fork after the last producing node: used on site and sent to the grid."""
    used = min(produced, demand)
    sent = max(0.0, produced - demand)
    nodes = [Node("house", "Used on site", energy(used),
                  f"{100 * _share(used, demand):.0f} % of the demand", "orange", -1),
             Node("grid", "Sent to the grid", energy(sent),
                  "surplus" if sent > 0 else "none", "grey", 1)]
    flows = [Flow(src, src + 1, max(_share(used, produced), 0.05), "green"),
             Flow(src, src + 2, max(_share(sent, produced), 0.05), "grey", sent <= 0)]
    return nodes, flows


def pv_picture(inp: PVInputs, d: PVDesign) -> Picture:
    nodes = [Node("sun", "Sun on the modules", f"{inp.annual_irradiation_kwh_m2:,.0f}",
                  "kWh/m2 per year", "sun"),
             Node("panels", "Modules", f"{d.dc_power_kwp:.2f} kWp", f"{d.n_modules} modules",
                  "blue"),
             Node("inverter", "Inverter output", energy(d.annual_energy_kwh), "per year", "green")]
    flows = [Flow(0, 1, 1.0, "sun"), Flow(1, 2, 0.9, "blue")]
    tail, tail_flows = _to_house_and_grid(d.annual_energy_kwh, inp.annual_demand_kwh, 2)
    return nodes + tail, flows + tail_flows


def wind_picture(inp: WindInputs, d: WindDesign) -> Picture:
    nodes = [Node("turbine", "Wind at hub height", f"{d.mean_speed_hub_ms:.1f} m/s", "mean speed",
                  "blue"),
             Node("turbine", "Turbines", f"{d.n_turbines} x {inp.turbine.rated_power_kw:,.0f} kW",
                  f"capacity factor {100 * d.capacity_factor_net:.0f} %", "green"),
             Node("inverter", "Yearly energy", energy(d.annual_energy_kwh),
                  f"{power(d.installed_power_kw)} installed", "green")]
    flows = [Flow(0, 1, 1.0, "blue"), Flow(1, 2, 0.9, "green")]
    tail, tail_flows = _to_house_and_grid(d.annual_energy_kwh, inp.annual_demand_kwh, 2)
    return nodes + tail, flows + tail_flows


def battery_picture(inp: BatteryInputs, d: BatteryDesign) -> Picture:
    stored = d.battery_kwh + d.loss_kwh
    nodes = [Node("sun" if inp.use_pv else "turbine", "Production", energy(d.generation_kwh),
                  "per year", "sun"),
             Node("house", "Used at once", energy(d.direct_kwh),
                  f"self-consumption {100 * d.self_consumption:.0f} %", "orange", -1),
             Node("battery", "Through the battery", energy(d.battery_kwh),
                  f"{d.capacity_kwh:.1f} kWh, {d.loss_kwh:,.0f} kWh lost", "green", 0),
             Node("grid", "Sent to the grid", energy(d.export_kwh), "surplus", "grey", 1)]
    total = max(d.generation_kwh, 1.0)
    flows = [Flow(0, 1, max(_share(d.direct_kwh, total), 0.05), "green"),
             Flow(0, 2, max(_share(stored, total), 0.05), "blue"),
             Flow(0, 3, max(_share(d.export_kwh, total), 0.05), "grey", d.export_kwh <= 0)]
    return nodes, flows


def hydrogen_picture(inp: HydrogenInputs, d: HydrogenDesign) -> Picture:
    source = "turbine" if (inp.use_wind and not inp.use_pv) else "sun"
    nodes = [Node(source, "Electricity used", energy(d.electricity_kwh),
                  f"{100 * d.grid_share:.0f} % from the grid", "sun"),
             Node("electrolyser", "Electrolyser", power(d.electrolyser_kw),
                  f"{100 * d.efficiency_lhv:.0f} % efficient (LHV)", "blue"),
             Node("tank", "Storage", f"{d.storage_kg:,.0f} kg", f"{inp.storage_bar:.0f} bar",
                  "green"),
             Node("flame", "Hydrogen", f"{d.hydrogen_kg:,.0f} kg", f"{d.hydrogen_kg_per_day:,.0f} "
                  "kg per day", "orange")]
    flows = [Flow(0, 1, 1.0, "sun"), Flow(1, 2, 0.8, "blue"), Flow(2, 3, 0.8, "green")]
    return nodes, flows


def solar_picture(inp: SolarThermalInputs, d: SolarThermalDesign) -> Picture:
    run = d.run
    nodes = [Node("sun", "Sun on the collectors", f"{inp.irradiation_kwh_m2:,.0f}",
                  "kWh/m2 per year", "sun"),
             Node("collector", "Collectors", f"{d.area_m2:.1f} m2", d.collector.name, "blue"),
             Node("hot_tank", "Hot-water store", f"{d.store_litres:,.0f} L",
                  f"{energy(run.collector_kwh)} collected", "orange")]
    flows = [Flow(0, 1, 1.0, "sun"), Flow(1, 2, 0.9, "blue")]
    cooling = run.cooling_demand_kwh > 0
    nodes.append(Node("tap", "Hot water", energy(run.heat_solar_kwh),
                      f"{100 * run.heat_fraction:.0f} % of the demand", "red", -1 if cooling else None))
    flows.append(Flow(2, 3, max(_share(run.heat_solar_kwh, run.collector_kwh), 0.1), "red"))
    if cooling:
        nodes.append(Node("snow", "Cooling", energy(run.cooling_solar_kwh),
                          f"{100 * run.cooling_fraction:.0f} % of the demand", "blue", 1))
        flows.append(Flow(2, 4, max(_share(run.chiller_heat_kwh, run.collector_kwh), 0.1),
                          "blue"))
    return nodes, flows


def biomass_picture(inp: BiomassInputs, d: BiomassDesign) -> Picture:
    if d.pathway == "biogas":
        nodes = [Node("digester", "Substrate", f"{d.mass_t_per_year:,.0f} t", "per year", "green"),
                 Node("digester", "Digester", f"{d.digester_volume_m3:,.0f} m3",
                      f"{d.biogas_m3_per_year:,.0f} Nm3 biogas", "orange"),
                 Node("engine", "CHP engine", power(d.electric_power_kw), "electric", "blue")]
        flows = [Flow(0, 1, 1.0, "green"), Flow(1, 2, 0.9, "orange")]
        el, heat = d.electricity_net_kwh, d.heat_useful_kwh
        src = 2
    else:
        label = "Boiler" if d.pathway == "boiler" else "ORC unit"
        nodes = [Node("flame", "Fuel", f"{d.mass_t_per_year:,.0f} t", f"{inp.fuel.name}", "green"),
                 Node("engine", label, power(d.thermal_power_kw), "thermal power", "orange")]
        flows = [Flow(0, 1, 1.0, "green")]
        el, heat = d.electricity_net_kwh, d.heat_useful_kwh
        src = 1
    total = max(heat + el, 1.0)
    has_el = el > 0
    nodes.append(Node("flame", "Heat delivered", energy(heat), f"{100 * d.heat_coverage:.0f} % of "
                      "the heat demand" if d.pathway != "biogas" else "to the site", "red",
                      -1 if has_el else None))
    flows.append(Flow(src, src + 1, max(_share(heat, total), 0.1), "red"))
    if has_el:
        nodes.append(Node("grid", "Electricity", energy(el), "net of own use",
                          "blue", 1))
        flows.append(Flow(src, src + 2, max(_share(el, total), 0.1), "blue"))
    return nodes, flows
