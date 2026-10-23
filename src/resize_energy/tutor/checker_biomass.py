"""Sanity checks of a biomass design (deterministic, offline)."""

from __future__ import annotations

from resize_energy.core.biomass_design import BiomassDesign, BiomassInputs
from resize_energy.tutor.checker import Finding


def check_biomass_design(inp: BiomassInputs, d: BiomassDesign) -> list[Finding]:
    out: list[Finding] = []
    if d.pathway == "biogas":
        out += _check_biogas(inp, d)
    else:
        out += _check_solid(inp, d)
    out.append(Finding(
        "info", "annual_balance",
        "Annual and average values only: no hourly profile, part-load efficiency, buffer tank "
        "or seasonal storage is modelled.", None))
    if not any(f.severity in ("warning", "error") for f in out):
        out.insert(0, Finding("ok", "design_ok", "No problem found with the main design rules.",
                              None))
    return out


def _check_solid(inp: BiomassInputs, d: BiomassDesign) -> list[Finding]:
    out: list[Finding] = []
    m = inp.fuel.moisture_wb
    if m > 0.45:
        out.append(Finding(
            "warning", "moisture_high",
            f"Moisture of {m:.0%} is high: the heating value falls to "
            f"{d.lhv_as_received_kwh_per_kg:.1f} kWh/kg and combustion becomes unstable. Dry the "
            "fuel or choose a boiler designed for wet fuel.", "biomass.lhv"))
    if d.load_factor < 0.15:
        out.append(Finding(
            "warning", "load_factor_low",
            f"Load factor {d.load_factor:.2f}: the demand is very peaked, so a plant sized for "
            "the peak would idle most of the year. Check the peak load and consider a buffer tank.",
            "biomass.load_duration"))
    if inp.coverage > 0.95:
        out.append(Finding(
            "warning", "coverage_high",
            f"Covering {inp.coverage:.0%} of the heat needs a plant of {d.power_ratio:.0%} of "
            "the peak: it would run at low load for most of the year. 70-90 % with a backup "
            "boiler for the peaks is the usual compromise.", "biomass.load_duration"))
    low = 5000 if inp.pathway == "orc" else 2000
    if d.full_load_hours < low:
        out.append(Finding(
            "warning", "full_load_hours",
            f"Only {d.full_load_hours:,.0f} full-load hours per year (a "
            f"{'cogeneration' if inp.pathway == 'orc' else 'biomass boiler'} should reach more "
            f"than {low:,}): the investment is hard to repay.", "biomass.plant_power"))
    if inp.storage_days < 3:
        out.append(Finding(
            "warning", "storage_short",
            f"Fuel autonomy of {inp.storage_days:.0f} days is short: a delayed delivery in winter "
            "stops the plant. 7-14 days is common.", "biomass.storage"))
    out.append(Finding(
        "info", "supply",
        f"Fuel supply: {d.mass_t_per_year:,.0f} t per year, {d.deliveries_per_year} truck loads, "
        f"{d.ash_t_per_year:.1f} t of ash to dispose of.", "biomass.fuel_mass"))
    if inp.pathway == "orc" and d.electricity_coverage > 1.0:
        out.append(Finding(
            "info", "electricity_surplus",
            f"The plant makes {d.electricity_coverage:.0%} of the electricity demand: the "
            "surplus is exported.", "biomass.plant_power"))
    return out


def _check_biogas(inp: BiomassInputs, d: BiomassDesign) -> list[Finding]:
    out: list[Finding] = []
    if inp.hrt_days < 20:
        out.append(Finding(
            "error", "hrt_low",
            f"Retention time of {inp.hrt_days:.0f} days is too short: the bacteria are washed "
            "out and the methane yield drops. Use 30-60 days.", "biomass.digester"))
    elif inp.hrt_days < 30:
        out.append(Finding(
            "warning", "hrt_short",
            f"Retention time of {inp.hrt_days:.0f} days is short for a mesophilic plant "
            "(30-60 days).", "biomass.digester"))
    if d.olr_kg_vs_per_m3_day > 5.0:
        out.append(Finding(
            "error", "olr_high",
            f"Organic loading rate {d.olr_kg_vs_per_m3_day:.1f} kg VS/(m3 d) is above the "
            "stable range: risk of acidification. Increase the retention time or the manure "
            "share.", "biomass.olr"))
    elif d.olr_kg_vs_per_m3_day > 4.0:
        out.append(Finding(
            "warning", "olr_close",
            f"Organic loading rate {d.olr_kg_vs_per_m3_day:.1f} kg VS/(m3 d) is close to the "
            "limit (about 4.5): the plant would need careful operation.", "biomass.olr"))
    elif d.olr_kg_vs_per_m3_day < 1.0:
        out.append(Finding(
            "info", "olr_low",
            f"Organic loading rate {d.olr_kg_vs_per_m3_day:.1f} kg VS/(m3 d) is low: the "
            "digester volume is used poorly, mostly because of dilute slurry.", "biomass.olr"))
    if inp.operating_hours < 7000:
        out.append(Finding(
            "warning", "chp_hours",
            f"{inp.operating_hours:,.0f} CHP hours per year is low: biogas is produced all year, "
            "so the engine should run 7500-8500 h or the gas would be stored or flared.",
            "biomass.chp_biogas"))
    if d.crop_hectares > 0:
        out.append(Finding(
            "info", "crop_land",
            f"The energy crops need about {d.crop_hectares:,.0f} ha per year; check that the "
            "land is available close to the plant and that the crops meet sustainability rules.",
            "biomass.land"))
    q = inp.annual_heat_demand_kwh
    if q > 0 and d.heat_useful_kwh < 0.5 * q:
        out.append(Finding(
            "info", "heat_short",
            f"The useful heat covers {d.heat_useful_kwh / q:.0%} of the heat demand: the rest "
            "needs another source.", "biomass.heat_balance"))
    elif q > 0 and d.heat_useful_kwh > q:
        out.append(Finding(
            "info", "heat_surplus",
            "The plant makes more useful heat than the demand: the surplus is wasted unless "
            "there is another user (drying, a heat network).", "biomass.heat_balance"))
    return out
