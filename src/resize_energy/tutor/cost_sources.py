"""Where the default costs come from, and how they compare with the literature (no Qt needed).

For every component the app proposes a cost for, this lists the default, the range found in the
sources, and an honest verdict: inside the range, above, below, or no source found. The ranges
are quoted from the documents named in ``refs`` (currency and year as in the source: they are
orders of magnitude, not quotes for your project). ``tests/test_cost_sources.py`` checks that
the defaults written here are the ones in the program.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from resize_energy.tutor.bibliography import REFS


@dataclass(frozen=True)
class CostBasis:
    key: str
    component: str
    unit: str
    defaults: tuple[float, ...]       # every default the program uses for it
    literature: str                   # what the sources say
    refs: tuple[tuple[str, str], ...]  # (reference key, where in it)
    verdict: str                      # within, below, above, none
    comment: str = ""


_VERDICTS = {
    "within": "Default inside the range of the sources.",
    "below": "Default below the range of the sources.",
    "above": "Default above the range of the sources.",
    "none": "No source found: the default is a round placeholder of RESize.",
}

COSTS: dict[str, CostBasis] = {c.key: c for c in (
    CostBasis("pv_capex", "PV plant, installed", "euro per kWp", (1100.0, 1000.0),
              "Germany 2024: rooftop up to 30 kWp 1,000-2,000; rooftop above 30 kWp 900-1,600; "
              "ground-mounted above 1 MWp 700-900 euro/kWp. Italy 2024: residential rooftop "
              "1.20-1.60 euro/W.",
              (("fraunhofer2024", "Table 1"), ("iea_pvps_italy2024", "key figures")), "within"),
    CostBasis("pv_om", "PV operation and maintenance", "euro per kWp per year", (15.0,),
              "Germany 2024, fixed OPEX: small rooftop 26, large rooftop 21.5, utility-scale 13.3 "
              "euro/kW per year. USA 2022, utility-scale: 24 USD/kW(AC) per year.",
              (("fraunhofer2024", "Table 2"), ("nrel_atb2024", "fixed O&M")), "within",
              "Inside the range 13-26, towards the low end (large plants)."),
    CostBasis("pv_life", "PV plant life", "years", (30.0,),
              "Germany 2024 and USA 2022: 30 years.", (("fraunhofer2024", "Table 2"), ("nrel_atb2024", "lifetime")),
              "within"),
    CostBasis("wind_capex", "Onshore wind turbines, installed", "euro per kW", (1700.0, 1500.0),
              "Germany 2024: onshore wind 1,300-1,900 euro/kW.", (("fraunhofer2024", "Table 1"),),
              "within", "Small wind turbines cost much more per kW and are not in this range."),
    CostBasis("wind_om", "Wind operation and maintenance", "euro per kW per year", (45.0,),
              "Germany 2024, onshore: fixed 32 euro/kW per year plus 0.007 euro/kWh variable, "
              "which is about 47 euro/kW per year at a 25 % capacity factor (RESize's arithmetic).",
              (("fraunhofer2024", "Table 2"),), "within"),
    CostBasis("wind_life", "Wind plant life", "years", (25.0,), "Germany 2024: 25 years for onshore wind.",
              (("fraunhofer2024", "Table 2"),), "within"),
    CostBasis("bio_capex", "Biogas plant with CHP, installed", "euro per kW of electricity", (4500.0,),
              "Germany 2024: biogas 2,894-5,788 euro/kW; solid biomass 3,473-5,788 euro/kW.",
              (("fraunhofer2024", "Table 1"),), "within"),
    CostBasis("bio_om", "Biogas operation and maintenance", "euro per kW per year", (250.0,),
              "Germany 2024: fixed OPEX 4 % of the investment plus 0.004 euro/kWh variable, "
              "about 210 euro/kW per year for a 4,500 euro/kW plant at 8,000 hours (RESize's "
              "arithmetic).", (("fraunhofer2024", "Table 2"),), "within",
              "Same order of magnitude."),
    CostBasis("batt_kwh", "Lithium-ion battery, installed", "euro per kWh", (550.0,),
              "Germany 2024: home battery with a small PV plant 500-1,000; with a large rooftop "
              "plant 450-800; with a utility-scale plant 400-600 euro/kWh. USA 2022, 4-hour "
              "utility-scale system: 482 USD/kWh.",
              (("fraunhofer2024", "Table 1"), ("cole2023", "2022 base year")), "within"),
    CostBasis("batt_kw", "Battery power electronics", "euro per kW", (0.0,),
              "The sources price the whole system per kWh, inverter included: no separate cost per "
              "kW is added.", (("fraunhofer2024", "Table 1"),), "within"),
    CostBasis("batt_om", "Battery operation and maintenance", "percent of CAPEX per year", (2.0,),
              "Germany 2024: about 2 % of the battery investment for utility-scale systems.",
              (("fraunhofer2024", "Table 2"),), "within"),
    CostBasis("batt_life", "Battery calendar life", "years", (15.0,), "Germany 2024: 15 years for PV battery systems.",
              (("fraunhofer2024", "Table 2"),), "within"),
    CostBasis("h2_capex", "Electrolyser system, installed", "euro per kW", (1000.0,),
              "IRENA 2020, installed system above 10 MW: alkaline 500-1,000, PEM 700-1,400 USD/kW "
              "(2020 values).", (("irena_h2_2020", "Table ES1, p. 12"),), "within",
              "Inside the range (alkaline and PEM together: 500-1,400 USD/kW, 2020 values); a small "
              "plant can cost more, so use a quote."),
    CostBasis("h2_stack_hours", "Electrolyser stack life", "hours", (60000.0,),
              "Alkaline 60,000; PEM 50,000-80,000 hours (2020 values).",
              (("irena_h2_2020", "Table ES1, p. 12"),), "within"),
    CostBasis("h2_stack_share", "Stack replacement cost", "fraction of the electrolyser CAPEX", (0.40,),
              "From the same table: stack-only 270 (alkaline) and 400 (PEM) USD/kW against a "
              "system of 500-1,000 and 700-1,400 USD/kW: about 27-57 % (RESize's arithmetic).",
              (("irena_h2_2020", "Table ES1, p. 12"),), "within"),
    CostBasis("h2_kwh", "Electrolyser energy per kg of hydrogen", "kWh per kg", (55.0,),
              "System efficiency 2020: alkaline 50-78, PEM 50-83 kWh/kg.",
              (("irena_h2_2020", "Table ES1, p. 12"),), "within"),
    CostBasis("h2_om", "Electrolyser operation and maintenance", "fraction of CAPEX per year", (0.03,),
              "IRENA does not give O&M as a share of CAPEX.", (), "none"),
    CostBasis("h2_storage", "Compressed hydrogen storage", "euro per kg stored", (600.0,),
              "About 500 USD/kg (2010) rising to about 800 USD/kg (2013) for a 250 bar tank module "
              "(Hexagon Lincoln, a DOE project); currencies are not converted.",
              (("baldwin2014", "slides on cost"),), "within"),
    CostBasis("solar_flat", "Flat-plate solar collector, installed", "euro per m2 of aperture", (380.0,),
              "Germany, small systems: domestic hot water for one house 940 euro/m2 (average 5.2 m2), "
              "combi systems 680 euro/m2 (13.4 m2); about 800 euro/m2 over all surveyed countries "
              "and system types.", (("mugnier2018", "Fig. 1 and text"),), "within",
              "The sources give total system prices. The program adds tank and fixed costs to the "
              "collector: for 5 m2 and a 300 litre tank, (5 x 380 + 300 x 1.8 + 1500) / 5 is about "
              "790 euro/m2 (RESize's arithmetic)."),
    CostBasis("hydro_capex", "Run-of-river hydropower, installed", "euro per kW", (6600.0,),
              "USA, 2024 ATB: new stream-reach development 6,574-8,611 USD/kW; the eight reference "
              "plants on existing non-powered dams 3,045-20,043 USD/kW.",
              (("nrel_atb2024_hydro", "capital expenditure"),), "within",
              "Dollars are not converted. The cost changes by a factor of two or three with the "
              "site (intake, penstock, access, grid connection): ask for quotes."),
    CostBasis("hydro_om", "Hydropower operation and maintenance", "percent of CAPEX per year", (2.5,),
              "USA, 2024 ATB: the yearly O&M is the lesser of 227,000 x P^0.547 USD (P in MW) and "
              "2.5 % of the CAPEX.", (("nrel_atb2024_hydro", "fixed O&M"),), "within",
              "At the upper limit of the formula, for small plants."),
    CostBasis("hydro_life", "Hydropower plant life", "years", (40.0,),
              "The ATB gives no number for the technical lifetime.", (), "none",
              "A round placeholder: civil works last much longer, machines are refurbished."),
    CostBasis("geo_capex_el", "Geothermal power plant with wells, installed", "euro per kW of net power",
              (6300.0,),
              "USA, 2024 ATB, hydrothermal plants: flash (200 degC and above) 3,091-5,922 USD/kW, "
              "average 4,350; binary (150 to below 200 degC) average 9,483, representative plant "
              "6,349, lowest case 4,882 USD/kW.",
              (("nrel_atb2024_geo", "capital cost"),), "within",
              "Includes exploration, wells and plant. Dollars are not converted."),
    CostBasis("geo_life", "Geothermal plant life", "years", (30.0,),
              "USA, 2024 ATB: 30 years for the plant and the reservoir.",
              (("nrel_atb2024_geo", "lifetime"),), "within"),
    CostBasis("geo_om", "Geothermal operation and maintenance", "fraction of CAPEX per year", (0.03,),
              "The ATB page gives no O&M value in a form that can be quoted.", (), "none",
              "A round placeholder."),
    CostBasis("geo_drill", "Geothermal well, drilled and cased", "euro per metre", (1500.0,),
              "MIT study, 2004 US dollars: 2.3 million for 1,500 m, 4.0 million for 3,000 m, 6.7-8.3 "
              "million for 5,000 m, 9.2-12.3 million for 6,000 m, that is about 1,300-2,000 per metre.",
              (("mit2006", "chapter 6, table 6.1"),), "within",
              "2004 values, not updated for inflation: today's wells cost more."),
    CostBasis("geo_surface", "Surface equipment of a geothermal heat plant", "euro per kW of heat",
              (250.0,), "No document with numbers for the heat exchangers, pumps and network "
              "connection was found.", (), "none", "A round placeholder: replace it with a quote."),
    CostBasis("solar_other", "Evacuated-tube and unglazed collectors, storage tank, fixed costs, "
              "adsorption chiller", "euro per m2, per litre, euro, per kW", (520.0, 120.0, 1.8, 1500.0, 1100.0),
              "No document with numbers for these items was found.", (), "none",
              "Round placeholders: replace them with quotes."),
)}

# which costs are shown with each 'Why?' topic
TOPIC_COSTS: dict[str, tuple[str, ...]] = {
    "pv.economics": ("pv_capex", "pv_om", "pv_life"),
    "wind.economics": ("wind_capex", "wind_om", "wind_life"),
    "battery.economics": ("batt_kwh", "batt_kw", "batt_om", "batt_life"),
    "hydrogen.lcoh": ("h2_capex", "h2_om", "h2_stack_hours", "h2_stack_share", "pv_capex", "wind_capex"),
    "hydrogen.efficiency": ("h2_kwh",),
    "hydrogen.stack": ("h2_stack_hours", "h2_stack_share"),
    "hydrogen.storage": ("h2_storage",),
    "solar.economics": ("solar_flat", "solar_other"),
    "econ.lcoe": ("pv_capex", "wind_capex", "bio_capex", "h2_capex"),
    "hydro.economics": ("hydro_capex", "hydro_om", "hydro_life"),
    "geo.economics": ("geo_capex_el", "geo_drill", "geo_surface", "geo_om", "geo_life"),
    "geo.wells": ("geo_drill",),
}


def _number(value: float) -> str:
    return f"{value:,.3g}" if abs(value) < 10 else f"{value:,.0f}"


def cost_keys(topic: str) -> list[str]:
    """The references cited by the costs of a topic."""
    keys: list[str] = []
    for c in TOPIC_COSTS.get(topic, ()):
        keys += [k for k, _w in COSTS[c].refs if k not in keys]
    return keys


def costs_html(topic: str) -> str:
    """The 'Typical costs and where they come from' block of a topic (empty if it has none)."""
    names = TOPIC_COSTS.get(topic)
    if not names:
        return ""
    items = []
    for name in names:
        c = COSTS[name]
        defaults = " / ".join(_number(v) for v in c.defaults)
        cites = "; ".join(escape(REFS[k].short) + (f", {escape(w)}" if w else "") for k, w in c.refs)
        line = (f"<li><b>{escape(c.component)}</b>: default {defaults} {escape(c.unit)}. "
                f"{escape(c.literature)}")
        if cites:
            line += f" <i>Source: {cites}.</i>"
        line += f" <b>{escape(_VERDICTS[c.verdict])}</b>"
        if c.comment:
            line += f" {escape(c.comment)}"
        items.append(line + "</li>")
    return ("<p><b>Typical costs and where they come from</b></p><ul>" + "".join(items) + "</ul>"
            "<p><i>Orders of magnitude from the literature, not quotes: prices change every year "
            "and with the size and the country. Replace the defaults with your own quotes.</i></p>")
