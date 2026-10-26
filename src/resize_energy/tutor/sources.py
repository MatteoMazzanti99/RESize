"""Which publications stand behind each 'Why?' topic (no Qt needed).

For every topic: where the *formula* comes from, where the *typical values and assumptions* come
from, and, honestly, what is a modelling choice of RESize with no external source. A reference is
written ``key|where`` (``where`` is a chapter or a short note) and looked up in
:mod:`resize_energy.tutor.bibliography`.
"""

from __future__ import annotations

from html import escape

from resize_energy.tutor.bibliography import REFS, full_citation
from resize_energy.tutor.cost_sources import cost_keys

# topic: (formula, values and assumptions, RESize's own choice)
_RAW: dict[str, tuple[str, str, str]] = {
    # --- photovoltaic -------------------------------------------------------------------------
    "pv.irradiation": ("duffie2013|ch. 1-2", "pvgis|PVcalc tool; huld2012|PVGIS database; suri2007|PVGIS method", ""),
    "pv.performance_ratio": ("iec61724|definition of PR",
                             "reich2012|typical PR range; jordan2013|degradation, median about 0.5 %/year (not modelled)", ""),
    "pv.required_peak_power": ("masters2013|PV system sizing; quaschning2013", "reich2012|typical PR", ""),
    "pv.temperature_extremes": ("iec62548|voltage at minimum temperature", "skoplaki2009|temperature coefficients", ""),
    "pv.max_modules_per_string": ("iec62548; masters2013", "skoplaki2009|temperature coefficients; luque2011|module behaviour with temperature", ""),
    "pv.min_modules_per_string": ("masters2013", "faiman2008|cell temperature above ambient; skoplaki2009", ""),
    "pv.mppt_window_cold": ("iec62548; masters2013", "skoplaki2009|temperature coefficient of Vmp", ""),
    "pv.string_layout": ("masters2013", "", "All strings equal and equally oriented: a simplification of RESize."),
    "pv.dc_ac_ratio": ("masters2013", "mondol2006|optimal DC/AC ratio", ""),
    "pv.annual_energy": ("masters2013; huld2012", "", "Yearly energy balance only: use and export are not simulated."),
    "pv.shading": ("quaschning1996", "duffie2013|sun position", "Flat obstacle band and a fixed diffuse share of 35 %: a RESize simplification."),
    "pv.monthly": ("duffie2013", "huld2012|PVGIS monthly outputs", "The monthly shape is typical of the latitude, not a measured year."),
    "pv.battery": ("luthander2015", "", "Typical home load shape and an invented production year: RESize defaults."),
    "pv.economics": ("short1995", "fraunhofer2024|cost ranges; iea_pvps_italy2024|Italian prices; nrel_atb2024", ""),
    "pv.sensitivity": ("saltelli2008|ch. 2", "", "One input at a time, +/-20 %: a RESize choice."),
    # --- wind ---------------------------------------------------------------------------------
    "wind.resource": ("burton2011; iec61400_12", "gwa|Global Wind Atlas; nasa_power|WS50M", ""),
    "wind.weibull": ("burton2011|ch. 2; justus1978; manwell2009", "burton2011|k = 2 as a common fit (Rayleigh)", ""),
    "wind.shear": ("burton2011; iec61400_1|normal wind profile", "", ""),
    "wind.air_density": ("iso2533; iec61400_12|density normalisation", "", ""),
    "wind.power_curve": ("iec61400_12", "nrel_turbines|tabulated power curves", "The generic curve is a smooth shape built from rated power and speeds."),
    "wind.cp_betz": ("betz1926; burton2011|ch. 3", "", ""),
    "wind.annual_energy": ("burton2011; iec61400_12|annual energy production", "", ""),
    "wind.losses": ("burton2011", "burton2011; ewea2009|typical availability and loss figures", "Two single numbers: a simplification of RESize."),
    "wind.capacity_factor": ("manwell2009", "irena_costs|capacity factors of new wind plants", ""),
    "wind.number_of_turbines": ("", "", "Identical turbines in a regular layout: a simplification of RESize."),
    "wind.spacing": ("burton2011|ch. 8; manwell2009", "", "Regular rectangular layout."),
    "wind.wake": ("jensen1983; katic1986", "burton2011|typical wake decay constant", "Generic thrust curve and one wind-speed distribution for all directions: RESize simplifications."),
    "wind.rose": ("burton2011|ch. 8", "nasa_power|WS50M and WD50M, hourly; gwa|wind roses", "Twelve sectors of 30 degrees; one speed distribution shape (Weibull k) for every sector, scaled by the mean speed of the sector."),
    "wind.layout": ("mosetti1994; kirkpatrick1983; jensen1983", "", "Surrogate of the wake loss (fixed thrust coefficient, power as the cube of the speed) used for the search, then the full model for the result; the area is a rectangle without exclusion zones, roads or terrain: RESize simplifications."),
    "wind.economics": ("short1995", "fraunhofer2024|cost ranges", ""),
    "wind.sensitivity": ("saltelli2008|ch. 2", "", "One input at a time, +/-20 %: a RESize choice."),
    # --- economics common to the comparison -----------------------------------------------------
    "econ.same_demand": ("iea_projected|methodology", "", "Annual balance only."),
    "econ.crf": ("short1995", "", "One discount rate for all technologies, constant prices."),
    "econ.lcoe": ("iea_projected; irena_costs", "fraunhofer2024|cost ranges", ""),
    "econ.savings": ("short1995", "", "Net-metering style balance: energy up to the demand is valued at the retail price."),
    "econ.payback": ("short1995", "", "Constant yearly benefit, no replacements."),
    "econ.co2": ("ipcc_ar5_annex3|life-cycle emissions of electricity supply", "ipcc_ar5_annex3|life-cycle factors; ispra|national grid factor", ""),
    "econ.sensitivity": ("saltelli2008; iea_projected", "", "Capital costs scaled together: a RESize choice."),
    # --- biomass ------------------------------------------------------------------------------
    "biomass.lhv": ("iso17225; obernberger2010", "obernberger2010|typical fuel values; mckendry2002|fuel properties", ""),
    "biomass.load_duration": ("quaschning2013; en15316", "", "Power-law shape of the duration curve: a RESize simplification."),
    "biomass.plant_power": ("obernberger2010", "", "Constant efficiencies at every load."),
    "biomass.fuel_mass": ("iso17225|moisture and heating value", "", "Energy balance with the nominal efficiency."),
    "biomass.storage": ("", "", "Design rule of RESize (usable volume of the silo, autonomy in days); check local practice."),
    "biomass.biogas_yield": ("fnr; ktbl2013", "ktbl2013|typical substrate yields; fnr", "Linear mixing of substrates."),
    "biomass.chp_biogas": ("fnr", "fnr|typical gas-engine efficiencies", ""),
    "biomass.digester": ("fnr", "fnr|retention time", "Density of the slurry 1 t/m3; one stirred digester."),
    "biomass.olr": ("fnr; weiland2010", "fnr|typical loading rates", ""),
    "biomass.heat_balance": ("fnr", "fnr|heat demand of the digester", "A fixed share of the heat is used by the digester."),
    "biomass.land": ("fnr", "ktbl2013|typical crop yields; red3|sustainability criteria", ""),
    "biomass.co2": ("ipcc2006; red3", "ipcc2006|emission factors", "Biogenic CO2 counted as neutral; one average grid factor."),
    # --- hydrogen -----------------------------------------------------------------------------
    "hydrogen.efficiency": ("nist_webbook|heating values of hydrogen; carmo2013", "irena_h2_2020|specific consumption; iea_ghr; schmidt2017", ""),
    "hydrogen.dispatch": ("buttler2018", "buttler2018|minimum load of electrolysers", "The dispatch rules (renewables first, minimum load, grid top-up) are a RESize choice."),
    "hydrogen.sizing": ("irena_h2_2020", "irena_h2_2020|costs and efficiency", "Linear scaling with size."),
    "hydrogen.compression": ("gardiner2009", "gardiner2009|compression energy", "Ideal-gas work with a fixed efficiency."),
    "hydrogen.storage": ("nist_webbook|properties of hydrogen", "", "Storage sized on average daily production times the days chosen."),
    "hydrogen.water": ("irena_h2_policy", "irena_h2_policy|water consumption", ""),
    "hydrogen.stack": ("iea_future_h2", "iea_future_h2; schmidt2017|stack life; buttler2018", "Wear proportional to full-load hours."),
    "hydrogen.lcoh": ("iea_ghr; irena_h2_2020", "irena_h2_2020|cost ranges", "The whole renewable plant is charged to the hydrogen."),
    "hydrogen.co2": ("rfnbo2023|methodology; ipcc_ar5_annex3", "ipcc_ar5_annex3|life-cycle factors", "Average grid factor as a placeholder."),
    "hydrogen.partload": ("buttler2018; brauns2020; ulleberg2003|efficiency model of an electrolyser", "", "A smooth two-parameter curve, not the polarisation curve of a stack."),
    "hydrogen.ageing": ("frensch2019", "frensch2019|degradation rates; schmidt2017", "Linear drift, replacement at the stack life you set."),
    "hydrogen.tank": ("h2council2020", "", "Constant offtake all year, no losses: a RESize simplification."),
    "hydrogen.prices": ("entsoe|day-ahead prices; armijo2020", "entsoe", "Without real prices an invented year with the usual shape is used."),
    "hydrogen.sensitivity": ("saltelli2008; iea_projected", "", "One input at a time: a RESize choice."),
    # --- battery ------------------------------------------------------------------------------
    "battery.selfuse": ("luthander2015", "", "Hourly values: peaks inside one hour are not seen."),
    "battery.load": ("vdew1999|standard load profiles", "vdew1999", "A typical shape of the type chosen, not your consumption."),
    "battery.dispatch": ("weniger2014", "", "No grid charging, no peak shaving, no forecast."),
    "battery.capacity": ("irena_storage2017", "irena_storage2017", ""),
    "battery.efficiency": ("schimpe2018", "schimpe2018|efficiency and ageing of LFP cells", "Constant efficiency at any power and temperature."),
    "battery.diminishing": ("hoppmann2014", "", ""),
    "battery.life": ("wang2011", "wang2011|cycle life of LFP cells", "End of life taken at 70-80 % of the initial capacity."),
    "battery.economics": ("short1995", "fraunhofer2024|battery costs; cole2023|US utility-scale costs", "Constant prices over the life."),
    "battery.lcos": ("schmidt2019; lazard", "lazard|cost ranges", ""),
    "battery.co2": ("peters2017", "peters2017|embodied emissions of Li-ion batteries", "Embodied carbon of the battery is not counted."),
    "battery.sensitivity": ("saltelli2008; iea_projected", "", "One input at a time: a RESize choice."),
    # --- solar thermal and cooling ------------------------------------------------------------
    "solar.resource": ("duffie2013|ch. 1-2", "", "An invented year with the right totals, not measured data."),
    "solar.collector": ("iso9806; hottel1958; bliss1959; duffie2013|ch. 6", "iso9806|test coefficients", "Steady state, constant coefficients."),
    "solar.load": ("en15316; ashrae|service water heating", "ashrae|typical demand", "The same litres every day of the year."),
    "solar.store": ("duffie2013|ch. 10", "iea_shc|Task 32, storage", "Fully mixed tank; heat loss UA = 0.16 x sqrt(V): a RESize rule."),
    "solar.simulation": ("duffie2013|ch. 12", "", "Hourly steps; pipe and pump losses as one percentage."),
    "solar.solar_fraction": ("klein1979", "", "Yearly value from the hourly simulation."),
    "solar.area": ("duffie2013", "weiss2024; iea_shc|Task 26", ""),
    "solar.stagnation": ("iso9806|stagnation", "iea_shc|Task 44", "Counted as hours with the store at 95 degC."),
    "solar.adsorption": ("henning2007", "iea_shc|Task 38", ""),
    "solar.chiller_cop": ("henning2007|ch. 4", "henning2007", "COP linear between minimum and nominal drive temperature."),
    "solar.chillers": ("henning2007", "iea_shc|Task 53", "Typical catalogue values for each family."),
    "solar.economics": ("short1995", "mugnier2018|installed prices of small systems; weiss2024|market overview", ""),
    "solar.co2": ("ipcc_ar5_annex3", "ipcc_ar5_annex3|life-cycle factors; ispra|national grid factor", "Emissions of making the collectors are not counted."),
    "solar.sensitivity": ("saltelli2008", "", "One input at a time, +/-20 %."),
    # --- hydropower ---------------------------------------------------------------------------
    "hydro.fdc": ("vogel1994", "esha2004|hydrology", "A log-normal curve fixed by the mean flow and Q95: a RESize simplification."),
    "hydro.eco_flow": ("", "tennant1976|10 % and 30 % of the mean flow; wfd2000", "A constant flow all year: a RESize simplification."),
    "hydro.design_flow": ("esha2004|ch. 3; paish2002", "", "A cost proportional to the rated power: a RESize simplification."),
    "hydro.power": ("esha2004|ch. 3 and 6", "esha2004|tables 6.7 and 6.8; paish2002", ""),
    "hydro.penstock": ("white2016|pipe flow; swamee1976", "esha2004|ch. 5", "One pipe of constant diameter; water hammer is not checked."),
    "hydro.turbine": ("esha2004|section 6.2", "esha2004|tables 6.3 and 6.7; paish2002", "The flow rules that choose between overlapping types, and the crossflow figures, are RESize's own."),
    "hydro.energy": ("esha2004|ch. 3", "nrel_atb2024_hydro|capacity factors of run-of-river plants", "Operating losses of 5 %: a RESize choice."),
    "hydro.economics": ("short1995; iea_projected|methodology", "nrel_atb2024_hydro|costs of new stream-reach development", ""),
    "hydro.co2": ("ipcc_ar5_annex3|life-cycle emissions of electricity supply", "ipcc_ar5_annex3|hydropower, median value; ispra|national grid factor", ""),
    # --- geothermal ---------------------------------------------------------------------------
    "geo.heat_power": ("dipippo2016; lund2021", "lund2021|direct use", "Constant flow and temperature for the whole life."),
    "geo.coverage": ("quaschning2013; en15316", "", "Power-law shape of the duration curve; wells in whole pairs: RESize simplifications."),
    "geo.wells": ("mit2006|ch. 6", "mit2006|cost of wells against depth, 2004 dollars", "A single cost per metre for every depth: a RESize simplification."),
    "geo.pumping": ("white2016|pumps", "dipippo2016|well flow and pumping", "Typical pressure rise and pump efficiency: values of RESize."),
    "geo.exergy": ("dipippo2016|exergy of geofluids; mit2006|ch. 7", "", ""),
    "geo.binary": ("mit2006|ch. 7, fig. 7.2 and table 7.2; dipippo2016", "mit2006|ten operating binary plants, brine 103-166 degC", "The reinjection temperature is a typical value of RESize."),
    "geo.flash": ("mit2006|section 7.2.2, table 7.5; dipippo2016", "mit2006|utilization efficiency 31 % at 200 degC, parasitic load 5 %", "One utilization efficiency for every temperature."),
    "geo.net_power": ("dipippo2016; mit2006|ch. 7", "", "Identical wells, no decline of the reservoir; operating hours of RESize."),
    "geo.economics": ("short1995; iea_projected|methodology", "nrel_atb2024_geo|cost of hydrothermal plants; mit2006|ch. 6", "Surface cost of the heat, drilling cost and O&M are placeholders of RESize."),
    "geo.co2": ("ipcc_ar5_annex3|life-cycle emissions of electricity supply", "ipcc_ar5_annex3|geothermal, median value; ispra|national grid factor", ""),
}


