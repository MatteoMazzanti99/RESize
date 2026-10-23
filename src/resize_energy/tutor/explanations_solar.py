"""'Why?' texts of the solar thermal module (hot water and adsorption cooling)."""

from __future__ import annotations

SOLAR_EXPLANATIONS: dict[str, dict[str, str]] = {
    "solar.resource": {
        "title": "Sun on the collector, and the air around it",
        "formula": "G(t) on the collector plane;  sum of G(t) over the year = H [kWh/m2]",
        "why": (
            "A collector turns the radiation that hits its own tilted surface into heat, so the "
            "number that matters is the yearly irradiation on that plane (PVGIS gives it for "
            "your tilt and orientation). The outside air temperature matters too: the hotter "
            "the water in the collector compared with the air, the more heat leaks away. RESize "
            "builds a typical year hour by hour with the shape of the sun at your latitude, "
            "random cloudy days, and a seasonal and daily temperature wave, and scales it to "
            "your yearly irradiation."
        ),
        "assumptions": (
            "An invented year, not measured data: the totals are right, the order of the cloudy "
            "days is not. Beam and diffuse light are not separated, and the incidence angle is "
            "folded into the collector's efficiency."
        ),
        "reference": "Duffie & Beckman, Solar Engineering of Thermal Processes, ch. 1-2.",
    },
    "solar.collector": {
        "title": "Collector efficiency",
        "formula": "eta = eta0 - a1 (Tm - Ta) / G - a2 (Tm - Ta)^2 / G",
        "why": (
            "Part of the light is lost before it heats the water (eta0, the efficiency with no "
            "temperature difference). The rest leaks to the air in proportion to how much "
            "hotter the collector is than the air (a1, a2), and weighs more when the sun is "
            "weak. So the same collector is excellent for warm water on a sunny day and poor "
            "for hot water on a grey winter day. Glazed flat plates have high eta0 but lose "
            "heat quickly; evacuated tubes start lower but keep their efficiency at high "
            "temperature, which is what you want to drive an adsorption chiller or make process "
            "heat. Unglazed collectors are cheap and fine only for lukewarm water (pools)."
        ),
        "assumptions": (
            "Steady state, constant coefficients, mean fluid temperature = store temperature "
            "plus half of the temperature rise in the collector. Take eta0, a1, a2 from the "
            "Solar Keymark certificate of the collector you will buy: the defaults are typical "
            "round numbers."
        ),
        "reference": "EN ISO 9806; Solar Keymark database; Duffie & Beckman, ch. 6.",
    },
    "solar.load": {
        "title": "The hot-water demand",
        "formula": "Q = V x 1.163 Wh/(L K) x (T_use - T_mains)",
        "why": (
            "The heat you need is the heat to bring the water you draw from the mains "
            "temperature to the temperature you use. The mains water is colder in winter, so "
            "the demand is larger exactly when the sun is weakest: this is the basic reason "
            "why solar thermal covers 100 % of the demand in summer and a small part in winter. "
            "The draw is spread over the day with morning and evening peaks."
        ),
        "assumptions": (
            "The same litres every day of the year and the same hourly shape (no holidays or "
            "weekends). 55-60 degC is a usual set point; a lower one saves energy, a higher one "
            "limits the risk of legionella."
        ),
        "reference": "EN 15316-3; ASHRAE Handbook, Service Water Heating.",
    },
    "solar.store": {
        "title": "The storage tank",
        "formula": "dT/dt = (Q_collector - Q_load - UA (T - T_room)) / (V x 1.163 Wh/(L K))",
        "why": (
            "The sun and the demand do not coincide, so the heat is stored in a tank of water. "
            "A bigger tank smooths the day and the cloudy spells and lets the collector work at "
            "a lower temperature (more efficient), but it loses more heat and costs more. A "
            "common rule is 50-80 litres per m2 of collector. The model treats the tank as one "
            "mixed volume: a real tank is stratified (hot on top), which is a little better."
        ),
        "assumptions": (
            "One temperature for the whole tank; heat loss UA = 0.16 x sqrt(V) W/K (a well "
            "insulated tank); the backup heater is outside the tank and only adds the missing "
            "heat."
        ),
        "reference": "IEA SHC Task 32, Advanced storage concepts; Duffie & Beckman, ch. 10.",
    },
    "solar.simulation": {
        "title": "Hour by hour: the energy balance",
        "formula": "T_store(t+1) = T_store(t) + (Q_col - Q_hot_water - Q_chiller - Q_loss) / C",
        "why": (
            "Averages hide the problem, so the plant is simulated for the 8,760 hours of the "
            "year. Each hour: the collector adds heat if the sun is strong enough; the hot-water "
            "draw takes heat from the tank (the part the sun cannot supply is made up by the "
            "backup); the chiller, if any, takes the heat it needs when the tank is hot enough; "
            "the tank loses a little heat to the room. If the tank reaches 95 degC the extra "
            "heat is thrown away (stagnation)."
        ),
        "assumptions": (
            "Hourly steps; a pipe and pump loss as a single percentage of the collector heat; "
            "no frost or boiling model; perfect control."
        ),
        "reference": "Klein et al., TRNSYS; Duffie & Beckman, ch. 12 (simulation of solar systems).",
    },
    "solar.solar_fraction": {
        "title": "Solar fraction",
        "formula": "f = solar heat delivered / heat demand",
        "why": (
            "The solar fraction is the share of the energy you need that comes from the sun "
            "instead of the boiler. Typical well-designed hot-water systems reach 50-70 % in "
            "central Europe and 70-90 % near the Mediterranean. It is never 100 %: in winter "
            "there is not enough sun, and sizing for 100 % in winter would overheat the system "
            "all summer. When there is cooling too, the cold is counted as the heat a "
            "boiler-driven chiller would need (cold / COP) so both loads can be added."
        ),
        "assumptions": "Yearly value from the hourly simulation, not a monthly or f-chart estimate.",
        "reference": "Klein & Beckman, f-chart method (1979); ISO 9488 for vocabulary.",
    },
    "solar.area": {
        "title": "How many square metres?",
        "formula": "useful energy per m2 = (heat + cold) / area, falling as the area grows",
        "why": (
            "The first square metres are used completely; the later ones produce heat when the "
            "tank is already hot or the demand already covered, so each extra m2 adds less. The "
            "chart shows the solar fraction rising and the energy per m2 falling as the area "
            "changes. The economic optimum is usually well below the area that gives the "
            "highest fraction: look for the knee of the curve, where the net present value is "
            "highest."
        ),
        "assumptions": (
            "Tank volume grows with the area (litres per m2 as chosen). The costs per m2 are "
            "constant, with no discount for larger plants."
        ),
        "reference": "IEA SHC Task 26, Solar Combisystems; Solar Heat Worldwide.",
    },
    "solar.stagnation": {
        "title": "Overheating and stagnation",
        "formula": "T_store > 95 degC  ->  the excess heat is dumped",
        "why": (
            "When the tank is full and the sun is still shining (summer, holidays, low demand) "
            "the collectors cannot give their heat away, the fluid heats up and, in the worst "
            "case, boils: this is stagnation. It damages the glycol, the pump and the collector "
            "and shortens the life of the plant. The hours at the limit and the heat wasted are "
            "a sign of oversizing; the fixes are a smaller field, a bigger tank, a summer heat "
            "sink (a pool, a cooling machine) or collectors with a self-limiting design."
        ),
        "assumptions": "Counted as hours in which the store hits 95 degC at the end of the hour.",
        "reference": "IEA SHC Task 44; Solar Keymark requirements on stagnation.",
    },
    "solar.adsorption": {
        "title": "Cooling with heat: the adsorption chiller",
        "formula": "heat in -> cold out: Q_cold = COP x Q_heat",
        "why": (
            "An adsorption chiller makes chilled water from hot water, with almost no "
            "electricity. Inside, water evaporates at low pressure and takes heat from the "
            "chilled-water circuit (this is the cooling); its vapour is adsorbed by a solid "
            "such as silica gel. When the solid is saturated, hot water (60-90 degC, from the "
            "solar collectors) dries it again, driving the vapour out to a condenser cooled by "
            "a cooling tower or dry cooler; two beds alternate so the machine works "
            "continuously. It is the same idea as a refrigerator, but the compressor is "
            "replaced by a chemical process driven by heat. It makes sense because the sun is "
            "strongest exactly when the cooling is needed, and it needs the collectors to stay "
            "busy in summer, when hot-water demand is low."
        ),
        "assumptions": (
            "Silica-gel / water machine with a given thermal COP and a minimum drive "
            "temperature; the chiller works whenever the tank is hot enough; heat rejection "
            "assumed adequate and its electricity lumped in the parasitic consumption."
        ),
        "reference": "Henning, Solar Assisted Air Conditioning of Buildings (2nd ed., 2010); IEA SHC Task 38.",
    },
    "solar.chiller_cop": {
        "title": "Chiller COP and drive temperature",
        "formula": "COP = Q_cold / Q_heat;  cold = COP(T_store) x heat taken from the tank",
        "why": (
            "The thermal COP says how many kWh of cold you get per kWh of hot water; for "
            "silica-gel machines it is about 0.5-0.65 at best, and it falls when the drive "
            "water is cooler, until the machine stops (about 55-60 degC). So the collectors "
            "must reach high temperatures: this is why evacuated tubes or good flat plates are "
            "used, and why the real average COP of the plant is lower than the nominal one. "
            "Note the difference with an electric compressor chiller (COP 3-5): the "
            "adsorption machine uses far less electricity but needs 2 kWh of heat for 1 kWh of "
            "cold."
        ),
        "assumptions": (
            "COP varies linearly between the minimum and the nominal drive temperature, from "
            "45 % to 100 % of the nominal value; cooling-water temperature constant. Replace "
            "the defaults with the datasheet of the machine."
        ),
        "reference": "Manufacturer datasheets (silica-gel / water, 5-15 kW); Henning (2010), ch. 4.",
    },
    "solar.chillers": {
        "title": "Which cooling technology?",
        "formula": "cold = COP(T_tank) x heat taken;  compare machines on the same collectors and tank",
        "why": (
            "Three families make cold from solar heat. The adsorption chiller (silica gel and "
            "water) starts at about 60 degC and has a COP of about 0.5-0.6: it works with "
            "simple collectors and is quiet, but is bulky and dear for its size. The "
            "single-effect absorption chiller (lithium bromide and water) has a better COP, "
            "about 0.7, and is cheaper per kW, but needs 75-95 degC water: with ordinary flat "
            "plates it often stays idle, so evacuated tubes are the usual choice. Desiccant "
            "cooling dries the air with a rotating wheel regenerated by 50-80 degC heat and "
            "cools it with water: it works with the coolest drive water and suits ventilation "
            "air, but it needs more fan electricity and handles humidity rather than a "
            "chilled-water circuit. The comparison runs every technology you ticked on the same "
            "collectors, tank and cooling load."
        ),
        "assumptions": (
            "Typical catalogue values (COP, drive temperatures, cost per kW, electricity) for "
            "each family, with a COP that falls linearly towards the minimum drive temperature; "
            "the main technology uses the values you typed. A real machine has its own curve "
            "and size steps: use the datasheet. Double-effect absorption (COP above 1) needs "
            "140-180 degC and concentrating collectors, which this model does not include."
        ),
        "reference": "Henning, Solar Assisted Air Conditioning of Buildings (2010); IEA SHC Task 53.",
    },
    "solar.economics": {
        "title": "Costs, savings and payback of the solar plant",
        "formula": (
            "CAPEX = A x c_A + V x c_V + P_chiller x c_ch + fixed;  "
            "savings = heat_solar x p_heat + electricity saved x p_el"
        ),
        "why": (
            "The sun is free but the plant is not: the cost is collectors, tank, chiller and "
            "installation, paid once. The savings are the backup heat you do not buy (valued "
            "at the price of your boiler heat) and, with cooling, the electricity a compressor "
            "chiller would use less what the adsorption machine uses itself. The levelised cost "
            "of useful solar energy (LCOH) is the cost per kWh over the life of the plant; "
            "compare it with the price of the heat you replace. Without subsidies, hot water "
            "for a house usually repays in 10-20 years in central Europe, sooner in sunny and "
            "expensive-energy places; solar cooling is rarely competitive today without "
            "incentives, and is usually chosen for its low electricity peak."
        ),
        "assumptions": (
            "Constant prices and energy over the life, no incentives, taxes or financing, no "
            "replacement of the pump or the glycol, O&M as a percentage of CAPEX. The prices "
            "are round placeholders."
        ),
        "reference": "IEA SHC, Solar Heat Worldwide 2024; IRENA, Renewable Power Generation Costs.",
    },
    "solar.co2": {
        "title": "Carbon avoided",
        "formula": "CO2 = heat_solar x EF_heat + electricity saved x EF_grid",
        "why": (
            "Every kWh of heat the sun supplies is a kWh the boiler does not burn, so the "
            "carbon avoided is the heat times the emission factor of the fuel (about 0.2 kg/kWh "
            "for natural gas). With cooling, the avoided emissions are those of the electricity "
            "a compressor chiller would have used."
        ),
        "assumptions": "Emissions of making the collectors are small (a few years of the savings) and not counted.",
        "reference": "IPCC AR6 WG3 Annex III; national emission-factor tables.",
    },
    "solar.sensitivity": {
        "title": "Which assumption matters most?",
        "formula": "NPV recomputed with each input moved by -20 % and +20 %, one at a time",
        "why": (
            "The cost of the plant, the price of the heat you replace and the sun decide the "
            "result; the discount rate matters less. The longest bar is the number worth "
            "checking first. If the net present value changes sign inside the range, the "
            "decision is fragile for that input."
        ),
        "assumptions": "One at a time, +/-20 %, with the collector area fixed at the chosen one.",
        "reference": "Saltelli et al., Global Sensitivity Analysis: The Primer (2008).",
    },
}

SOLAR_TOPIC_ORDER: tuple[str, ...] = (
    "solar.resource",
    "solar.collector",
    "solar.load",
    "solar.store",
    "solar.simulation",
    "solar.solar_fraction",
    "solar.area",
    "solar.stagnation",
    "solar.adsorption",
    "solar.chiller_cop",
    "solar.chillers",
    "solar.economics",
    "solar.co2",
    "solar.sensitivity",
)
