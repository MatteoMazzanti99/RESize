"""Typical energy prices and grid emissions of the main countries.

Pure data, no GUI. All money is in euro (dollar figures converted at 1.17 USD/EUR, the ECB
rate of late 2025). The numbers are round, indicative values for a household or small
business in 2025: they replace the generic defaults of the cost pages so that a student in
Italy, Spain or the USA starts from realistic numbers. They are not tariffs: check yours.

Sources
* Household electricity: Eurostat (EU countries, second half of 2025, taxes included) and
  GlobalPetrolPrices (other countries, 2023-2025 average).
* Household natural gas: Eurostat (EU countries, second half of 2025, taxes included).
* Grid carbon intensity: lowcarbonpower.org (latest 12 months, imports included).
* Price paid for the surplus, and gas outside the EU: the author's rounded estimates. The
  export price depends on the local scheme (net metering, feed-in tariff, market price).
"""

from __future__ import annotations

from dataclasses import dataclass

BOILER_EFFICIENCY = 0.90      # backup heat cost = gas price / this efficiency
DATA_YEAR = "2025"


@dataclass(frozen=True)
class Country:
    code: str
    name: str
    electricity_eur_kwh: float      # what a household pays, taxes included
    export_eur_kwh: float           # typical value of the surplus fed to the grid
    gas_eur_kwh: float              # household natural gas, per kWh of gas
    grid_g_co2_kwh: float           # carbon intensity of the grid
    rough: tuple[str, ...] = ()     # which of the numbers above are only rough estimates

    @property
    def heat_eur_kwh(self) -> float:
        """Cost of a kWh of heat from a gas boiler."""
        return self.gas_eur_kwh / BOILER_EFFICIENCY

    @property
    def grid_kg_co2_kwh(self) -> float:
        return self.grid_g_co2_kwh / 1000.0

    @property
    def note(self) -> str:
        text = (f"{self.name}: electricity {self.electricity_eur_kwh:.3f} euro/kWh, surplus "
                f"{self.export_eur_kwh:.3f} euro/kWh, gas {self.gas_eur_kwh:.3f} euro/kWh, grid "
                f"{self.grid_g_co2_kwh:.0f} g CO2/kWh ({DATA_YEAR}).")
        if self.rough:
            text += " Rough estimates: " + ", ".join(self.rough) + "."
        return text


_EXPORT = "price paid for the surplus"
COUNTRIES: tuple[Country, ...] = (
    Country("AU", "Australia", 0.220, 0.05, 0.080, 434, ("gas", _EXPORT)),
    Country("BR", "Brazil", 0.138, 0.10, 0.100, 116, ("gas", _EXPORT)),
    Country("CA", "Canada", 0.106, 0.06, 0.035, 132, ("gas", _EXPORT)),
    Country("CN", "China", 0.065, 0.05, 0.050, 472, ("gas", _EXPORT)),
    Country("FR", "France", 0.266, 0.04, 0.130, 44, (_EXPORT,)),
    Country("DE", "Germany", 0.387, 0.08, 0.122, 296, (_EXPORT,)),
    Country("IN", "India", 0.066, 0.04, 0.050, 586, ("gas", _EXPORT)),
    Country("IT", "Italy", 0.310, 0.11, 0.148, 312, ("electricity", _EXPORT)),
    Country("JP", "Japan", 0.196, 0.08, 0.110, 438, ("gas", _EXPORT)),
    Country("MX", "Mexico", 0.092, 0.05, 0.045, 405, ("gas", _EXPORT)),
    Country("NL", "Netherlands", 0.280, 0.07, 0.172, 290, ("electricity", _EXPORT)),
    Country("PL", "Poland", 0.220, 0.07, 0.085, 514, ("electricity", "gas", _EXPORT)),
    Country("ZA", "South Africa", 0.170, 0.05, 0.080, 660, ("gas", _EXPORT)),
    Country("KR", "South Korea", 0.108, 0.07, 0.065, 437, ("gas", _EXPORT)),
    Country("ES", "Spain", 0.261, 0.06, 0.086, 146, (_EXPORT,)),
    Country("TR", "Turkey", 0.062, 0.05, 0.025, 341, ("gas", _EXPORT)),
    Country("GB", "United Kingdom", 0.344, 0.10, 0.075, 224, ("gas", _EXPORT)),
    Country("US", "United States", 0.158, 0.05, 0.045, 339, ("gas", _EXPORT)),
)


def get_country(code: str) -> Country:
    for c in COUNTRIES:
        if c.code == code:
            return c
    raise KeyError(code)
