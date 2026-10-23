"""Plain-text summary of a biomass project for the AI tutor."""

from __future__ import annotations

from resize_energy.core.biomass_design import PATHWAYS, BiomassDesign, BiomassInputs
from resize_energy.tutor.checker import Finding

_SEVERITY = {"error": "ERROR", "warning": "WARNING", "info": "NOTE", "ok": "OK"}


def build_biomass_context(inp: BiomassInputs, d: BiomassDesign, findings: list[Finding]) -> str:
    lines = [f"PROJECT: biomass, {PATHWAYS[inp.pathway]} (preliminary sizing made with RESize)",
             "", "INPUTS"]
    if inp.pathway == "biogas":
        a, b = inp.substrate_a, inp.substrate_b
        lines += [
            f"- Electricity demand {inp.annual_electricity_demand_kwh:,.0f} kWh/year, coverage "
            f"{inp.coverage:.0%}; heat demand {inp.annual_heat_demand_kwh:,.0f} kWh/year",
            f"- Substrates: {1 - inp.share_b:.0%} {a.name}, {inp.share_b:.0%} {b.name}",
            f"- CHP: eta_el {inp.eta_el:.2f}, eta_th {inp.eta_th:.2f}, {inp.operating_hours:,.0f} h; "
            f"parasitic electricity {inp.parasitic_electricity:.0%}; digester heating "
            f"{inp.digester_heat_share:.0%} of the CHP heat; HRT {inp.hrt_days:.0f} days",
            "", "RESULTS",
            f"- CHP {d.electric_power_kw:,.0f} kW electric; substrate {d.mass_t_per_year:,.0f} t/year;"
            f" biogas {d.biogas_m3_per_year:,.0f} Nm3/year ({d.ch4_fraction:.0%} CH4)",
            f"- Digester {d.digester_volume_m3:,.0f} m3 (working {d.working_volume_m3:,.0f} m3), "
            f"OLR {d.olr_kg_vs_per_m3_day:.2f} kg VS/(m3 d); crop land {d.crop_hectares:,.0f} ha; "
            f"digestate {d.digestate_t_per_year:,.0f} t/year",
            f"- Useful heat {d.heat_useful_kwh:,.0f} kWh/year after digester heating of "
            f"{d.heat_digester_kwh:,.0f} kWh",
        ]
    else:
        lines += [
            f"- Heat demand {inp.annual_heat_demand_kwh:,.0f} kWh/year, peak {inp.peak_heat_kw:,.0f} "
            f"kW, coverage {inp.coverage:.0%}",
            f"- Fuel: {inp.fuel.name}, LHV dry {inp.fuel.lhv_dry_kwh_per_kg:.2f} kWh/kg, bulk "
            f"{inp.fuel.bulk_density_kg_m3:.0f} kg/m3",
            f"- Efficiencies: thermal {inp.eta_th:.2f}, electrical {inp.eta_el:.2f}; storage "
            f"{inp.storage_days:.0f} days",
            "", "RESULTS",
            f"- Load factor {d.load_factor:.2f}; plant {d.thermal_power_kw:,.0f} kW thermal"
            + (f", {d.electric_power_kw:,.0f} kW electric" if inp.eta_el > 0 else "")
            + f" ({d.power_ratio:.0%} of the peak); {d.full_load_hours:,.0f} full-load hours",
            f"- Fuel {d.mass_t_per_year:,.0f} t/year (LHV {d.lhv_as_received_kwh_per_kg:.2f} "
            f"kWh/kg), storage {d.storage_m3:,.0f} m3, {d.deliveries_per_year} truck loads, "
            f"ash {d.ash_t_per_year:.1f} t",
        ]
    lines += [f"- CO2 avoided {d.co2_avoided_t_per_year:,.0f} t/year", "", "DESIGN CHECKS"]
    lines += [f"- [{_SEVERITY[f.severity]}] {f.message}" for f in findings] or ["- (none)"]
    return "\n".join(lines)