def _parse(text: str) -> list[tuple[str, str]]:
    out = []
    for item in text.split(";"):
        item = item.strip()
        if item:
            key, _, note = item.partition("|")
            out.append((key.strip(), note.strip()))
    return out


SOURCES: dict[str, dict] = {
    topic: {"formula": _parse(f), "values": _parse(v), "own": own}
    for topic, (f, v, own) in _RAW.items()
}


def _cite(items: list[tuple[str, str]]) -> str:
    return "; ".join(escape(REFS[k].short) + (f", {escape(note)}" if note else "")
                     for k, note in items)


def cited_keys(topic: str) -> list[str]:
    entry = SOURCES.get(topic)
    if not entry:
        return []
    seen: list[str] = []
    for key, _note in entry["formula"] + entry["values"]:
        if key not in seen:
            seen.append(key)
    seen += [k for k in cost_keys(topic) if k not in seen]
    return seen


def sources_html(topic: str, full: bool = False) -> str:
    """The 'Sources' block of a topic; ``full`` also lists the complete references."""
    entry = SOURCES.get(topic)
    if not entry:
        return ""
    lines = []
    if entry["formula"]:
        lines.append(f"<b>Formula:</b> {_cite(entry['formula'])}.")
    if entry["values"]:
        lines.append(f"<b>Typical values and assumptions:</b> {_cite(entry['values'])}.")
    if entry["own"]:
        lines.append(f"<b>RESize's own choice (no external source):</b> {escape(entry['own'])}")
    if not lines:
        return ""
    keys = cited_keys(topic)
    out = "<p><b>Sources</b><br>" + "<br>".join(lines) + "</p>"
    if full and keys:
        out += ("<p><b>References</b><br>"
                + "<br>".join(full_citation(k) for k in sorted(keys, key=lambda k: REFS[k].short))
                + "</p>")
    out += f"<!--refs:{','.join(keys)}-->"
    return out


def references_html(html: str) -> str:
    """The 'References' section of a report: every publication cited in ``html``."""
    import re

    keys: set[str] = set()
    for chunk in re.findall(r"<!--refs:([^>]*?)-->", html):
        keys.update(k for k in chunk.split(",") if k in REFS)
    if not keys:
        return ""
    items = "".join(f"<li>{full_citation(k)}</li>"
                    for k in sorted(keys, key=lambda k: REFS[k].short.lower()))
    return (f"<h2>References</h2><ul>{items}</ul>"
            "<p><i>Standards and reports are revised: use the current edition when you cite them.</i></p>")
