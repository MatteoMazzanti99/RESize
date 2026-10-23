"""'Why?' texts of the biomass module (merged into ``EXPLANATIONS``)."""

from __future__ import annotations

BIOMASS_EXPLANATIONS: dict[str, dict[str, str]] = {
    "biomass.lhv": {
        "title": "Fuel energy: moisture and lower heating value",
        "formula": "LHV_ar = LHV_dry * (1 - M) - 0.679 * M     [kWh/kg, M = moisture, wet basis]",
        "why": (
            "Burning wood does not release the energy of the water it contains: that water has "
            "to be evaporated and leaves with the flue gas. So the useful energy per kilogram "
            "of fuel as delivered falls quickly with moisture: dry wood gives about 5 kWh/kg, "
            "chips at 30 % moisture about 3.4 kWh/kg, wet chips at 50 % only about 2.2. "
            "Moisture decides how many tonnes you must buy, store and haul for the same heat."
        ),
        "assumptions": (
            "LHV of the dry matter taken as a typical value for the fuel type; evaporation heat "
            "at 25 degC. Real fuels vary with species, bark share and season."
        ),
        "reference": "EN ISO 17225 (solid biofuels); Obernberger and Thek, The Pellet Handbook.",
    },
    "biomass.load_duration": {
        "title": "Heat load duration curve and how much heat a plant covers",
        "formula": "P(t) = P_peak (1 - t/T)^n,  n = 1/LF - 1;   f(x) = (n+1) x - n x^((n+1)/n)",
        "why": (
            "A heating load is high only for a few hours a year. Sorting the hours from the "
            "highest to the lowest load gives the load duration curve. The load factor LF "
            "(annual heat divided by peak power times 8760 h) describes how peaked it is; the "
            "curve above is a simple shape with that same mean. A biomass plant sized for "
            "the full peak would run at partial load most of the year, so it is usually sized "
            "for 60-80 % of the peak and covers 85-95 % of the heat; a gas or oil boiler "
            "(or a buffer tank) takes the peaks. The function f(x) gives the share of the heat "
            "covered by a plant of power x times the peak."
        ),
        "assumptions": (
            "Power-law shape of the curve, plant able to modulate down to zero. Real boilers "
            "have a minimum load (about 30 %) and a buffer tank smooths the demand: use real "
            "hourly data for a detailed design."
        ),
        "reference": "Quaschning, Regenerative Energiesysteme; EN 15316 (heating systems).",
    },
    "biomass.plant_power": {
        "title": "Plant power from the share of heat to cover",
        "formula": "P_th = x * P_peak with f(x) = coverage;    P_el = P_th * eta_el / eta_th",
        "why": (
            "Given the share of the yearly heat you want to cover, the load duration curve tells "
            "you the plant power (inverting f). For a cogeneration plant (ORC) the electrical "
            "power follows from the ratio of the two efficiencies: for every unit of heat the "
            "plant also makes eta_el / eta_th units of electricity. Heat-led sizing means the "
            "plant runs when there is a heat demand; the electricity is a result, not a target."
        ),
        "assumptions": (
            "Constant efficiencies at every load (in practice they drop at part load). The "
            "full-load hours give a quick check: a biomass boiler should reach about 3000-5000 "
            "h per year, an ORC plant more than 6000 h to be economic."
        ),
        "reference": "Obernberger, Biomass CHP technologies; IEA Bioenergy Task 32.",
    },
    "biomass.fuel_mass": {
        "title": "Fuel needed per year",
        "formula": "E_fuel = E_heat / eta_th;     m = E_fuel / LHV_ar",
        "why": (
            "The fuel energy is the useful heat divided by the efficiency of the plant, and the "
            "mass follows from the heating value of the fuel as delivered. This is the number "
            "that sizes the supply chain: how much biomass must be available within a "
            "reasonable distance, how many trucks and how much ash to dispose of."
        ),
        "assumptions": (
            "Annual average efficiency equal to the nominal one, no losses in storage "
            "(dry matter loss and drying in the pile can reach several percent)."
        ),
        "reference": "",
    },
    "biomass.storage": {
        "title": "Fuel storage and deliveries",
        "formula": "V = P_th / (eta_th * LHV) * 24 h * days / (rho_bulk * 0.8)",
        "why": (
            "Biomass has a low energy density: chips hold about 0.85 MWh per m3, against 10 MWh "
            "per m3 for oil. The store must cover the days between deliveries and the winter "
            "peaks, so it is sized on the nominal consumption for the chosen autonomy. The "
            "number of truck loads follows from the annual mass and the payload of a truck, "
            "which depends on the bulk density."
        ),
        "assumptions": (
            "Consumption at nominal power for the whole autonomy period (conservative), 80 % "
            "usable volume of the silo, 30 m3 truck. Real silos depend on the extraction system "
            "and on the delivery contract."
        ),
        "reference": "",
    },
    "biomass.biogas_yield": {
        "title": "Biogas and methane from the substrates",
        "formula": "V_CH4 = sum of (m_i * y_i);    E_CH4 = V_CH4 * 9.97 kWh/Nm3",
        "why": (
            "Each tonne of substrate (fresh matter) gives a methane volume that depends on its "
            "content of volatile solids and on how digestible they are: slurries are dilute "
            "(10-15 m3 CH4 per tonne), energy crops are rich (about 100 m3 CH4 per tonne). A "
            "mix of a rich substrate and manure is the usual compromise between yield and "
            "stability. Methane has a heating value of 9.97 kWh per normal m3."
        ),
        "assumptions": (
            "Typical handbook values, linear mixing. Real yields depend on the sample: ask for "
            "a biochemical methane potential (BMP) test before investing."
        ),
        "reference": "FNR, Guide to Biogas; KTBL, Faustzahlen Biogas.",
    },
    "biomass.chp_biogas": {
        "title": "CHP engine sized on the electricity demand",
        "formula": "E_gross = coverage * E_dem / (1 - parasitic);  P_el = E_gross / hours;  "
                   "E_CH4 = E_gross / eta_el",
        "why": (
            "A biogas plant is normally run for electricity: the engine runs about 8000 hours a "
            "year at steady power. The plant itself uses part of what it makes (pumps, mixers, "
            "feeding), so the gross electricity is a little higher than the demand to cover. "
            "The methane energy follows from the electrical efficiency of the engine, and the "
            "heat from the thermal efficiency."
        ),
        "assumptions": (
            "Constant efficiencies. Typical gas engines have 38-42 % electrical and 42-48 % "
            "thermal efficiency. The production does not follow the hourly load: a grid "
            "connection or a storage is assumed."
        ),
        "reference": "FNR, Guide to Biogas.",
    },
    "biomass.digester": {
        "title": "Digester volume and retention time",
        "formula": "V_work = m_day * HRT / rho;     V_total = V_work / 0.9",
        "why": (
            "The microorganisms need time to degrade the substrate: the hydraulic retention "
            "time (HRT) is the average days the material stays in the digester. Mesophilic "
            "plants use 30-60 days (longer for fibrous crops, shorter for slurries). The "
            "working volume is the daily feed times the HRT, and the gas headspace adds about "
            "10 %. A shorter HRT means a smaller, cheaper digester but a lower methane yield."
        ),
        "assumptions": "Density of the slurry 1 t/m3; one continuous stirred digester.",
        "reference": "FNR, Guide to Biogas.",
    },
    "biomass.olr": {
        "title": "Organic loading rate",
        "formula": "OLR = VS per day / V_work    [kg VS per m3 per day]",
        "why": (
            "The organic loading rate says how much volatile solids (the part that can be "
            "digested) you feed per m3 each day. Too high and the acids produced faster than "
            "they are consumed can acidify the digester and stop gas production; too low and "
            "the volume is not used well. Stable mesophilic plants work at about 2-4 kg VS per "
            "m3 and day, with an upper limit near 4.5."
        ),
        "assumptions": "Volatile solids from the typical total solids of each substrate.",
        "reference": "FNR, Guide to Biogas; Weiland, Biogas production: current state.",
    },
    "biomass.heat_balance": {
        "title": "Heat of the CHP: how much is really available",
        "formula": "Q_total = E_gross * eta_th / eta_el;   Q_useful = Q_total * (1 - share_digester)",
        "why": (
            "The engine produces about as much heat as electricity or more. A quarter of it, "
            "depending on climate and insulation, keeps the digester at 37-42 degC; only the "
            "rest can be sold or used for buildings. Because a biogas plant runs all year, the "
            "heat is often wasted in summer unless there is a steady use (drying, "
            "greenhouses, a heat network)."
        ),
        "assumptions": (
            "A fixed share of the heat is used by the digester; the demand is taken as an annual "
            "amount without a summer-winter mismatch."
        ),
        "reference": "FNR, Guide to Biogas.",
    },
    "biomass.land": {
        "title": "Land and digestate",
        "formula": "area = sum of (m_i / crop yield_i)",
        "why": (
            "Energy crops need land: this is the hectares of maize or grass silage to grow each "
            "year at a typical yield. Manure and waste need none, but they must be collected "
            "nearby: slurries are 90 % water and do not travel well. What comes out of the "
            "digester (digestate) keeps almost all the mass and the nutrients, and is spread "
            "on fields as fertiliser."
        ),
        "assumptions": (
            "Typical yields (45 t per ha for maize silage, 30 for grass). Food-versus-energy "
            "and sustainability rules for crops depend on the country."
        ),
        "reference": "FNR, Guide to Biogas; RED III sustainability criteria.",
    },
    "biomass.co2": {
        "title": "Avoided CO2 emissions",
        "formula": "CO2 avoided = Q/eta_ref * EF_gas + E_el * EF_grid - E_fuel * EF_supply",
        "why": (
            "The CO2 released when biomass burns was taken from the air by the plant as it grew, "
            "so it is counted as neutral over a short cycle. What is avoided is the fossil "
            "fuel it replaces: the gas that would have made the same heat in a reference boiler "
            "and the grid electricity. Growing, drying, chipping, hauling and, for biogas, "
            "methane leaks are subtracted as a supply-chain emission."
        ),
        "assumptions": (
            "Biogenic CO2 neutral; one average emission factor for the grid and for the "
            "supply chain (a placeholder to replace with your own data). Land-use change and "
            "the time the carbon takes to regrow are not included."
        ),
        "reference": "IPCC Guidelines for National Greenhouse Gas Inventories; EU RED III.",
    },
}

SOLID_TOPIC_ORDER: tuple[str, ...] = (
    "biomass.lhv", "biomass.load_duration", "biomass.plant_power", "biomass.fuel_mass",
    "biomass.storage", "biomass.co2",
)
BIOGAS_TOPIC_ORDER: tuple[str, ...] = (
    "biomass.biogas_yield", "biomass.chp_biogas", "biomass.digester", "biomass.olr",
    "biomass.heat_balance", "biomass.land", "biomass.co2",
)
BIOMASS_TOPIC_ORDER: tuple[str, ...] = tuple(
    dict.fromkeys(SOLID_TOPIC_ORDER + BIOGAS_TOPIC_ORDER))


def topics_for(pathway: str) -> tuple[str, ...]:
    """The 'Why?' topics that apply to a pathway."""
    return BIOGAS_TOPIC_ORDER if pathway == "biogas" else SOLID_TOPIC_ORDER
