"""Plain-text summary of a solar thermal project for the AI tutor."""

from __future__ import annotations

from resize_energy.core.solar_thermal_design import SolarThermalDesign, SolarThermalInputs
from resize_energy.tutor.checker import Finding

_SEVERITY = {"error": "ERROR", "warning": "WARNING", "info": "NOTE", "ok": "OK"}


def build_solar_context(inp: SolarThermalInputs, d: SolarThermalDesign,
                        findings: list[Finding]) -> str:
    r = d.run
    c = d.collector
    lines = [
        "PROJECT: solar thermal plant (hot water and/or adsorption cooling), preliminary "
        "hourly simulation made with RESize",
        "",
        "INPUTS",
        f"- Hot water {inp.dhw_litres_per_day:g} L/day at {inp.t_use_c:g} degC; cooling "
        f"{inp.cooling_kwh_per_year:,.0f} kWh/year",
        f"- Site: latitude {inp.latitude_deg:.1f}, {inp.irradiation_kwh_m2:,.0f} kWh/m2 on the "
        f"collector, air {inp.t_mean_c:g} degC +/- {inp.t_season_amp_c:g}",
        f"- Collector {c.name}: eta0 {c.eta0}, a1 {c.a1}, a2 {c.a2}; "
        f"{inp.store_l_per_m2:g} L of store per m2",
        f"- Chiller COP {inp.cop_nominal} (nominal), drive {inp.t_drive_min_c:g}-"
        f"{inp.t_drive_nominal_c:g} degC",
        "",
        "RESULTS",
        f"- {d.area_m2:g} m2 of collectors, tank {d.store_litres:,.0f} L, chiller "
        f"{d.chiller_kw:.1f} kW; collector heat {r.collector_kwh:,.0f} kWh/year",
        f"- Solar fraction {r.solar_fraction:.0%} (hot water {r.heat_fraction:.0%}, cooling "
        f"{r.cooling_fraction:.0%}); {r.hours_stagnation} stagnation hours, "
        f"{r.wasted_kwh:,.0f} kWh dumped",
        f"- CAPEX {d.capex:,.0f} euro; savings {d.savings_per_year:,.0f} euro/year; payback "
        f"{d.payback_years:.1f} years; NPV {d.npv:,.0f} euro; LCOH {d.lcoh:.3f} euro/kWh; "
        f"CO2 avoided {d.co2_avoided_t:.2f} t/year",
        "",
        "DESIGN CHECKS",
    ]
    lines += [f"- [{_SEVERITY[f.severity]}] {f.message}" for f in findings] or ["- (none)"]
    return "\n".join(lines)
