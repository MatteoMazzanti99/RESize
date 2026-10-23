"""'Why?' texts of the technology comparison (merged into ``EXPLANATIONS``)."""

from __future__ import annotations

COMPARE_EXPLANATIONS: dict[str, dict[str, str]] = {
    "econ.same_demand": {
        "title": "Comparing on the same demand",
        "formula": "PV: P = c * E / (H * PR)   Wind: N = ceil(c * E / E_turbine)   H2: kg = c * E / 33.33",
        "why": (
            "A fair comparison sizes every plant for the same job: the same yearly demand E and "
            "the same share c to cover. The photovoltaic array can be sized to the exact target, "
            "while turbines come in whole units, so the wind plant usually produces a bit more "
            "than needed (a lot more when one turbine is large compared with the demand). That "
            "extra energy is sold at the export price, so it helps the wind balance less than "
            "the energy that replaces purchases. Biogas and hydrogen come from their own "
            "modules; hydrogen is counted as the energy of the molecule (33.33 kWh per kg) and "
            "compared with hydrogen from natural gas, not with the grid."
        ),
        "assumptions": (
            "Annual energy balance only. Wind and sun are not available at the same hours of "
            "the day, and neither follows the load: a real comparison needs hourly data and "
            "possibly storage. The PV array is not limited by inverter or string constraints."
        ),
        "reference": "IEA, Projected Costs of Generating Electricity (methodology).",
    },
    "econ.crf": {
        "title": "Money has a time value: the capital recovery factor",
        "formula": "CRF = r (1 + r)^n / ((1 + r)^n - 1)",
        "why": (
            "A plant is paid for today and repays over its lifetime. The capital recovery factor "
            "turns the investment into an equal yearly payment that covers the interest r on the "
            "money and gives it back over n years. With r = 5 % and n = 25 years, every euro "
            "of CAPEX costs about 7.1 cents per year. A higher discount rate penalises "
            "capital-intensive technologies more."
        ),
        "assumptions": (
            "One discount rate for all technologies, constant prices (real terms), no taxes and "
            "no financing structure. In practice the rate depends on the risk of the project."
        ),
        "reference": "Short and Packey, A Manual for the Economic Evaluation of Energy "
                     "Efficiency and Renewable Energy Technologies, NREL/TP-462-5173.",
    },
    "econ.lcoe": {
        "title": "Levelised cost of energy (LCOE)",
        "formula": "LCOE = (CAPEX * CRF + O&M per year) / E per year   [euro/kWh]",
        "why": (
            "LCOE is the price at which each kWh must be sold for the plant to repay its costs "
            "and the interest on them over its life. It lets you compare technologies of "
            "different size and cost structure: PV has little O&M and a lot of CAPEX, wind has "
            "more O&M and, at good sites, many more full-load hours. If the LCOE is below the "
            "price you pay for electricity, producing is cheaper than buying."
        ),
        "assumptions": (
            "Constant yearly energy (no degradation) and constant costs. Grid connection, land, "
            "decommissioning, taxes and incentives are not included unless you put them in the "
            "CAPEX. LCOE does not capture when the energy is produced."
        ),
        "reference": "IEA/NEA, Projected Costs of Generating Electricity; IRENA, Renewable "
                     "Power Generation Costs.",
    },
    "econ.savings": {
        "title": "Value of the energy: avoided purchases and exports",
        "formula": "S = min(E, D) * p_retail + max(0, E - D) * p_export   (hydrogen: E * p_reference)",
        "why": (
            "Energy that replaces what you would buy from the grid is worth the retail price. "
            "Energy beyond your demand is sold at the export price, usually much lower. The "
            "yearly benefit is S minus the O&M cost."
        ),
        "assumptions": (
            "Annual balance, like net metering: all energy up to the demand is assumed to be "
            "self-used. In reality part of it is exported hour by hour even below the yearly "
            "demand, so the real savings are lower. Prices are constant over the lifetime."
        ),
        "reference": "",
    },
    "econ.payback": {
        "title": "Payback time and net present value",
        "formula": "payback = CAPEX / (S - O&M)      NPV = -CAPEX + (S - O&M) * (1 - (1+r)^-n) / r",
        "why": (
            "The simple payback is the time needed for the yearly benefit to repay the "
            "investment; it is easy to understand but ignores interest and what happens after "
            "the payback. The net present value adds all the yearly benefits over the lifetime, "
            "discounted at the rate r, and subtracts the CAPEX: a positive NPV means the "
            "project earns more than the discount rate. The discounted payback is the time "
            "when the discounted cash flow reaches zero."
        ),
        "assumptions": (
            "Constant yearly benefit, no replacement of components (inverters, gearboxes) and "
            "no residual value. Payback and NPV depend a lot on the electricity price you "
            "assume."
        ),
        "reference": "Short and Packey, NREL/TP-462-5173.",
    },
    "econ.co2": {
        "title": "Avoided CO2 emissions",
        "formula": "CO2 avoided = E * (EF_grid - EF_life)   [kg CO2 per year]",
        "why": (
            "Each kWh produced displaces a kWh from the grid, with the grid's emission factor "
            "EF_grid. The plant itself is not free of emissions: manufacturing, transport and "
            "installation give a life-cycle value EF_life per kWh, which is subtracted. Typical "
            "life-cycle values are tens of g/kWh for PV and about 10 g/kWh for onshore wind, "
            "against hundreds for the grid mix."
        ),
        "assumptions": (
            "An average grid factor (not the marginal plant that is actually displaced) and "
            "a constant factor over the lifetime, although grids are decarbonising. Life-cycle "
            "values vary with the study and the manufacturing country."
        ),
        "reference": "IPCC AR5 WGIII Annex III (life-cycle emissions of electricity supply).",
    },
}

COMPARE_TOPIC_ORDER: tuple[str, ...] = (
    "econ.same_demand",
    "econ.crf",
    "econ.lcoe",
    "econ.savings",
    "econ.payback",
    "econ.co2",
)
