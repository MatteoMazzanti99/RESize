"""'Why?' texts of the run-of-river hydropower module (merged into ``EXPLANATIONS``)."""

from __future__ import annotations

HYDRO_EXPLANATIONS: dict[str, dict[str, str]] = {
    "hydro.fdc": {
        "title": "Flow-duration curve: how much water the river has",
        "formula": "Q(p) = exp(mu + sigma * z),  z = value of the normal curve exceeded with "
                   "probability p;   sigma = -1.645 + sqrt(1.645^2 + 2 ln(Q_mean / Q95))",
        "why": (
            "A river never carries its mean flow: it is high in spring and low in late summer. "
            "The flow-duration curve sorts all the days of the year from the wettest to the "
            "driest and tells you, for every flow, the share of time p it is exceeded. A run-of-"
            "river plant has no reservoir, so the curve decides everything: how much water the "
            "turbine can use and for how many hours. RESize builds the curve from two numbers "
            "that every hydrologic study gives: the mean flow and Q95, the flow that is "
            "exceeded 95 % of the time (the low-flow value). Taking the logarithm of the flow "
            "as a normal variable, those two numbers fix the whole curve. A large ratio "
            "Q_mean / Q95 means a flashy river with a very uneven year."
        ),
        "assumptions": (
            "The log-normal shape is a convenient fit, not a law: a snow-fed or a karst river "
            "can be different. If you have the measured daily flows of the site, build the "
            "curve from them and use its Q_mean and Q95 here. One typical year: dry and wet "
            "years change the energy by tens of percent."
        ),
        "reference": "Vogel and Fennessey (1994), flow-duration curves; ESHA Guide, hydrology.",
    },
    "hydro.eco_flow": {
        "title": "Environmental flow and the flow left for the turbine",
        "formula": "Q_available(p) = max(Q(p) - Q_eco, 0)",
        "why": (
            "Part of the water must stay in the river reach between the intake and the "
            "powerhouse, to keep fish and the river's life alive. This environmental flow is "
            "taken first: the turbine only gets what is left. The rule depends on the country "
            "and the river basin (a share of the mean flow, or a flow per square kilometre of "
            "catchment). A common starting point is about 10 % of the mean flow, a bare "
            "minimum; about 30 % is considered good for the river. It is the number that changes "
            "the energy most for a low-head plant on a small river, and it is often the "
            "condition on which the permit is granted."
        ),
        "assumptions": (
            "A constant flow all year, taken from the river at every moment. Some rules ask for "
            "a seasonal flow (more in spring, when fish spawn): check the one of your basin."
        ),
        "reference": "Tennant (1976); Water Framework Directive 2000/60/EC; the basin authority.",
    },
    "hydro.design_flow": {
        "title": "Design flow: how big to make the turbine",
        "formula": "Q_design = Q(p_design) - Q_eco;    capacity factor = E / (P_rated * 8760)",
        "why": (
            "The design flow is the largest flow the turbine takes. A big machine (a flow that "
            "is exceeded only 10 % of the time) catches the floods but works at full power for "
            "few hours and costs a lot; a small one (a flow exceeded 60-90 % of the time) runs "
            "all year at full power but lets most of the water pass by. The usual choice for a "
            "run-of-river plant is a flow that the river exceeds 20-40 % of the time. Moving "
            "the design flow along the curve shows the trade-off: the energy grows more and "
            "more slowly while the power, and the cost, keep growing."
        ),
        "assumptions": (
            "The cost is proportional to the rated power (a single euro per kW). In reality the "
            "intake, the penstock and the building scale with the flow and the head in other "
            "ways: use quotes for a real project."
        ),
        "reference": "ESHA Guide on How to Develop a Small Hydropower Plant, chapters 3 and 6.",
    },
    "hydro.power": {
        "title": "Power from the head and the flow",
        "formula": "P = rho * g * Q * H_net * eta_t * eta_g / 1000   [kW]",
        "why": (
            "Water falling through a height H releases the potential energy m g H; per second "
            "that is rho g Q H, in watts, with Q the flow in cubic metres per second. The "
            "head that counts is the net one, the gross head (the difference of level between "
            "intake and the turbine outlet) minus what the penstock loses to friction. The "
            "machine then converts the hydraulic power with the efficiency of the turbine "
            "(0.8-0.94) and of the generator (0.91-0.97). A rule of thumb: about 8 kW for every "
            "m3/s and every metre of head."
        ),
        "assumptions": (
            "The turbine efficiency is the best one of the type; at partial flow it is lower, "
            "which the 'operating losses' share of the energy covers only in part. The "
            "generator efficiency follows the size of the machine."
        ),
        "reference": "ESHA Guide, tables 6.7 and 6.8; Paish (2002).",
    },
    "hydro.penstock": {
        "title": "Penstock: diameter and head loss",
        "formula": "D = sqrt(4 * Q / (pi * v));    h_f = (f * L / D + K) * v^2 / (2 * g);    "
                   "f = 0.25 / (log10(e / (3.7 * D) + 5.74 / Re^0.9))^2",
        "why": (
            "The penstock brings the water from the intake to the turbine and it loses a part "
            "of the head to friction. A narrow pipe is cheap but the water runs fast and the "
            "loss grows with the square of the speed; a wide one wastes less head and costs "
            "more. A design speed of 2-4 m/s is a common compromise and sets the diameter. The "
            "friction loss comes from the Darcy-Weisbach equation, with the friction factor f "
            "that depends on the roughness e of the pipe and on the Reynolds number Re (the "
            "Swamee-Jain formula gives it directly); K groups the local losses of the trash "
            "rack, the entrance, the bends and the valve."
        ),
        "assumptions": (
            "One pipe of constant diameter and roughness, full of water, water at about "
            "20 degC. The loss is computed at every flow of the year, not only at the design "
            "flow. Water hammer (the pressure surge when the valve closes) is not checked: it "
            "decides the wall thickness of the pipe."
        ),
        "reference": "White, Fluid Mechanics; Swamee and Jain (1976); ESHA Guide, chapter 5.",
    },
    "hydro.turbine": {
        "title": "Which turbine, and from which flow it works",
        "formula": "Kaplan 2-40 m;  Francis 25-350 m;  Pelton 50-1300 m;  Q_min = fraction * Q_design",
        "why": (
            "The turbine type depends mainly on the head and the flow. Low head and large flow: "
            "Kaplan (a propeller with adjustable blades). Medium head: Francis. High head and "
            "small flow: Pelton (a jet that hits buckets); the crossflow machine is a simple, "
            "cheaper option for small plants. Each type also has a lowest flow below which it "
            "does not work well: a single-regulated Kaplan stops around 30 % of its design flow, "
            "a Francis around 50 %, a Pelton with one jet works down to 30 % and with several "
            "jets down to 10 %. Below that flow the "
            "turbine is switched off and the water goes by. RESize picks the type from these "
            "ranges; check the final choice with a turbine maker."
        ),
        "assumptions": (
            "The selection is a rule of thumb inside the head ranges of the ESHA tables: the "
            "flow decides between types that overlap. The lowest working flows are typical "
            "values; the crossflow figures are RESize's own. Cavitation, rotational speed and "
            "the choice between one and several units are not studied."
        ),
        "reference": "ESHA Guide, section 6.2 and tables 6.3 and 6.7.",
    },
    "hydro.energy": {
        "title": "Energy in a year",
        "formula": "E = (1 - losses) * sum of P(Q_t(p)) * 8760 / N over the curve;    "
                   "Q_t = min(Q_available, Q_design), and 0 if below Q_min",
        "why": (
            "The yearly energy is the area under the power-duration curve. RESize cuts the "
            "flow-duration curve into 400 equal slices of time, computes for every slice the "
            "flow that goes through the turbine (the river flow minus the environmental flow, "
            "at most the design flow, zero below the minimum flow), the head lost in the "
            "penstock at that flow and the power, and adds them up. Many hours at full power "
            "(about 3000-4500 for a run-of-river plant, a capacity factor of 40-60 %) mean a "
            "good site."
        ),
        "assumptions": (
            "A typical year, no reservoir and no flood losses or ice. The share of 'operating "
            "losses' (default 5 %) covers outages, cleaning of the trash rack and the "
            "efficiency at partial load, and is a RESize choice: replace it with data from the "
            "plants of the same river."
        ),
        "reference": "ESHA Guide, chapter 3 (energy); NREL ATB 2024 (capacity factors).",
    },
    "hydro.economics": {
        "title": "Cost of the plant and of the energy",
        "formula": "LCOE = (CAPEX * CRF + O&M) / E;    O&M = fraction * CAPEX;    "
                   "NPV = -CAPEX + net benefit * annuity factor",
        "why": (
            "A small hydropower plant has few moving parts and lasts for decades, but it is "
            "expensive to build: the civil works (intake, penstock, powerhouse, connection) "
            "cost more than the machines, and they depend a lot on the site. The levelised "
            "cost of energy spreads the capital over the life with the capital recovery factor "
            "and adds the yearly O&M; it is the price at which the plant just pays for itself. "
            "Comparing it with the price you pay or the price of the energy sold tells whether "
            "the plant is worth building."
        ),
        "assumptions": (
            "Constant prices, one discount rate, no incentives, no taxes, no replacement of the "
            "machines. The cost per kW is a literature value for a new run-of-river plant in "
            "the USA: it varies by a factor of two or three with the site; ask for quotes."
        ),
        "reference": "NREL ATB 2024, hydropower; IEA and NEA, Projected Costs of Generating Electricity.",
    },
    "hydro.co2": {
        "title": "Carbon avoided",
        "formula": "CO2 = E * (EF_grid - EF_plant) / 1000   [t per year]",
        "why": (
            "Electricity from a hydropower plant displaces electricity made on the grid, so "
            "it avoids the grid's emissions. The plant is not free of them: building the dam or "
            "the weir, the penstock and the machines emits CO2, about 24 g per kWh as a median "
            "of the published life-cycle studies. A run-of-river plant has no large "
            "reservoir, so the methane that rotting vegetation releases from the bottom of "
            "one is much smaller."
        ),
        "assumptions": (
            "One average emission factor for the grid, today's. If the grid decarbonises "
            "the saving shrinks over the years."
        ),
        "reference": "IPCC AR5, Annex III (life-cycle emissions); national grid factor (ISPRA).",
    },
}

HYDRO_TOPIC_ORDER: tuple[str, ...] = (
    "hydro.fdc", "hydro.eco_flow", "hydro.design_flow", "hydro.power", "hydro.penstock",
    "hydro.turbine", "hydro.energy", "hydro.economics", "hydro.co2",
)
