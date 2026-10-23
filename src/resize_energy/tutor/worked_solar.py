"""Worked examples of the solar thermal topics, with the user's own numbers."""

from __future__ import annotations

from resize_energy.core import solar_thermal as st
from resize_energy.core.solar_thermal_design import SolarThermalDesign, SolarThermalInputs

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def solar_worked_example(key: str, inp: SolarThermalInputs, d: SolarThermalDesign) -> str | None:
    r = d.run
    c = d.collector
    if key == "solar.resource":
        return (f"Irradiation on the collector plane {inp.irradiation_kwh_m2:,.0f} kWh/m2 per "
                f"year at latitude {inp.latitude_deg:.1f}; mean air temperature "
                f"{inp.t_mean_c:.0f} degC, seasonal swing +/- {inp.t_season_amp_c:.0f} K")
    if key == "solar.collector":
        g, ta, tm = 800.0, 20.0, 60.0
        eta = st.collector_efficiency(c, tm, ta, g)
        cold = st.collector_efficiency(c, tm, 0.0, 300.0)
        return (f"{c.name}: eta0 {c.eta0:.2f}, a1 {c.a1:g}, a2 {c.a2:g}\n"
                f"At G = 800 W/m2, water 60 degC, air 20 degC: eta = {c.eta0:.2f} - "
                f"{c.a1:g} x 40 / 800 - {c.a2:g} x 40^2 / 800 = {eta:.2f}\n"
                f"A grey winter day (G = 300, air 0 degC): eta = {cold:.2f}")
    if key == "solar.load":
        if inp.dhw_litres_per_day <= 0:
            return "No hot-water demand in this project (0 litres per day): cooling only."
        mains = st.mains_temperature(15, inp.t_mean_c, inp.t_season_amp_c)
        mains_s = st.mains_temperature(196, inp.t_mean_c, inp.t_season_amp_c)
        return (f"{inp.dhw_litres_per_day:,.0f} L/day x 1.163 Wh/(L K) x ({inp.t_use_c:.0f} - "
                f"{mains:.0f}) K = {inp.dhw_litres_per_day * 0.001163 * (inp.t_use_c - mains):.1f} "
                f"kWh per winter day ({inp.dhw_litres_per_day * 0.001163 * (inp.t_use_c - mains_s):.1f}"
                f" in summer)\nYear: {r.heat_demand_kwh:,.0f} kWh")
    if key == "solar.store":
        return (f"Tank {d.store_litres:,.0f} L ({inp.store_l_per_m2:g} L per m2 of collector): "
                f"{d.store_litres * st.WATER_KWH_PER_L_K:.2f} kWh per kelvin\n"
                f"Standing loss over the year {r.store_loss_kwh:,.0f} kWh "
                f"({r.store_loss_kwh / max(1.0, r.collector_kwh):.0%} of the collector heat)")
    if key == "solar.simulation":
        return (f"Collector heat into the tank {r.collector_kwh:,.0f} kWh = "
                f"{r.heat_solar_kwh:,.0f} (hot water) + {r.chiller_heat_kwh:,.0f} (chiller) + "
                f"{r.store_loss_kwh:,.0f} (tank losses) + {r.wasted_kwh:,.0f} dumped "
                f"+ change of the stored heat")
    if key == "solar.solar_fraction":
        parts = []
        if r.heat_demand_kwh > 0:
            parts.append(f"Hot water: {r.heat_solar_kwh:,.0f} / {r.heat_demand_kwh:,.0f} kWh = "
                         f"{r.heat_fraction:.0%}")
        if r.cooling_demand_kwh > 0:
            parts.append(f"Cooling: {r.cooling_solar_kwh:,.0f} / {r.cooling_demand_kwh:,.0f} kWh "
                         f"= {r.cooling_fraction:.0%}")
        parts.append(f"Overall solar fraction {r.solar_fraction:.0%}")
        return "\n".join(parts)
    if key == "solar.area":
        pts = "; ".join(f"{a:g} m2 -> {f:.0%}, {y:,.0f} kWh/m2" for a, f, y, _ in d.sweep)
        return (f"{d.area_m2:g} m2 chosen"
                f"{'' if d.target_reached else ' (the target fraction could not be reached)'}; "
                f"{d.yield_kwh_m2:,.0f} kWh of useful energy per m2\n" + pts)
    if key == "solar.stagnation":
        return (f"{r.hours_stagnation} hours at the 95 degC limit; {r.wasted_kwh:,.0f} kWh dumped "
                f"({r.wasted_kwh / max(1.0, r.collector_kwh + r.wasted_kwh):.0%} of the heat the "
                f"collectors could have made)")
    if key == "solar.adsorption":
        if inp.cooling_kwh_per_year <= 0:
            return "No cooling in this project (0 kWh of cold): the chiller is not part of it."
        return (f"Cooling demand {r.cooling_demand_kwh:,.0f} kWh, chiller {d.chiller_kw:.1f} kW "
                f"of cooling; it drew {r.chiller_heat_kwh:,.0f} kWh of hot water and produced "
                f"{r.cooling_solar_kwh:,.0f} kWh of cold ({r.cooling_fraction:.0%} of the demand)")
    if key == "solar.chiller_cop":
        if inp.cooling_kwh_per_year <= 0:
            return "No cooling in this project: nominal COP 0 is not used."
        mean = r.cooling_solar_kwh / r.chiller_heat_kwh if r.chiller_heat_kwh > 0 else 0.0
        lo = st.chiller_cop(inp.cop_nominal, inp.t_drive_min_c + 5, inp.t_drive_min_c,
                               inp.t_drive_nominal_c)
        return (f"Nominal COP {inp.cop_nominal:.2f} at {inp.t_drive_nominal_c:.0f} degC; at "
                f"{inp.t_drive_min_c + 5:.0f} degC it is {lo:.2f}; stops below "
                f"{inp.t_drive_min_c:.0f} degC\nAverage over the year: {r.cooling_solar_kwh:,.0f}"
                f" / {r.chiller_heat_kwh:,.0f} = {mean:.2f}; {r.hours_below_drive} hours with "
                "cooling wanted but the tank too cold")
    if key == "solar.chillers":
        if inp.cooling_kwh_per_year <= 0:
            return "No cooling in this project: 0 cooling technologies evaluated."
        if not d.cooling_options:
            return (f"Only the main technology was evaluated (1 of {len(st.CHILLERS)}): "
                    f"{st.CHILLERS[inp.chiller].name}. Tick the others in step 1 to compare.")
        return "\n".join(
            f"{o.name}{' (main)' if o.is_main else ''}: {o.chiller_kw:.1f} kW, mean COP "
            f"{o.mean_cop:.2f}, {o.cooling_fraction:.0%} of the cooling, NPV {o.npv:,.0f} euro"
            for o in d.cooling_options)
    if key == "solar.economics":
        return (f"CAPEX = {d.collector_cost:,.0f} (collectors) + {d.store_cost:,.0f} (tank) + "
                f"{d.chiller_cost:,.0f} (chiller) + {d.fixed_cost:,.0f} (fixed) = {d.capex:,.0f} "
                f"euro; O&M {d.om_per_year:,.0f} euro/year\n"
                f"Savings {d.savings_per_year:,.0f} euro/year -> payback {d.payback_years:.1f} "
                f"years; NPV over {inp.life_years:g} years at {inp.discount_rate:.1%} = "
                f"{d.npv:,.0f} euro\nLCOH = {d.lcoh:.3f} euro/kWh against "
                f"{inp.heat_price:.3f} euro/kWh for the heat you replace")
    if key == "solar.co2":
        return (f"{r.heat_solar_kwh:,.0f} kWh x {inp.heat_ef_kg_per_kwh} kg/kWh"
                f" + electricity saved x {inp.grid_ef_kg_per_kwh} kg/kWh = "
                f"{d.co2_avoided_t:.2f} t of CO2 per year")
    if key == "solar.sensitivity":
        s = d.sensitivity
        if s is None:
            return f"No sensitivity available; base NPV {d.npv:,.0f} euro."
        lines = [f"Base NPV {s.base:,.0f} euro. Swing for -20 % / +20 %:"]
        lines += [f"- {c.label}: {c.swing:,.0f} euro" for c in s.curves[:4]]
        return "\n".join(lines)
    return None
