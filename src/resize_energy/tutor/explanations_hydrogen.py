"""'Why?' texts of the green hydrogen module (merged into ``EXPLANATIONS``)."""

from __future__ import annotations

HYDROGEN_EXPLANATIONS: dict[str, dict[str, str]] = {
    "hydrogen.efficiency": {
        "title": "Energy per kilogram of hydrogen and efficiency",
        "formula": "eta_LHV = 33.33 kWh/kg / (kWh per kg consumed)",
        "why": (
            "A kilogram of hydrogen holds 33.3 kWh (lower heating value) or 39.4 kWh (higher "
            "heating value). A PEM electrolyser system, with its power electronics, pumps and "
            "cooling, needs about 50-58 kWh of electricity per kilogram, which is an efficiency "
            "of 57-67 % on the LHV. The specific consumption is the number that links the "
            "electricity you have to the hydrogen you get, so it fixes the size of everything "
            "else. It rises over the years as the stack degrades."
        ),
        "assumptions": (
            "One constant value for the whole system at any load and for the whole life. In "
            "reality the stack is more efficient at part load and less efficient when old, "
            "while the auxiliaries weigh more at low load."
        ),
        "reference": "IEA, Global Hydrogen Review; IRENA, Green hydrogen cost reduction (2020).",
    },
    "hydrogen.dispatch": {
        "title": "Hour by hour: renewables first, minimum load, grid top-up",
        "formula": "P_el(t) = min(P_res(t), P_nom);  off if P_el(t) < min_load * P_nom",
        "why": (
            "An electrolyser can follow the sun and the wind, but not without limits: it cannot "
            "use more than its nominal power (the surplus is curtailed) and a PEM stack must "
            "stay above a minimum load (about 5-10 %) to run safely. So the yearly hydrogen "
            "depends on how the renewable power is spread over the 8760 hours, not only on "
            "its total. If the grid is allowed, it fills the gap up to the nominal power, "
            "within the limit you set in full-load hours, which also sets the carbon "
            "content of the hydrogen."
        ),
        "assumptions": (
            "Real hourly wind and radiation of one year (NASA POWER) when available, otherwise "
            "an invented year. One year is not the long-term average. The grid top-up is spread "
            "evenly over the hours because no hourly prices are used. Ramp rates and "
            "start-up times are ignored (PEM is fast: seconds)."
        ),
        "reference": "Buttler and Spliethoff, Current status of water electrolysis, RSER 2018.",
    },
    "hydrogen.sizing": {
        "title": "Sizing from the hydrogen demand",
        "formula": "P_el = demand / (kg per kW of electrolyser per year);  P_res = ratio * P_el",
        "why": (
            "Simulating 1 kW of electrolyser with the renewable plant scaled by a ratio gives "
            "the kilograms it makes in a year; the electrolyser needed for your demand is the "
            "demand divided by that. The ratio between renewable and electrolyser power is a "
            "design choice: more renewable power (oversizing, 1.2-2) keeps the electrolyser "
            "running more hours, so it costs less per kilogram, but more energy is "
            "curtailed. The best ratio is where the cost per kilogram is lowest."
        ),
        "assumptions": (
            "The result is linear in size (no scale effects on efficiency). Costs per kW are "
            "the same for any size, which is not true for small plants."
        ),
        "reference": "IRENA, Green hydrogen cost reduction (2020).",
    },
    "hydrogen.compression": {
        "title": "Compression to the storage pressure",
        "formula": "w = R T ln(p_out / p_in) / eta_iso    [kWh/kg],  R = 4124 J/(kg K)",
        "why": (
            "A PEM electrolyser delivers hydrogen at about 30 bar; to store it in tanks at "
            "350 bar it must be compressed. The minimum work is the isothermal one, "
            "R T ln(p2/p1); a real multi-stage compressor needs about 1.6 times that "
            "(isothermal efficiency about 60 %). It adds 1-2 kWh per kilogram, a few percent "
            "of the electrolysis energy. Higher pressure stores more per cubic metre but costs "
            "more energy and money."
        ),
        "assumptions": (
            "Ideal-gas work with a fixed efficiency and a temperature of 298 K. The "
            "compressor is counted inside the electrical consumption of the plant."
        ),
        "reference": "Gardiner, Hydrogen Production and Storage; IEA Global Hydrogen Review.",
    },
    "hydrogen.storage": {
        "title": "Hydrogen storage",
        "formula": "V = m / rho(p),   rho = p / (Z R T),   Z = 1 + 0.0006 p",
        "why": (
            "Hydrogen is very light: at 350 bar it is only 24 kg per cubic metre (a petrol "
            "tank of the same size holds hundreds of kilograms of fuel with much more energy). "
            "The tank volume is the mass to buffer, the average daily production times the "
            "days of autonomy, divided by the density at the storage pressure. The buffer "
            "smooths the difference between the variable production and the customer's "
            "steady demand."
        ),
        "assumptions": (
            "Average daily production times the chosen days (not the worst week), simple "
            "real-gas correction at 288 K. Seasonal storage needs far more, usually in salt "
            "caverns."
        ),
        "reference": "NIST Chemistry WebBook (hydrogen properties).",
    },
    "hydrogen.water": {
        "title": "Water and oxygen",
        "formula": "2 H2O -> 2 H2 + O2:   8.94 kg water and 7.94 kg oxygen per kg of H2",
        "why": (
            "Water is the raw material: the chemistry needs 9 litres per kilogram of hydrogen; "
            "a real plant uses about 10-15 litres because of purification losses and cooling "
            "make-up. The water must be very pure (conductivity below 1 microsiemens per "
            "cm): sea or brackish water needs desalination first, which adds a little energy "
            "and cost. The oxygen is a by-product that can be sold or used (for example in "
            "wastewater treatment)."
        ),
        "assumptions": (
            "A fixed consumption per kilogram; the energy and cost of water treatment are "
            "included only as a price per cubic metre."
        ),
        "reference": "IRENA, Green hydrogen: a guide to policy making.",
    },
    "hydrogen.stack": {
        "title": "Stack life and replacement",
        "formula": "life [years] = stack hours / full-load hours per year",
        "why": (
            "The stack, where the reaction takes place, wears out with operating hours: a PEM "
            "stack lasts about 50,000-80,000 hours at full-load equivalent. A plant that runs "
            "5000 full-load hours a year needs a new stack after 12 years; one that runs "
            "8000 hours, after 7.5 years. The replacement is a large cost (30-45 % of the "
            "electrolyser) and is added to the yearly cost in proportion to the hours used."
        ),
        "assumptions": (
            "Wear proportional to the full-load hours. Frequent starts and stops and high "
            "temperatures can shorten the life further."
        ),
        "reference": "IEA, The Future of Hydrogen (2019).",
    },
    "hydrogen.lcoh": {
        "title": "Levelised cost of hydrogen (LCOH)",
        "formula": "LCOH = (annual cost of electrolyser, stack, storage, renewables, grid, water) / kg",
        "why": (
            "The cost of a kilogram of hydrogen adds the capital cost of the electrolyser "
            "(spread over its life with the capital recovery factor), the operation and "
            "maintenance, the stack replacement, the storage, the water and, above all, the "
            "electricity: either the cost of the renewable plant built for the electrolyser or "
            "the price of grid electricity. Running more hours lowers the capital cost per "
            "kilogram, but only cheap electricity makes cheap hydrogen."
        ),
        "assumptions": (
            "The whole renewable plant is charged to the hydrogen, also the curtailed energy "
            "(a plant built for it). Constant prices, no incentives, taxes or grid fees, no "
            "revenue from oxygen or heat."
        ),
        "reference": "IEA, Global Hydrogen Review; IRENA, Green hydrogen cost reduction.",
    },
    "hydrogen.co2": {
        "title": "Carbon intensity of the hydrogen",
        "formula": "CI = (E_grid * EF_grid + E_pv * EF_pv + E_wind * EF_wind) / kg",
        "why": (
            "Hydrogen is only as clean as the electricity that makes it. At 55 kWh per "
            "kilogram, grid power with 0.25 kg CO2 per kWh gives about 14 kg CO2 per kilogram "
            "of hydrogen, more than the 9-10 kg of hydrogen from natural gas. Solar and wind "
            "bring it down to 1-3 kg, counting the emissions of building the plant. EU rules "
            "for renewable hydrogen require an emission reduction of 70 % compared with "
            "fossil fuel, which is about 3.4 kg CO2 per kg of hydrogen, and set conditions "
            "on how grid electricity can be used."
        ),
        "assumptions": (
            "Average grid factor and life-cycle factors of PV and wind as placeholders. "
            "Regulatory rules (additionality, temporal and geographic correlation) are not "
            "checked here: the result is an indication, not a certification."
        ),
        "reference": "EU Delegated Regulation 2023/1184 (RFNBO); IPCC AR5 WGIII Annex III.",
    },
    "hydrogen.partload": {
        "title": "Efficiency at part load",
        "formula": "f(x) = (1 - a)(1 - g(1 - x)) + a / x;   kWh/kg(x) = kWh/kg_nominal * f(x)",
        "why": (
            "Solar and wind rarely give exactly the nominal power, so the electrolyser spends "
            "much of the year at part load. Two things happen. The stack is a little more "
            "efficient at low current (g: the gain at very low load). But the auxiliaries, "
            "pumps, cooling and power electronics, draw nearly the same power at any load "
            "(a: about 6 % of nominal), so per kilogram they weigh 1/x more. The result is a "
            "curve that is flat around 40-100 % and rises steeply below 20 %: running at "
            "very low load wastes energy, which is why the minimum load matters."
        ),
        "assumptions": (
            "A smooth curve with two parameters, not the polarisation curve of a real stack. "
            "Temperature and pressure effects are ignored."
        ),
        "reference": "Buttler and Spliethoff, RSER 2018; Brauns and Turek, Processes 2020.",
    },
    "hydrogen.ageing": {
        "title": "Stack ageing over the years",
        "formula": "kWh/kg(age) = kWh/kg_new * (1 + d * hours / 1000)",
        "why": (
            "The stack voltage rises slowly with the hours of operation (typically 0.1-0.3 % "
            "every 1000 hours for PEM), so the same electricity gives less hydrogen year after "
            "year until the stack is replaced and the plant starts again from new. The hydrogen "
            "you plan with is the average over the life, not the first year. A plant that "
            "runs many hours ages faster but also makes more hydrogen in the same years."
        ),
        "assumptions": (
            "Linear drift, replacement at the stack life you set, no extra wear from starts and "
            "stops. The average is simple (not discounted)."
        ),
        "reference": "Frensch et al., Influence of the operation mode on PEM electrolysis degradation, IJHE 2019.",
    },
    "hydrogen.tank": {
        "title": "Storage sized hour by hour",
        "formula": "level(t) = sum of (production - offtake);  tank = max(level) - min(level)",
        "why": (
            "If the customer takes hydrogen at a constant rate, equal to the yearly average, "
            "the tank must hold the difference between the variable production and that "
            "steady offtake. Adding hour after hour, the level goes up in the sunny or windy "
            "periods and down in the others; the tank is the distance between the highest and "
            "the lowest point. With solar alone this is a seasonal tank, far bigger than a "
            "few days of autonomy, which is why the choice of 'days' can be too optimistic."
        ),
        "assumptions": (
            "Constant offtake all year, one year of data repeated, no losses or leaks, no "
            "compressor limits. A real customer has its own profile."
        ),
        "reference": "Hydrogen Council, Path to hydrogen competitiveness (2020).",
    },
    "hydrogen.prices": {
        "title": "Hourly electricity prices: when to buy from the grid",
        "formula": "cost = sum of grid_energy(t) * price(t);  buy in the cheapest hours first",
        "why": (
            "An electrolyser can wait. If the grid is allowed a number of hours a year, it is "
            "better to use them when electricity costs less: nights, windy days, sunny "
            "middays. Buying in the cheapest hours instead of spreading the purchase evenly "
            "lowers the average price paid for the same energy and the same carbon (if the "
            "grid factor is constant). The gain depends on the volatility of the market."
        ),
        "assumptions": (
            "An invented price year with the usual shape unless you load real prices; one year "
            "is not the future. The grid factor is the same in every hour, although cheap hours "
            "are often the cleanest."
        ),
        "reference": "ENTSO-E Transparency Platform (day-ahead prices); Armijo and Philibert, IJHE 2020.",
    },
}

HYDROGEN_TOPIC_ORDER: tuple[str, ...] = (
    "hydrogen.efficiency",
    "hydrogen.dispatch",
    "hydrogen.sizing",
    "hydrogen.compression",
    "hydrogen.storage",
    "hydrogen.water",
    "hydrogen.stack",
    "hydrogen.partload",
    "hydrogen.ageing",
    "hydrogen.tank",
    "hydrogen.prices",
    "hydrogen.lcoh",
    "hydrogen.co2",
)
