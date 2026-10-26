"""'Why?' texts of the geothermal module (merged into ``EXPLANATIONS``)."""

from __future__ import annotations

GEOTHERMAL_EXPLANATIONS: dict[str, dict[str, str]] = {
    "geo.heat_power": {
        "title": "Heat from the brine",
        "formula": "P_th = m * cp * (T_prod - T_return) * eta_hx",
        "why": (
            "A geothermal doublet pumps hot water from a production well, takes its heat in a "
            "heat exchanger and sends the cooled water back down an injection well. The heat "
            "is the flow m times the specific heat of water cp (4.18 kJ/kg per kelvin) times "
            "the temperature drop. The lower the return temperature, the more heat you take "
            "from every kilogram: that is why a heat network with low return temperatures "
            "(40-50 degC) suits geothermal heat so well. The exchanger and the network lose a "
            "few percent, here eta_hx."
        ),
        "assumptions": (
            "Constant flow and temperature; the production temperature does not fall during "
            "the life of the doublet (in reality the cold front from the injection well reaches "
            "the production well after some decades). Liquid water with a constant cp."
        ),
        "reference": "Lund and Toth (2021), direct use of geothermal energy; DiPippo (2016).",
    },
    "geo.coverage": {
        "title": "How much of the heat a doublet covers",
        "formula": "f(x) = (n + 1) * x - n * x^((n + 1) / n);    x = n_doublets * P_pair / P_peak",
        "why": (
            "A district's heat demand is high for a few cold days and low for most of the "
            "year, so sizing the geothermal plant on the peak would waste it. The wells give "
            "a nearly constant power day and night and in summer: they work as base load. "
            "RESize uses the same load-duration curve as the biomass boiler: the function f "
            "gives the share of the yearly heat that a plant of x times the peak power covers. "
            "A plant of 60-80 % of the peak usually covers 85-95 % of the heat; a gas boiler "
            "takes the peaks. Wells are added one pair at a time, so the power comes in steps."
        ),
        "assumptions": (
            "Power-law load-duration curve built from the peak and the yearly demand, a plant "
            "that can modulate down to zero (in practice the pump has a minimum flow) and a "
            "buffer tank that is not modelled. Use hourly data for a detailed design."
        ),
        "reference": "Quaschning (2013); same curve as the biomass module.",
    },
    "geo.wells": {
        "title": "Depth and cost of the wells",
        "formula": "z = (T_prod - T_surface) / gradient;    well cost = z * cost per metre",
        "why": (
            "The rock gets hotter with depth: in a normal crust by about 30 degC per "
            "kilometre. To find water at the temperature you need you must go down to the "
            "depth z. Drilling is the main cost of geothermal energy, and it grows faster than "
            "the depth because deeper wells need more casing strings and more time: in the "
            "values of the MIT study a 3 km well cost about 4 million dollars (2004) and a 6 km "
            "one more than twice that. In areas with a volcanic or tectonic anomaly the "
            "gradient is higher, wells are shallower and the heat is much cheaper."
        ),
        "assumptions": (
            "One average gradient and one cost per metre for any depth (the cost really grows "
            "with depth); the cost is for a successful well, without exploration, failed "
            "wells, stimulation or financing. The doublet needs two wells."
        ),
        "reference": "MIT (2006), chapter 6, drilling technology and costs.",
    },
    "geo.pumping": {
        "title": "Pumping electricity",
        "formula": "P_pump = (m / rho) * Delta_p / eta_pump;    SPF = heat delivered / pump electricity",
        "why": (
            "The brine is moved by a production pump (the water does not always rise by "
            "itself) and, often, an injection pump. The hydraulic power is the volume flow "
            "m / rho times the pressure rise, and the motor spends more than that because of "
            "the pump efficiency. A good doublet delivers tens of units of heat for every unit of "
            "pumping electricity (the seasonal performance factor, SPF), far more than a heat "
            "pump (3-5); with a poorly permeable reservoir or a very salty brine it falls."
        ),
        "assumptions": (
            "One total pressure rise for the well pair, taken as typical; the real value "
            "depends on the productivity of the wells, the depth of the pump and the pipes. "
            "The pump follows the load (variable speed): its energy is proportional to the "
            "heat delivered."
        ),
        "reference": "DiPippo (2016), well flow and pumping; RESize's typical values.",
    },
    "geo.exergy": {
        "title": "Exergy: the part of the heat that can become work",
        "formula": "e = cp * ((T - T0) - T0 * ln(T / T0))     [temperatures in kelvin]",
        "why": (
            "Not all the heat of the brine can be turned into electricity: a heat engine must "
            "reject part of it to the environment. The exergy is the maximum useful work that "
            "a kilogram of brine could give if the plant were ideal, with the surroundings at "
            "the ambient temperature T0. It grows quickly with temperature: brine at 200 degC "
            "carries about 176 kJ/kg of exergy and at 100 degC only about 44 kJ/kg, four times "
            "less, which is why hot reservoirs are so much more valuable for power."
        ),
        "assumptions": (
            "Liquid water with a constant cp, an ambient temperature that is the yearly "
            "mean (the real output changes between a cold night and a hot afternoon, "
            "especially with air-cooled condensers)."
        ),
        "reference": "DiPippo (2016), exergy and utilization efficiency; MIT (2006), chapter 7.",
    },
    "geo.binary": {
        "title": "Binary plant: electricity from a medium-temperature brine",
        "formula": "eta = 0.09345 * T - 2.32657  [%, T in degC];    "
                   "P_gross = eta * m * cp * (T - T_reinjection)",
        "why": (
            "Below about 180 degC the brine does not boil enough to run a turbine directly. "
            "A binary plant keeps the brine in a closed loop: it heats a second fluid, an "
            "organic one with a low boiling point, which expands in the turbine. The "
            "efficiency of the cycle depends mainly on the brine temperature, rising from "
            "about 7 % at 100 degC to 13 % at 160 degC. In RESize the efficiency comes from "
            "a fit of ten operating plants (MIT 2006): P_gross is the heat taken from the "
            "brine, down to the reinjection temperature, times that efficiency. The brine is "
            "not cooled too much, because silica could precipitate and plug the wells."
        ),
        "assumptions": (
            "The fit is based on plants with brine between 103 and 166 degC; outside this range "
            "it is an extrapolation. It is defined with the net power of the cycle: the well "
            "pumps are subtracted separately. The reinjection temperature is a typical value: "
            "take the one allowed by the chemistry of your brine."
        ),
        "reference": "MIT (2006), chapter 7, figure 7.2 and table 7.2; DiPippo (2016), binary plants.",
    },
    "geo.flash": {
        "title": "Flash plant: electricity from a hot brine",
        "formula": "P_gross = eta_u * m * e;    P_net = P_gross * (1 - parasitic) - P_pump",
        "why": (
            "At 180-200 degC and above, part of the brine boils when its pressure is lowered "
            "in a separator: the steam goes to a turbine and the water is reinjected. The "
            "utilization efficiency eta_u is the share of the exergy of the brine that becomes "
            "power. For a single-flash plant at 200 degC it is about 31 % (MIT 2006); a "
            "double-flash plant at 250 degC reaches 46 %. The plant also uses part of its own "
            "power for the cooling tower fans and pumps (5 % of the gross power)."
        ),
        "assumptions": (
            "One flash, a utilization efficiency taken from a 200 degC plant (editable) and "
            "no change with the temperature. The gases that come with the steam are not "
            "considered: they are emitted (mostly CO2) unless they are reinjected."
        ),
        "reference": "MIT (2006), chapter 7, section 7.2.2 and table 7.5; DiPippo (2016).",
    },
    "geo.net_power": {
        "title": "Net power and number of wells",
        "formula": "P_net,pair = P_gross - P_plant - P_pump;    n = ceil(coverage * E_demand / "
                   "(P_net,pair * h))",
        "why": (
            "What the grid sees is the net power: the gross power of the turbine minus what the "
            "plant itself uses for its own auxiliaries and for the pumps. One pair of wells "
            "(a production and an injection well) gives a fixed net power, so the number of "
            "pairs is the demand you want to cover divided by the energy of one pair in a year, "
            "rounded up. Geothermal plants run almost all year (7500-8000 hours), so the "
            "energy is the net power times the operating hours. Because wells come in whole "
            "pairs, the plant usually covers a little more or less than the target."
        ),
        "assumptions": (
            "All wells are equal, with the same flow and temperature; no interference between "
            "wells; the decline of the reservoir is not modelled. The operating hours are an "
            "input (default 7900 h): check them with plants of the same type."
        ),
        "reference": "DiPippo (2016); MIT (2006), chapter 7.",
    },
    "geo.economics": {
        "title": "Cost of the plant and of the energy",
        "formula": "LCOE = (CAPEX * CRF + O&M + pumping) / E;    NPV = -CAPEX + net benefit * annuity factor",
        "why": (
            "A geothermal plant is a capital-intensive one: most of the money is spent before "
            "the first kilowatt-hour, on exploration, wells and plant, and the fuel is free. "
            "For a power plant RESize uses a cost per kW of net power that includes the wells; "
            "for heat it adds up the wells (two per doublet, depth times cost per metre) and "
            "the surface equipment. The levelised cost spreads the capital over the life with "
            "the capital recovery factor and adds the O&M and the pumping electricity; "
            "dividing by the energy gives the price at which the plant just pays for itself. "
            "Compare it with the price of the heat or electricity you replace."
        ),
        "assumptions": (
            "Constant prices, one discount rate, no incentives or taxes, no cost of exploration "
            "or of the dry or failed wells (the main risk of geothermal energy). The cost "
            "per kW of the power plant is a literature value for the USA; the cost per "
            "metre is a value of 2004 and has not been updated for inflation."
        ),
        "reference": "NREL ATB 2024, geothermal; MIT (2006), chapter 6.",
    },
    "geo.co2": {
        "title": "Carbon avoided",
        "formula": "CO2 = E_heat / eta_ref * EF_fuel - E_pump * EF_grid      (heat);    "
                   "CO2 = E * (EF_grid - EF_plant) / 1000      (power)",
        "why": (
            "Geothermal heat replaces the fuel of the boiler it displaces (natural gas here), "
            "including the boiler's efficiency; the pumps use grid electricity, which is "
            "subtracted. Geothermal electricity replaces grid electricity, minus the emissions "
            "of building the plant (about 38 g per kWh as a median in the published "
            "life-cycle studies). Direct emissions of gases dissolved in the brine can be "
            "important in flash plants and are not included: check the field."
        ),
        "assumptions": (
            "One average emission factor for the grid and for the natural gas; for heat, the "
            "emissions of building the plant are not included."
        ),
        "reference": "IPCC AR5, Annex III (life-cycle emissions); national grid factor (ISPRA).",
    },
}

HEAT_TOPIC_ORDER: tuple[str, ...] = (
    "geo.heat_power", "geo.coverage", "geo.wells", "geo.pumping", "geo.economics", "geo.co2",
)
POWER_TOPIC_ORDER: tuple[str, ...] = (
    "geo.exergy", "geo.binary", "geo.flash", "geo.net_power", "geo.wells", "geo.economics",
    "geo.co2",
)
GEOTHERMAL_TOPIC_ORDER: tuple[str, ...] = tuple(dict.fromkeys(HEAT_TOPIC_ORDER + POWER_TOPIC_ORDER))


def topics_for(pathway: str) -> tuple[str, ...]:
    """The 'Why?' topics that apply to a pathway."""
    return POWER_TOPIC_ORDER if pathway == "power" else HEAT_TOPIC_ORDER
