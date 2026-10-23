"""Plain-text summary of a green hydrogen project for the AI tutor."""

from __future__ import annotations

from resize_energy.core.hydrogen_design import HydrogenDesign, HydrogenInputs
from resize_energy.tutor.checker import Finding

_SEVERITY = {"error": "ERROR", "warning": "WARNING", "info": "NOTE", "ok": "OK"}


def build_hydrogen_context(inp: HydrogenInputs, d: HydrogenDesign,
                           findings: list[Finding]) -> str:
    sources = [n for n, on in (("PV", inp.use_pv), ("wind", inp.use_wind),
                               ("grid", inp.use_grid)) if on]
    lines = [
        "PROJECT: green hydrogen with a PEM electrolyser (preliminary sizing made with RESize)",
        "",
        "INPUTS",
        f"- Mode: {inp.mode}; sources: {', '.join(sources)}; hourly profile: {d.profile_source}",
        f"- Consumption {inp.kwh_per_kg_stack:.1f} kWh/kg (+ compression "
        f"{d.compression_kwh_per_kg:.2f}); minimum load {inp.min_load:.0%}; storage "
        f"{inp.storage_days:.0f} days at {inp.storage_bar:.0f} bar; grid limit "
        f"{inp.grid_hours_cap:,.0f} h",
        "",
        "RESULTS",
        f"- Electrolyser {d.electrolyser_kw:,.0f} kW; PV {d.pv_kwp:,.0f} kWp; wind "
        f"{d.wind_kw:,.0f} kW",
        f"- Hydrogen {d.hydrogen_kg:,.0f} kg/year ({d.hydrogen_kg_per_day:,.0f} kg/day), "
        f"{d.full_load_hours:,.0f} full-load hours, system efficiency {d.efficiency_lhv:.0%} (LHV)",
        f"- Renewable energy used {d.res_utilisation:.0%}; grid share {d.grid_share:.0%}",
        f"- LCOH {d.lcoh:.2f} euro/kg; carbon intensity {d.co2_kg_per_kg:.2f} kg CO2/kg; "
        f"storage {d.storage_kg:,.0f} kg ({d.storage_m3:,.1f} m3); water {d.water_m3:,.0f} m3/year",
        "",
        "DESIGN CHECKS",
    ]
    lines += [f"- [{_SEVERITY[f.severity]}] {f.message}" for f in findings] or ["- (none)"]
    return "\n".join(lines)
