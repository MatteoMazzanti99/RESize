"""Chart descriptions for the results pages and the PDF reports (no Qt, easy to test).

Each ``*_charts`` function returns an ordered ``{name: ChartSpec}``. The reports refer to a
chart as ``<img src="chart:NAME">`` and the window draws it with :mod:`gui.chart_render`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from resize_energy.core import economics as eco
from resize_energy.core import geothermal as _geo
from resize_energy.core import wind
from resize_energy.core.battery_design import BatteryDesign, BatteryInputs
from resize_energy.core.biomass_design import BiomassDesign, BiomassInputs
from resize_energy.core.comparison import ComparisonInputs, ComparisonResult
from resize_energy.core.geothermal_design import GeothermalDesign, GeothermalInputs
from resize_energy.core.hydro_design import HydroDesign, HydroInputs, exceedance_sweep
from resize_energy.core.hydrogen_design import HydrogenDesign, HydrogenInputs
from resize_energy.core.plant_economics import Economics
from resize_energy.core.pv_design import PVDesign, PVInputs
from resize_energy.core.pv_extra import battery_view
from resize_energy.core.sensitivity import Sensitivity
from resize_energy.core.solar_thermal import CHILLERS as SOLAR_CHILLERS
from resize_energy.core.solar_thermal import COLLECTORS as SOLAR_COLLECTORS
from resize_energy.core.solar_thermal import collector_efficiency as solar_eff
from resize_energy.core.solar_thermal_design import SolarThermalDesign, SolarThermalInputs
from resize_energy.core.wind_design import WindDesign, WindInputs

GREEN, BLUE, AMBER, PURPLE = "#0A7452", "#1F5FBF", "#C77700", "#7B3FB8"
GREY, RED, TEAL, LIGHT = "#7C8AA0", "#B3261E", "#0E8C9B", "#9CC9B8"
TECH_COLORS = {"pv": GREEN, "wind": BLUE, "biomass": AMBER, "hydrogen": PURPLE, "hydro": TEAL,
               "geothermal": RED}
MONTHS = ("J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D")


@dataclass(frozen=True)
class Series:
    name: str
    values: tuple[float, ...]
    color: str = GREEN
    x: tuple[float, ...] | None = None          # lines: x values (default 0, 1, 2, ...)
    colors: tuple[str, ...] | None = None       # bars: one colour per bar
    fill: bool = False                          # lines: shade under the line


@dataclass(frozen=True)
class ChartSpec:
    kind: str                                   # "bars" "hbars" "stack" "lines"
    title: str
    categories: tuple[str, ...] = ()
    series: tuple[Series, ...] = ()
    x_label: str = ""
    y_label: str = ""
    caption: str = ""                           # one plain sentence under the chart
    vlines: tuple[tuple[float, str], ...] = ()  # (value on the value axis, label)
    hlines: tuple[tuple[float, str], ...] = ()  # lines charts only
    decimals: int = 0
    width: int = 460
    height: int = 270


def nice_ticks(lo: float, hi: float, target: int = 5) -> list[float]:
    """Round tick values covering [lo, hi] (about ``target`` of them)."""
    if not math.isfinite(lo) or not math.isfinite(hi):
        return [0.0, 1.0]
    if hi <= lo:
        hi = lo + 1.0
    raw = (hi - lo) / max(1, target)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    first = math.floor(lo / step) * step
    out, v = [], first
    while v < hi + step * 0.999:
        out.append(round(v, 10))
        v += step
        if len(out) > 40:
            break
    return out


def unit_for(values: list[float], base: str = "kWh") -> tuple[float, str]:
    """Divide big energies so the axis reads 12.3 MWh instead of 12,300,000 kWh."""
    top = max((abs(v) for v in values if math.isfinite(v)), default=0.0)
    if top >= 5e6:
        return 1e6, "G" + base[1:] if base.startswith("k") else base
    if top >= 5e3:
        return 1e3, "M" + base[1:] if base.startswith("k") else base
    return 1.0, base


def _scaled(values: list[float], base: str = "kWh") -> tuple[tuple[float, ...], str, int]:
    f, unit = unit_for(values, base)
    out = tuple(v / f for v in values)
    top = max((abs(v) for v in out if math.isfinite(v)), default=0.0)
    return out, unit, (0 if top >= 100 else 1 if top >= 10 else 2)


# --- photovoltaic -----------------------------------------------------------------------
def pv_charts(inp: PVInputs, d: PVDesign) -> dict[str, ChartSpec]:
    vals = [inp.annual_demand_kwh, inp.annual_demand_kwh * inp.coverage, d.annual_energy_kwh]
    scaled, unit, dec = _scaled(vals)
    inv = inp.inverter
    voltages = (d.voc_cold_string_v, d.vmp_hot_string_v, d.vmp_cold_string_v)
    ok = (d.voc_cold_string_v <= inv.vdc_max_v, d.vmp_hot_string_v >= inv.mppt_vmin_v,
          d.vmp_cold_string_v <= inv.mppt_vmax_v)
    extra: dict[str, ChartSpec] = {}
    if d.monthly_kwh:
        months = tuple(float(i) for i in range(1, 13))
        extra["pv_monthly"] = ChartSpec(
            "lines", "Month by month: what the plant makes and what you use", (),
            (Series("PV production [kWh]", d.monthly_kwh, GREEN, x=months, fill=True),
             Series("your demand, flat [kWh]", (inp.annual_demand_kwh / 12,) * 12, GREY,
                    x=months)),
            x_label="Month (1 = January)", y_label="Energy per month [kWh]", height=280,
            caption="Above the grey line the plant makes more than you use; below it you buy "
                    "from the grid. The yearly total hides this swing.")
    if d.feasible and d.dc_power_kwp > 0 and inp.annual_demand_kwh > 0:
        b = battery_view(inp.latitude_deg, inp.annual_demand_kwh, d.dc_power_kwp,
                         d.specific_yield_kwh_per_kwp)
        extra["pv_battery"] = ChartSpec(
            "hbars", f"With and without a {b.capacity_kwh:.1f} kWh battery",
            ("Self-sufficiency, no battery", "Self-sufficiency, with battery",
             "Self-consumption, no battery", "Self-consumption, with battery"),
            (Series("share [%]", (b.self_sufficiency_without * 100, b.self_sufficiency * 100,
                                  b.self_consumption_without * 100, b.self_consumption * 100),
                    colors=(LIGHT, GREEN, LIGHT, GREEN)),),
            x_label="Share [%]", decimals=0,
            caption="Self-sufficiency: share of your consumption not bought. Self-consumption: "
                    "share of the production you use yourself. See the Battery module to size "
                    "it properly.")
    base = {
        "pv_energy": ChartSpec(
            "hbars", "Yearly energy: demand and photovoltaic production",
            ("Your yearly demand", "Share you want from PV", "PV production (expected)"),
            (Series("energy", scaled, colors=(GREY, LIGHT, GREEN)),),
            x_label=f"Energy per year [{unit}]", decimals=dec,
            caption=f"The array produces about {d.annual_energy_kwh:,.0f} kWh a year, "
                    f"{d.achieved_coverage:.0%} of your demand."),
        "pv_voltage": ChartSpec(
            "hbars", "String voltages against the inverter limits",
            ("Voc on the coldest day", "Vmp on the hottest day", "Vmp on the coldest day"),
            (Series("voltage", voltages, colors=tuple(GREEN if o else RED for o in ok)),),
            x_label="Voltage of one string [V]",
            vlines=((inv.vdc_max_v, "Vdc max"), (inv.mppt_vmin_v, "MPPT min"),
                    (inv.mppt_vmax_v, "MPPT max")),
            caption="Green bars respect the inverter. The cold Voc must stay left of 'Vdc max', "
                    "the other two inside the MPPT window."),
    }
    return {**base, **extra} | economics_charts("pv", d.economics)


# --- wind ----------------------------------------------------------------------------------
def _turbine_power(inp: WindInputs, rho: float):
    t = inp.turbine
    if t.power_curve:
        return lambda v: wind.curve_power_kw(v, t.power_curve, t.cut_out_ms, rho)
    return lambda v: wind.generic_power_kw(v, t.rated_power_kw, t.cut_in_ms, t.rated_speed_ms,
                                           t.cut_out_ms, rho)


def _wake_charts(d: WindDesign) -> dict[str, ChartSpec]:
    w = d.wake
    if w is None:
        return {}
    dirs = tuple(f"{i * 30}" for i in range(len(w.sector_efficiency)))
    return {
        "wind_wake_rose": ChartSpec(
            "bars", "Where the wind comes from, and how much the wakes cost from there", dirs,
            (Series("share of the time [%]", tuple(x * 100 for x in w.sector_weights), BLUE),
             Series("wake loss from that direction [%]",
                    tuple((1 - x) * 100 for x in w.sector_efficiency), RED)),
            x_label="Direction the wind comes from [deg, 0 = north, 90 = east]",
            y_label="Percent", decimals=0,
            caption=f"Overall wake loss {d.wake_loss:.1%}. The loss is highest when the wind "
                    "runs along a line of turbines."),
        "wind_wake_turbines": ChartSpec(
            "bars", f"Energy of each turbine against a lone turbine ({d.rows} rows)",
            tuple(str(i + 1) for i in range(len(w.turbine_efficiency))),
            (Series("share [%]", tuple(x * 100 for x in w.turbine_efficiency), GREEN),),
            x_label="Turbine (row by row, first row first)", y_label="Percent of a free turbine",
            decimals=0,
            caption="The first row sees free wind; the others lose a little in every direction "
                    "from which they are behind a turbine."),
    }


def wind_charts(inp: WindInputs, d: WindDesign) -> dict[str, ChartSpec]:
    out = _wind_base_charts(inp, d)
    return out | _wake_charts(d) | economics_charts("wind", d.economics)


def _wind_base_charts(inp: WindInputs, d: WindDesign) -> dict[str, ChartSpec]:
    t = inp.turbine
    power = _turbine_power(inp, d.air_density)
    top = int(math.ceil(t.cut_out_ms)) + 1
    k, a = inp.weibull_k, d.weibull_scale_ms
    hours = [8760.0 * (wind.weibull_cdf(v + 1.0, k, a) - wind.weibull_cdf(float(v), k, a))
             for v in range(top)]
    centre = [power(v + 0.5) for v in range(top)]
    kwh_bins = [h * p / 1000.0 for h, p in zip(hours, centre, strict=True)]  # MWh, gross
    curve_x = tuple(i * 0.5 for i in range(int(2 * (t.cut_out_ms + 1)) + 1))
    cats = tuple(f"{v}" for v in range(top))
    energy, unit, dec = _scaled([inp.annual_demand_kwh, inp.annual_demand_kwh * inp.coverage,
                                 d.annual_energy_kwh])
    return {
        "wind_distribution": ChartSpec(
            "bars", "How often each wind speed blows (at hub height)", cats,
            (Series("hours", tuple(h / 87.6 for h in hours), BLUE),),
            x_label="Wind speed [m/s] (1 m/s classes)", y_label="Share of the year [%]",
            decimals=1,
            caption=f"Mean {d.mean_speed_hub_ms:.1f} m/s at {t.hub_height_m:.0f} m: the Weibull "
                    f"curve with k = {k:.1f} says how many hours each class lasts."),
        "wind_curve": ChartSpec(
            "lines", f"Power curve of the turbine ({t.rated_power_kw:,.0f} kW)", (),
            (Series("power", tuple(power(v) for v in curve_x), BLUE, x=curve_x, fill=True),),
            x_label="Wind speed [m/s]", y_label="Electric power [kW]",
            vlines=((t.cut_in_ms, "cut-in"), (t.rated_speed_ms, "rated"),
                    (t.cut_out_ms, "cut-out")),
            caption="Nothing below cut-in, full power from the rated speed, stopped above "
                    "cut-out."),
        "wind_energy_by_speed": ChartSpec(
            "bars", "Where the energy comes from (one turbine, before losses)", cats,
            (Series("energy", tuple(kwh_bins), GREEN),),
            x_label="Wind speed [m/s]", y_label="Energy per year [MWh]",
            caption="Hours at each speed x power at that speed: the energy is made by the "
                    "middle speeds, not by the rare strong winds."),
        "wind_energy": ChartSpec(
            "hbars", "Yearly energy: demand and wind production",
            ("Your yearly demand", "Share you want from wind", f"Wind: {d.n_turbines} turbine(s)"),
            (Series("energy", energy, colors=(GREY, LIGHT, BLUE)),),
            x_label=f"Energy per year [{unit}]", decimals=dec,
            caption=f"{d.n_turbines} turbine(s) give {d.annual_energy_kwh:,.0f} kWh, "
                    f"{d.achieved_coverage:.0%} of the demand."),
    }


# --- biomass -------------------------------------------------------------------------------
def biomass_charts(inp: BiomassInputs, d: BiomassDesign) -> dict[str, ChartSpec]:
    out: dict[str, ChartSpec] = {}
    if d.pathway == "biogas":
        vals = [d.fuel_energy_kwh, d.electricity_gross_kwh, d.electricity_net_kwh,
                d.heat_total_kwh, d.heat_digester_kwh, d.heat_credited_kwh]
        scaled, unit, dec = _scaled(vals)
        out["bio_flow"] = ChartSpec(
            "hbars", "Where the energy of the biogas goes",
            ("Energy in the biogas (methane)", "Electricity from the engine",
             "Electricity you can use", "Heat from the engine", "Heat to warm the digester",
             "Heat left for you"),
            (Series("energy", scaled, colors=(AMBER, BLUE, GREEN, RED, GREY, TEAL)),),
            x_label=f"Energy per year [{unit}]", decimals=dec, height=300,
            caption="The engine turns part of the biogas into electricity and the rest into "
                    "heat; part of both is used by the plant itself.")
        return out
    lf = max(d.load_factor, 1e-6)
    n = 1.0 / lf - 1.0
    xs = tuple(float(h) for h in range(0, 8761, 120))
    curve = tuple(inp.peak_heat_kw * (1.0 - h / 8760.0) ** n for h in xs)
    out["bio_load"] = ChartSpec(
        "lines", "Heat demand through the year, from the highest hour to the lowest", (),
        (Series("heat demand", curve, AMBER, x=xs, fill=True),),
        x_label="Hours of the year (sorted from the highest demand)", y_label="Heat power [kW]",
        hlines=((d.thermal_power_kw, f"plant {d.thermal_power_kw:,.0f} kW"),),
        caption=f"The plant covers {d.heat_coverage:.0%} of the heat: the part of the curve "
                "below the line. The peaks above it are left to a back-up boiler.")
    vals = [inp.annual_heat_demand_kwh, d.heat_useful_kwh]
    labels = ["Heat demand", "Heat from the plant"]
    colors = [GREY, AMBER]
    if d.electricity_net_kwh > 0:
        vals.append(d.electricity_net_kwh)
        labels.append("Electricity from the plant")
        colors.append(BLUE)
    scaled, unit, dec = _scaled(vals)
    out["bio_energy"] = ChartSpec(
        "hbars", "Yearly energy: demand and what the plant delivers", tuple(labels),
        (Series("energy", scaled, colors=tuple(colors)),),
        x_label=f"Energy per year [{unit}]", decimals=dec)
    return out


# --- hydrogen ------------------------------------------------------------------------------
def hydrogen_charts(inp: HydrogenInputs, d: HydrogenDesign) -> dict[str, ChartSpec]:
    kg = d.hydrogen_kg
    parts = [("Electrolyser", d.cost_electrolyser, PURPLE), ("Stack replacement", d.cost_stack, GREY),
             ("Storage", d.cost_storage, TEAL), ("Solar and wind plants", d.cost_res, GREEN),
             ("Grid electricity", d.cost_grid, RED), ("Water", d.cost_water, BLUE)]
    parts = [p for p in parts if p[1] > 0]
    out = {
        "h2_cost": ChartSpec(
            "hbars", f"What makes up the cost of 1 kg of hydrogen ({d.lcoh:.2f} euro/kg)",
            tuple(p[0] for p in parts), (Series("euro per kg", tuple(p[1] / kg for p in parts),
                                                colors=tuple(p[2] for p in parts)),),
            x_label="euro per kg of hydrogen", decimals=2,
            caption="Every cost of the plant over its life, divided by the kilograms made."),
    }
    if d.monthly_res_kwh:
        f = d.kwh_per_kg_total
        series = [Series("From renewables", tuple(v / f for v in d.monthly_res_kwh), GREEN)]
        if any(v > 0 for v in d.monthly_grid_kwh):
            series.append(Series("From the grid", tuple(v / f for v in d.monthly_grid_kwh), RED))
        out["h2_monthly"] = ChartSpec(
            "stack", "Hydrogen made in each month", MONTHS, tuple(series),
            x_label="Month", y_label="Hydrogen [kg]",
            caption="Summer is high for solar, winter for wind: the electrolyser follows the "
                    "resource." + ("" if d.profile_source != "synthetic" else
                                   " (Invented year: the shape is only indicative.)"))
    if inp.part_load_model and d.load_hist_kwh:
        from resize_energy.core import hydrogen as _h2

        xs = tuple(i / 50 for i in range(5, 51))
        out["h2_partload"] = ChartSpec(
            "lines", "Consumption of the electrolyser at part load", (),
            (Series("kWh per kg", tuple(d.nominal_kwh_per_kg_total * _h2.part_load_factor(
                x, inp.aux_share, inp.stack_gain) for x in xs), PURPLE, x=tuple(x * 100 for x in xs)),),
            x_label="Load [% of nominal power]", y_label="kWh per kg of hydrogen", decimals=0,
            vlines=((inp.min_load * 100, "minimum load"),),
            caption="Flat in the middle, steeply worse below 20 %: the auxiliaries still draw "
                    "power when little hydrogen is made.")
    if inp.degradation_per_1000h > 0 and len(d.kg_by_year) > 1:
        out["h2_ageing"] = ChartSpec(
            "bars", "Hydrogen made in each year of the plant's life",
            tuple(str(i + 1) for i in range(len(d.kg_by_year))),
            (Series("kg", d.kg_by_year, PURPLE),), x_label="Year", y_label="Hydrogen [kg]",
            caption="The stack ages and makes less hydrogen from the same electricity; each jump "
                    "up is a new stack.")
    if d.tank_level_kg:
        out["h2_tank"] = ChartSpec(
            "lines", "Hydrogen in the tank through the year (constant offtake)", (),
            (Series("kg in the tank", d.tank_level_kg, TEAL,
                    x=tuple(float(i) for i in range(len(d.tank_level_kg))), fill=True),),
            x_label="Day of the year", y_label="Hydrogen stored [kg]",
            hlines=((d.storage_kg, f"tank {d.storage_kg:,.0f} kg"),),
            caption="It fills when production is above the average and empties otherwise: the "
                    "tank is the highest point.")
    out["h2_carbon"] = ChartSpec(
        "hbars", "Carbon footprint of the hydrogen",
        ("This plant", "Limit for 'renewable' hydrogen (EU)", "Hydrogen from natural gas"),
        (Series("kg CO2 per kg", (d.co2_kg_per_kg, 3.4, inp.grey_h2_kg_co2_per_kg),
                colors=(GREEN if d.co2_kg_per_kg <= 3.4 else RED, GREY, GREY)),),
        x_label="kg of CO2 per kg of hydrogen", decimals=1,
        caption="Below the EU limit (about 3.4) the hydrogen counts as renewable.")
    return out | sensitivity_charts("h2", d.sensitivity)


# --- sensitivity ---------------------------------------------------------------------------
_CURVE_COLORS = (BLUE, GREEN, AMBER, PURPLE, RED, TEAL, GREY, "#9C4F96")


def economics_charts(prefix: str, econ: Economics | None) -> dict[str, ChartSpec]:
    """Cash flow, costs against savings, and the sensitivity of the net present value."""
    if econ is None:
        return {}
    years = tuple(float(y) for y in range(len(econ.cash)))
    out = {
        f"{prefix}_cash": ChartSpec(
            "lines", "Money over the life of the plant (discounted, in thousand euro)", (),
            (Series("cumulative result [kEUR]", tuple(c / 1000.0 for c in econ.cash), GREEN,
                    x=years, fill=True),),
            x_label="Year", y_label="Cumulative result [thousand euro]", decimals=1, height=280,
            hlines=((0.0, "break-even"),),
            caption=f"The line starts at -{econ.capex:,.0f} euro (the investment) and crosses "
                    f"zero after about {econ.discounted_payback_years:.1f} years once future "
                    f"money is discounted; it ends at the net present value, "
                    f"{econ.npv:,.0f} euro."),
        f"{prefix}_unit_cost": ChartSpec(
            "hbars", "Cost of making a kWh against its value",
            ("Cost of this plant (LCOE)", "Average value of its energy"),
            (Series("euro/kWh", (econ.lcoe, econ.savings_per_year / econ.energy_kwh),
                    colors=(RED, GREEN)),),
            x_label="euro per kWh", decimals=3,
            caption="Green longer than red: each kWh saves more than it costs to produce. "
                    "The green bar averages the energy you use (valued at the retail price) "
                    "and the surplus you export (at the lower export price)."),
    }
    return out | sensitivity_charts(prefix, econ.sensitivity)


def sensitivity_charts(prefix: str, sens: Sensitivity | None) -> dict[str, ChartSpec]:
    """Two pictures: which input matters most, and what happens to the result as it moves."""
    if sens is None or not sens.curves:
        return {}
    top = sens.curves[:8]
    pct = tuple(s * 100 for s in sens.steps)
    lo, hi = pct[0], pct[-1]
    swing = tuple(c.swing / 2.0 for c in top)
    first = top[0]
    return {
        f"{prefix}_sens_swing": ChartSpec(
            "hbars", f"What moves the result most (each input changed by +/- {hi:.0f} %)",
            tuple(c.label for c in top),
            (Series(f"+/- {sens.unit}", swing, colors=(GREEN,) + (LIGHT,) * (len(top) - 1)),),
            x_label=f"Change in {sens.metric.lower()} [{sens.unit}]", decimals=sens.decimals,
            caption=f"A +/- {hi:.0f} % change of '{first.label.lower()}' moves the result by about "
                    f"{sens.relative_swing(first):.0%}: it is the number worth checking first."),
        f"{prefix}_sens_spider": ChartSpec(
            "lines", f"{sens.metric}: what if an input is {lo:.0f} % or +{hi:.0f} % off?", (),
            tuple(Series(c.label, c.values, _CURVE_COLORS[i % len(_CURVE_COLORS)], x=pct)
                  for i, c in enumerate(top[:6])),
            x_label="Change of the input [%]", y_label=f"{sens.metric} [{sens.unit}]",
            decimals=sens.decimals, height=300,
            caption="The steeper the line, the more the result depends on that input. All lines "
                    f"cross at 0 %, the case you chose ({sens.base:,.{sens.decimals}f} "
                    f"{sens.unit})."),
    }


# --- comparison ----------------------------------------------------------------------------
def comparison_charts(inp: ComparisonInputs, r: ComparisonResult) -> dict[str, ChartSpec]:
    techs = r.techs
    names = tuple(t.name for t in techs)
    colors = tuple(TECH_COLORS[t.key] for t in techs)
    c = inp.costs
    refs: list[tuple[float, str]] = []
    if any(t.product == "electricity" for t in techs):
        refs.append((c.retail_price_eur_per_kwh, "electricity price"))
    if r.hydrogen is not None:
        refs.append((r.hydrogen.reference_price_eur_per_kwh, "gas hydrogen"))
    life = int(math.ceil(max(t.lifetime_years for t in techs)))
    years = tuple(float(y) for y in range(life + 1))
    cash = []
    for t in techs:
        vals = tuple(-t.capex_eur / 1e6 + t.net_benefit_eur_per_year
                     * (eco.annuity_factor(c.discount_rate, min(y, t.lifetime_years))
                        if y > 0 else 0.0) / 1e6 for y in years)
        cash.append(Series(t.name, vals, TECH_COLORS[t.key], x=years))
    payback = tuple(t.payback_years if math.isfinite(t.payback_years) else math.inf
                    for t in techs)
    return {
        "cmp_lcoe": ChartSpec(
            "hbars", "Cost of one kWh (lower is better)", names,
            (Series("euro/kWh", tuple(t.lcoe_eur_per_kwh for t in techs), colors=colors),),
            x_label="euro per kWh (LCOE)", vlines=tuple(refs), decimals=3,
            caption="The lines are what you would pay without the plant: a bar left of its "
                    "line means producing is cheaper than buying."),
        "cmp_payback": ChartSpec(
            "hbars", "Years to earn back the investment (lower is better)", names,
            (Series("years", payback, colors=colors),), x_label="Simple payback [years]",
            decimals=1,
            caption="'never' means the yearly savings do not cover the running costs."),
        "cmp_cash": ChartSpec(
            "lines", "Money over the life of the plant (discounted)", (), tuple(cash),
            x_label="Years", y_label="Cumulative result [million euro]",
            hlines=((0.0, "break-even"),), decimals=1, height=300,
            caption="Where a line crosses zero the plant has repaid itself; the end of the "
                    "line is its net present value."),
        "cmp_co2": ChartSpec(
            "hbars", "CO2 avoided each year (higher is better)", names,
            (Series("t CO2", tuple(t.co2_avoided_t_per_year for t in techs), colors=colors),),
            x_label="tonnes of CO2 per year"),
    } | _compare_sens_charts(techs, r.sensitivity)


def _compare_sens_charts(techs, sens) -> dict[str, ChartSpec]:
    if not sens:
        return {}
    pct = tuple(x * 100 for x in (-0.2, -0.1, 0.0, 0.1, 0.2))
    texts = {
        "capex": ("cmp_sens_capex", "All capital costs together",
                  "If every technology costs 20 % more or less to build, the order of the "
                  "lines tells you whether the winner changes."),
        "rate": ("cmp_sens_rate", "The discount rate",
                 "Capital-heavy technologies (those starting higher on the left) suffer most "
                 "when money is more expensive."),
    }
    out = {}
    for key, (name, what, caption) in texts.items():
        data = sens.get(key, {})
        series = tuple(Series(t.name, data[t.key], TECH_COLORS[t.key], x=pct)
                       for t in techs if t.key in data)
        if series:
            out[name] = ChartSpec(
                "lines", f"Cost of one kWh if {what.lower()} change", (), series,
                x_label="Change [%]", y_label="LCOE [euro/kWh]", decimals=3, height=290,
                caption=caption)
    return out


def _all_finite_or_inf(spec: ChartSpec) -> bool:
    return all(not math.isnan(v) for s in spec.series for v in s.values)


__all__ = [
    "ChartSpec", "Series", "biomass_charts", "comparison_charts", "geothermal_charts",
    "hydro_charts", "hydrogen_charts", "nice_ticks", "pv_charts", "unit_for", "wind_charts",
]

# --- battery storage -----------------------------------------------------------------------
def battery_charts(inp: BatteryInputs, d: BatteryDesign) -> dict[str, ChartSpec]:
    out: dict[str, ChartSpec] = {}
    xs = tuple(p.capacity_kwh for p in d.sweep)
    out["bat_sweep"] = ChartSpec(
        "lines", "Self-sufficiency grows with the battery, then flattens", (),
        (Series("self-sufficiency [%]", tuple(p.self_sufficiency * 100 for p in d.sweep),
                GREEN, x=xs),
         Series("self-consumption [%]", tuple(p.self_consumption * 100 for p in d.sweep),
                BLUE, x=xs)),
        x_label="Battery capacity [kWh]", y_label="Share [%]",
        vlines=((d.capacity_kwh, "your battery"),), height=290,
        caption="The first kWh give a lot, the last ones almost nothing: they are filled only "
                "on the sunniest days.")
    out["bat_npv"] = ChartSpec(
        "lines", "Money gained or lost by the battery over its life", (),
        (Series("net present value [euro]", tuple(p.npv for p in d.sweep), AMBER, x=xs),),
        x_label="Battery capacity [kWh]", y_label="Net present value [euro]",
        hlines=((0.0, "break-even"),), vlines=((d.capacity_kwh, "your battery"),), height=290,
        caption="Above zero the battery repays itself; below, it costs more than it saves.")
    labels = ("Without battery", "With battery")
    out["bat_grid"] = ChartSpec(
        "stack", "Where the electricity you consume comes from", labels,
        (Series("Directly from the plant", (d.load_kwh - d.import_without_kwh
                                            - 0.0, d.direct_kwh), GREEN),
         Series("From the battery", (0.0, d.battery_kwh), TEAL),
         Series("From the grid", (d.import_without_kwh, d.import_kwh), RED)),
        y_label="Energy [kWh]",
        caption=f"The grid share falls from {1 - d.self_sufficiency_without:.0%} to "
                f"{1 - d.self_sufficiency:.0%} of the consumption.")
    series = [Series("Directly from the plant", d.monthly_direct, GREEN)]
    if d.battery_kwh > 0:
        series.append(Series("From the battery", d.monthly_battery, TEAL))
    series.append(Series("From the grid", d.monthly_import, RED))
    out["bat_monthly"] = ChartSpec(
        "stack", "The electricity you consume, month by month", MONTHS, tuple(series),
        x_label="Month", y_label="Energy [kWh]",
        caption="In winter the plant produces little and the battery has nothing to store: "
                "the grid does most of the work.")
    for name, label, week in (("bat_summer", "A summer week", d.summer_week),
                              ("bat_winter", "A winter week", d.winter_week)):
        load, gen, soc, _ = week
        hours = tuple(float(h) for h in range(len(load)))
        out[name] = ChartSpec(
            "lines", f"{label}: consumption, production and energy in the battery", (),
            (Series("consumption [kW]", load, GREY, x=hours),
             Series("production [kW]", gen, GREEN, x=hours),
             Series("battery charge [kWh]", soc, TEAL, x=hours, fill=True)),
            x_label="Hours (the week starts on Monday at midnight)", y_label="kW or kWh",
            decimals=1, height=290,
            caption="The battery fills when the production is above the consumption and "
                    "empties in the evening.")
    return out | sensitivity_charts("bat", d.sensitivity)


# --- solar thermal -------------------------------------------------------------------------
def solar_charts(inp: SolarThermalInputs, d: SolarThermalDesign) -> dict[str, ChartSpec]:
    r = d.run
    out: dict[str, ChartSpec] = {}
    if r.heat_demand_kwh > 0:
        out["solar_monthly"] = ChartSpec(
            "bars", "Hot water: what you need each month and what the sun gives", MONTHS,
            (Series("demand [kWh]", r.monthly_heat_demand_kwh, GREY),
             Series("covered by the sun [kWh]", r.monthly_heat_solar_kwh, AMBER)),
            x_label="Month", y_label="Heat [kWh]", decimals=0,
            caption=f"In summer the sun covers almost everything, in winter little: over the "
                    f"year {r.heat_fraction:.0%} of the hot water is solar.")
    if r.cooling_demand_kwh > 0:
        out["solar_cooling"] = ChartSpec(
            "bars", "Cooling: what you need each month and what the chiller delivers", MONTHS,
            (Series("cooling demand [kWh]", r.monthly_cooling_demand_kwh, GREY),
             Series("cold from the sun [kWh]", r.monthly_cooling_solar_kwh, BLUE)),
            x_label="Month", y_label="Cold [kWh]", decimals=0,
            caption=f"The {SOLAR_CHILLERS[inp.chiller].name.split(' (')[0].lower()} covers "
                    f"{r.cooling_fraction:.0%} of the cooling with heat from the collectors: it "
                    "works exactly when the sun is strongest.")
        if d.cooling_options:
            opts = d.cooling_options
            out["solar_chillers"] = ChartSpec(
                "hbars", "Cooling technologies on the same collectors",
                tuple(o.name.split(" (")[0] for o in opts),
                (Series("share of the cooling [%]", tuple(o.cooling_fraction * 100 for o in opts),
                        colors=tuple(BLUE if o.is_main else LIGHT for o in opts)),),
                x_label="Cooling covered by the sun [%]", decimals=0,
                caption="Blue is your main technology. Mean COPs: " + ", ".join(
                    f"{o.name.split(' (')[0].lower()} {o.mean_cop:.2f}" for o in opts) + ".")
    parts = [("Hot water", r.heat_solar_kwh), ("Adsorption chiller", r.chiller_heat_kwh),
             ("Tank heat losses", r.store_loss_kwh), ("Heat dumped (overheating)", r.wasted_kwh)]
    parts = [p for p in parts if p[1] > 0.5]
    out["solar_balance"] = ChartSpec(
        "hbars", "Where the heat of the collectors goes",
        tuple(p[0] for p in parts),
        (Series("kWh per year", tuple(p[1] for p in parts),
                colors=tuple((AMBER, BLUE, GREY, RED)[("Hot water", "Adsorption chiller",
                                                       "Tank heat losses",
                                                       "Heat dumped (overheating)").index(p[0])]
                             for p in parts)),),
        x_label="Heat per year [kWh]", decimals=0,
        caption=f"The collectors put {r.collector_kwh:,.0f} kWh a year into the tank. Red is heat "
                "that nobody used: a sign of a field that is too big for the load.")
    if d.sweep:
        areas = tuple(a for a, *_ in d.sweep)
        out["solar_area"] = ChartSpec(
            "lines", "More collectors: the solar fraction rises, each m2 yields less", (),
            (Series("solar fraction [%]", tuple(f * 100 for _, f, _, _ in d.sweep), AMBER,
                    x=areas),
             Series("energy per m2 [kWh / 10]", tuple(y / 10 for _, _, y, _ in d.sweep), BLUE,
                    x=areas)),
            x_label="Collector area [m2]", y_label="Percent  /  kWh per m2 divided by 10",
            decimals=0, height=280, vlines=((d.area_m2, "chosen"),),
            caption="The orange line flattens and the blue one falls: the last square metres "
                    "work less. The best area is usually before the orange line becomes flat.")
        out["solar_npv"] = ChartSpec(
            "lines", "Net present value against collector area (thousand euro)", (),
            (Series("NPV [kEUR]", tuple(n / 1000.0 for *_, n in d.sweep), GREEN, x=areas),),
            x_label="Collector area [m2]", y_label="NPV [thousand euro]", decimals=1,
            height=250, hlines=((0.0, "break-even"),), vlines=((d.area_m2, "chosen"),),
            caption="Above the zero line the plant repays itself; the top of the curve is the "
                    "area that earns most.")
    temps = tuple(float(x) for x in range(0, 101, 10))
    types = [("flat", BLUE), ("tube", GREEN), ("unglazed", GREY)]
    out["solar_efficiency"] = ChartSpec(
        "lines", "Collector efficiency against how hot the water is (sun 800 W/m2)", (),
        tuple(Series(
            SOLAR_COLLECTORS[k].name + (" (yours)" if k == inp.collector else ""),
            tuple(solar_eff(d.collector if k == inp.collector else SOLAR_COLLECTORS[k],
                            20.0 + t, 20.0, 800.0) * 100 for t in temps), col, x=temps)
              for k, col in types),
        x_label="Collector water minus outside air [K]", y_label="Efficiency [%]", decimals=0,
        height=280,
        caption="At low temperature differences the glazed flat plate is best; at the high "
                "temperatures of a chiller or industrial heat the evacuated tube keeps its "
                "efficiency.")
    week_x = tuple(float(h) for h in range(168))
    lines = []
    for name, color, label in (("winter", BLUE, "winter week (mid-January)"),
                               ("summer", AMBER, "summer week (mid-July)")):
        vals = r.store_temp_week.get(name, ())
        if len(vals) == 168:
            lines.append(Series(label, vals, color, x=week_x))
    hl = [(95.0, "overheating"), (inp.t_use_c, "hot-water set point")]
    if inp.cooling_kwh_per_year > 0:
        hl.append((inp.t_drive_min_c, "chiller minimum"))
    if lines:
        out["solar_tank"] = ChartSpec(
            "lines", "Tank temperature over a winter and a summer week", (), tuple(lines),
            x_label="Hour of the week", y_label="Tank temperature [degC]", decimals=0,
            height=280, hlines=tuple(hl),
            caption="The tank heats up during the day and cools when the hot water is used. "
                    "Near the red line the field is making more heat than the load can use.")
    years = tuple(float(y) for y in range(int(math.ceil(inp.life_years)) + 1))
    net = d.savings_per_year - d.om_per_year
    cash = [-d.capex] + [-d.capex + net * eco.annuity_factor(inp.discount_rate, min(float(y), inp.life_years))
                         for y in range(1, len(years))]
    out["solar_cash"] = ChartSpec(
        "lines", "Money over the life of the plant (discounted, thousand euro)", (),
        (Series("cumulative result [kEUR]", tuple(c / 1000.0 for c in cash), GREEN, x=years,
                fill=True),),
        x_label="Year", y_label="Cumulative result [thousand euro]", decimals=1, height=260,
        hlines=((0.0, "break-even"),),
        caption=f"Investment {d.capex:,.0f} euro; the line ends at the net present value, "
                f"{d.npv:,.0f} euro.")
    return out | sensitivity_charts("solar", d.sensitivity)


# --- hydropower ----------------------------------------------------------------------------
def hydro_charts(inp: HydroInputs, d: HydroDesign) -> dict[str, ChartSpec]:
    out: dict[str, ChartSpec] = {}
    xs = tuple(100.0 * p for p, _, _ in d.curve)
    out["hydro_fdc"] = ChartSpec(
        "lines", "River flow through the year, from the wettest day to the driest", (),
        (Series("river", tuple(q for _, q, _ in d.curve), BLUE, x=xs),
         Series("through the turbine", tuple(t for _, _, t in d.curve), TEAL, x=xs, fill=True)),
        x_label="Share of the time the flow is exceeded [%]", y_label="Flow [m3/s]", decimals=2,
        hlines=((inp.eco_flow_m3s, "environmental flow"),
                (d.design_flow_m3s + inp.eco_flow_m3s, "design flow + environmental")),
        caption="The turbine takes what is above the environmental flow, up to its design flow, "
                f"and stops below {d.min_flow_m3s:.2f} m3/s.")
    total = sum(q for _, q, _ in d.curve) or 1.0
    eco = sum(min(q, inp.eco_flow_m3s) for _, q, _ in d.curve) / total
    used = d.water_used_fraction
    rest = max(0.0, 1.0 - eco - used)
    out["hydro_water"] = ChartSpec(
        "hbars", "Where the water of the river goes",
        ("Stays in the river (environmental flow)", "Goes through the turbine",
         "Passes by (above the design flow or too little)"),
        (Series("share of the water [%]", (eco * 100, used * 100, rest * 100),
                colors=(GREEN, TEAL, GREY)),),
        x_label="Share of the yearly volume of water [%]", decimals=0,
        caption="A run-of-river plant has no reservoir: the water it cannot use goes by.")
    sweep = exceedance_sweep(inp)
    if len(sweep) > 2:
        sx = tuple(100.0 * p for p, *_ in sweep)
        scaled, unit, dec = _scaled([e for _, _, e, _ in sweep])
        out["hydro_sweep"] = ChartSpec(
            "lines", "Bigger or smaller turbine: energy and capacity factor", (),
            (Series(f"energy [{unit}]", scaled, TEAL, x=sx),
             Series("capacity factor [%]", tuple(c * 100 for *_, c in sweep), AMBER, x=sx)),
            x_label="Design flow, exceeded this share of the time [%]", y_label="", decimals=dec,
            vlines=((100.0 * inp.design_exceedance, "your choice"),), height=290,
            caption="Moving to the left (a bigger turbine) the energy grows more and more "
                    "slowly while the capacity factor, and the cost per kWh, get worse.")
    return out


# --- geothermal ----------------------------------------------------------------------------
def geothermal_charts(inp: GeothermalInputs, d: GeothermalDesign) -> dict[str, ChartSpec]:
    out: dict[str, ChartSpec] = {}
    if d.pathway == "heat":
        lf = max(d.load_factor, 1e-6)
        n = 1.0 / lf - 1.0
        xs = tuple(float(h) for h in range(0, 8761, 120))
        curve = tuple(inp.peak_heat_kw * (1.0 - h / 8760.0) ** n for h in xs)
        plant = d.wells_pairs * d.heat_per_pair_kw
        out["geo_load"] = ChartSpec(
            "lines", "Heat demand through the year, from the highest hour to the lowest", (),
            (Series("heat demand", curve, RED, x=xs, fill=True),),
            x_label="Hours of the year (sorted from the highest demand)",
            y_label="Heat power [kW]", hlines=((plant, f"wells {plant:,.0f} kW"),),
            caption=f"The wells give a nearly constant power and cover {d.coverage:.0%} of the "
                    "heat: the part of the curve below the line. A boiler takes the peaks.")
        vals = [inp.annual_heat_demand_kwh, d.heat_kwh]
        scaled, unit, dec = _scaled(vals)
        out["geo_energy"] = ChartSpec(
            "hbars", "Yearly heat: demand and what the wells deliver",
            ("Heat demand", "Heat from the wells"), (Series("energy", scaled, colors=(GREY, RED)),),
            x_label=f"Energy per year [{unit}]", decimals=dec)
        return out
    gross = d.gross_kw
    own = max(0.0, d.gross_kw - d.pumps_kw - d.net_kw)
    scaled, unit, dec = _scaled([gross, own, d.pumps_kw, d.net_kw], "kW")
    out["geo_power"] = ChartSpec(
        "hbars", "From the turbine to the grid",
        ("Gross power of the turbine", "Used by the plant itself", "Used by the pumps",
         "Net power"), (Series("power", scaled, colors=(AMBER, GREY, GREY, GREEN)),),
        x_label=f"Power [{unit}]", decimals=dec,
        caption="What reaches the grid is what is left after the plant's own use and the pumps.")
    m = inp.flow_per_well_kg_s
    binary_t = tuple(float(t) for t in range(100, 201, 5))
    flash_t = tuple(float(t) for t in range(160, 251, 5))
    out["geo_temperature"] = ChartSpec(
        "lines", "Power of one well against the brine temperature", (),
        (Series("binary plant", tuple(
            _geo.binary_cycle_efficiency(t) * _geo.thermal_power_kw(m, t, inp.reinjection_temp_c)
            for t in binary_t if t > inp.reinjection_temp_c), BLUE,
            x=tuple(t for t in binary_t if t > inp.reinjection_temp_c)),
         Series("flash plant", tuple(
             inp.flash_utilization * m * _geo.brine_exergy_kj_per_kg(t, inp.ambient_temp_c)
             for t in flash_t), RED, x=flash_t)),
        x_label="Brine temperature [degC]", y_label="Gross power [kW]",
        vlines=((inp.reservoir_temp_c, "your reservoir"),), height=290,
        caption="Hotter brine gives much more power from the same flow. The binary fit is "
                "built on plants between 103 and 166 degC.")
    return out
