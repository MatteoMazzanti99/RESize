"""'Why?' texts of the battery storage module (merged into ``EXPLANATIONS``)."""

from __future__ import annotations

BATTERY_EXPLANATIONS: dict[str, dict[str, str]] = {
    "battery.selfuse": {
        "title": "Self-consumption and self-sufficiency",
        "formula": "self-sufficiency = 1 - import / load;  self-consumption = (direct + charge) / production",
        "why": (
            "They sound alike but answer different questions. Self-sufficiency is the share of "
            "what you consume that does not come from the grid. Self-consumption is the share "
            "of what you produce that you use yourself instead of selling it. A battery raises "
            "both: the surplus of the day, which would be exported at a low price, is kept "
            "for the evening, when you would otherwise buy at the full price."
        ),
        "assumptions": (
            "Hourly values: inside one hour production and load are supposed constant, so "
            "short peaks and dips are not seen."
        ),
        "reference": "Luthander et al., Photovoltaic self-consumption in buildings, Applied Energy 2015.",
    },
    "battery.load": {
        "title": "The load profile",
        "formula": "load(t) = shape(t) * annual demand / sum of the shape",
        "why": (
            "What matters for a battery is not how much you consume in a year but when. A home "
            "uses most of its energy in the morning and evening, when the sun is low, so a "
            "battery has a lot to do; an office uses energy at midday, when PV produces, so it "
            "needs little storage. The same yearly kWh give very different batteries."
        ),
        "assumptions": (
            "A typical shape for the type chosen, not your real consumption. If you have the "
            "hourly data of your meter, the result will be more accurate."
        ),
        "reference": "Standard load profiles of distribution utilities; IEA-PVPS Task 13.",
    },
    "battery.dispatch": {
        "title": "Hour by hour: load first, then battery, then grid",
        "formula": "surplus = P_gen - P_load;  charge = min(surplus, power, free room / eta)",
        "why": (
            "Each hour the plant serves the load first. If there is a surplus it charges the "
            "battery, within the power of the converter and the room left; what does not fit "
            "is exported. If there is a deficit the battery discharges, within its power and "
            "what it holds; the rest is imported. This is the simplest and, for self-consumption, "
            "a very good strategy; it does not look at prices or weather forecasts."
        ),
        "assumptions": (
            "No grid charging, no peak shaving, no forecast. The efficiency is split equally "
            "between charging and discharging."
        ),
        "reference": "Weniger et al., Sizing of residential PV battery systems, Energy Procedia 2014.",
    },
    "battery.capacity": {
        "title": "Capacity, usable energy and power",
        "formula": "usable = capacity * depth of discharge * state of health;  power = C-rate * capacity",
        "why": (
            "The nameplate capacity is not what you can use: the battery is not fully emptied "
            "(depth of discharge, about 90 %) and it loses capacity with age, so the average "
            "over the life is lower still. The power is set by the converter and the cells and "
            "is given by the C-rate: 0.5 means that a full charge takes two hours. Too little "
            "power wastes the evening peak even if the capacity is large."
        ),
        "assumptions": "A constant state of health equal to the average over the life.",
        "reference": "Manufacturer datasheets of LFP home batteries; IRENA, Electricity storage and renewables (2017).",
    },
    "battery.efficiency": {
        "title": "Round-trip efficiency",
        "formula": "eta_charge = eta_discharge = sqrt(eta_round-trip)",
        "why": (
            "For every 100 kWh sent to the battery about 90 can be taken out: the rest is "
            "heat in the cells and the converter. These losses are paid by you, because they "
            "are energy that you produced and did not use. They are a few percent of the "
            "yearly energy, small compared with the gain, but they grow if the battery is "
            "cycled a lot."
        ),
        "assumptions": "A constant efficiency at any power and temperature.",
        "reference": "Schimpe et al., Comprehensive modeling of Li-ion storage systems, JES 2018.",
    },
    "battery.diminishing": {
        "title": "Why a bigger battery is not always better",
        "formula": "marginal gain = d(self-sufficiency) / d(capacity)  ->  0",
        "why": (
            "The first kilowatt-hours of battery are used every day and give a lot. Further "
            "ones are filled only in the sunny days of summer and do nothing in winter, when "
            "there is no surplus to store. So the self-sufficiency curve flattens, while the "
            "cost grows in a straight line: beyond a certain size each extra kWh costs more "
            "than it saves. The economic optimum is usually much smaller than the size that "
            "gives the highest self-sufficiency."
        ),
        "assumptions": "The plant size is fixed while the battery grows.",
        "reference": "Hoppmann et al., The economic viability of battery storage for residential solar PV, RSER 2014.",
    },
    "battery.life": {
        "title": "Life: cycles or calendar",
        "formula": "life = min(calendar life, cycle life / cycles per year)",
        "why": (
            "A battery ends its life for one of two reasons: it ages with time, even if unused, "
            "or it is worn by the charge and discharge cycles. A modern LFP battery makes "
            "about 6000 full cycles; a home uses 200-300 per year, so time (10-15 years) "
            "comes first. A battery that cycles daily with large energy, for example in "
            "industry, may be limited by the cycles instead."
        ),
        "assumptions": "The end of life is taken at 70-80 % of the initial capacity.",
        "reference": "Wang et al., Cycle-life model for graphite-LiFePO4 cells, J. Power Sources 2011.",
    },
    "battery.economics": {
        "title": "Savings, payback and net present value",
        "formula": "S = (import_without - import_with) * p_retail - (export_without - export_with) * p_export",
        "why": (
            "The battery does not produce energy: it moves it. What you save is the energy "
            "no longer bought, at the retail price, minus the income lost because that "
            "energy is no longer sold, at the export price. So the gain per kWh is the "
            "difference between the two prices, times the efficiency. With a small difference "
            "the battery has a long payback and often a negative net present value: this is "
            "a real result, not a mistake."
        ),
        "assumptions": "Constant prices over the life; no incentives; no replacement of the inverter.",
        "reference": "IEA-PVPS, Trends in PV applications; national net-metering rules.",
    },
    "battery.lcos": {
        "title": "Levelised cost of storage (LCOS)",
        "formula": "LCOS = (CAPEX * CRF + O&M) / energy delivered by the battery",
        "why": (
            "It is the cost of each kWh that comes out of the battery. Compare it with the "
            "difference between the price you would pay for that kWh from the grid and the "
            "price at which you would otherwise sell the surplus: only if the LCOS is lower "
            "than this margin does the battery pay for itself."
        ),
        "assumptions": "The cost of the electricity stored is not included (it is the surplus you would sell).",
        "reference": "Lazard, Levelized Cost of Storage; Schmidt et al., Joule 2019.",
    },
    "battery.co2": {
        "title": "Carbon avoided",
        "formula": "CO2 avoided = (import_without - import_with) * grid emission factor",
        "why": (
            "The battery avoids the electricity bought in the evening, which comes from the "
            "grid mix, in exchange for the surplus you do not export, which would have "
            "displaced other generation. Here only the first effect is counted, so it is an "
            "upper bound. The battery itself has an embodied footprint (about 60-100 kg CO2 "
            "per kWh) that is not included."
        ),
        "assumptions": "Average grid factor, no embodied carbon of the battery.",
        "reference": "Peters et al., Life cycle assessment of Li-ion batteries, Renew. Sust. Energy Rev. 2017.",
    },
    "battery.sensitivity": {
        "title": "What if my numbers are wrong? (sensitivity of the battery's value)",
        "formula": "result(input x (1 + s)) for s = -20 %, -10 %, +10 %, +20 %, one input at a time",
        "why": (
            "Every number you typed is an estimate. Sensitivity analysis asks: if this one is "
            "20 % off, how much does the result change? You repeat the calculation moving "
            "one input at a time and keep the others fixed. The inputs whose lines are "
            "steepest are the ones to measure, quote or negotiate carefully; the flat ones "
            "can stay approximate. For a battery the result is the small difference between two large numbers (savings against cost), so it is very sensitive: a change of a few cents in the tariff can turn a loss into a gain."
        ),
        "assumptions": (
            "One input at a time, the battery size fixed at the chosen one, prices constant over the life."
        ),
        "reference": "Saltelli et al., Global Sensitivity Analysis: The Primer (2008); IEA, Projected Costs of Generating Electricity.",
    },
}

BATTERY_TOPIC_ORDER: tuple[str, ...] = (
    "battery.selfuse",
    "battery.load",
    "battery.dispatch",
    "battery.capacity",
    "battery.efficiency",
    "battery.diminishing",
    "battery.life",
    "battery.economics",
    "battery.lcos",
    "battery.co2",
    "battery.sensitivity",
)
