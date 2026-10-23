"""'Why?' texts of the cost step of the photovoltaic and wind flows."""

from __future__ import annotations


def _econ(prefix: str, unit: str, plant: str) -> dict[str, dict[str, str]]:
    return {
        f"{prefix}.economics": {
            "title": "Costs, savings and payback",
            "formula": (
                "CAPEX = P x c_kW ;  O&M = P x o_kW per year\n"
                "Savings = min(E, D) x p_retail + max(0, E - D) x p_export\n"
                "Net benefit = Savings - O&M ;  payback = CAPEX / net benefit\n"
                "NPV = -CAPEX + net benefit x AF(r, n) ;  LCOE = (CAPEX x CRF + O&M) / E\n"
                "CO2 avoided = E x (grid factor - life-cycle factor)"
            ),
            "why": (
                f"A {plant} is paid for once and then runs for decades, so its cost is spread "
                "over the years with the capital recovery factor CRF: the yearly payment that "
                "repays the investment at the discount rate r over n years. Dividing that, plus "
                "the yearly maintenance, by the energy gives the levelised cost of energy (LCOE), "
                "the price at which the plant just breaks even; compare it with what you pay for "
                "grid electricity. The savings come from the energy you use yourself, valued at "
                "the retail price, plus the surplus sold at the (lower) export price. The net "
                "present value adds up all future net benefits discounted to today minus the "
                "investment: above zero, the plant earns more than the discount rate."
            ),
            "assumptions": (
                "Constant energy and prices in real terms, no degradation, taxes, incentives, "
                "financing or inverter/turbine replacement. The energy used on site is "
                "min(production, demand) over the year; the hour-by-hour overlap is not "
                "evaluated, so the saving is optimistic where production is not simultaneous "
                "with consumption."
            ),
            "reference": "Short, Packey & Holt (1995), NREL/TP-462-5173; IRENA, Renewable Power "
                         "Generation Costs.",
        },
        f"{prefix}.sensitivity": {
            "title": "Which assumption matters most?",
            "formula": "NPV recomputed with each input moved by -20 % and +20 %, one at a time",
            "why": (
                "Prices, costs and the resource are all uncertain. Moving one input at a time "
                "and watching the net present value shows which of them the conclusion depends "
                "on: the longest bar is the number to check first, and the spider chart shows "
                "whether the response is steep or flat. If the NPV changes sign inside the "
                "range, the investment is not robust to that input."
            ),
            "assumptions": (
                "One at a time and +/-20 % only: inputs that move together (for example a "
                "higher electricity price and a higher export price) are not combined, and the "
                f"{unit} is held fixed while the costs change."
            ),
            "reference": "Saltelli et al., Global Sensitivity Analysis: The Primer (2008), ch. 2.",
        },
    }


PV_ECON_EXPLANATIONS = _econ("pv", "installed power", "PV plant")
WIND_ECON_EXPLANATIONS = _econ("wind", "installed power", "wind plant")
PV_ECON_ORDER: tuple[str, ...] = ("pv.economics", "pv.sensitivity")
WIND_ECON_ORDER: tuple[str, ...] = ("wind.economics", "wind.sensitivity")
