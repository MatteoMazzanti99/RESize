"""Typical energy prices and grid emissions of 61 countries.

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
_R = ("electricity", "gas", _EXPORT)
_COUNTRIES: tuple[Country, ...] = (
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
    # --- added later: round values from memory of Eurostat and GlobalPetrolPrices, to be checked
    Country("AL", "Albania", 0.110, 0.05, 0.090, 30, _R),
    Country("AR", "Argentina", 0.070, 0.04, 0.025, 320, _R),
    Country("AT", "Austria", 0.310, 0.08, 0.115, 110, _R),
    Country("BE", "Belgium", 0.330, 0.05, 0.110, 150, _R),
    Country("BA", "Bosnia and Herzegovina", 0.110, 0.05, 0.060, 600, _R),
    Country("BG", "Bulgaria", 0.120, 0.05, 0.070, 330, _R),
    Country("CL", "Chile", 0.200, 0.08, 0.090, 280, _R),
    Country("HR", "Croatia", 0.160, 0.08, 0.060, 200, _R),
    Country("CY", "Cyprus", 0.300, 0.05, 0.120, 560, _R),
    Country("CZ", "Czechia", 0.270, 0.06, 0.090, 330, _R),
    Country("DK", "Denmark", 0.340, 0.05, 0.140, 120, _R),
    Country("EG", "Egypt", 0.035, 0.02, 0.020, 450, _R),
    Country("EE", "Estonia", 0.270, 0.06, 0.090, 220, _R),
    Country("FI", "Finland", 0.220, 0.05, 0.110, 55, _R),
    Country("GR", "Greece", 0.320, 0.07, 0.110, 280, _R),
    Country("HU", "Hungary", 0.100, 0.06, 0.040, 190, _R),
    Country("IS", "Iceland", 0.150, 0.06, 0.100, 28, _R),
    Country("ID", "Indonesia", 0.100, 0.05, 0.040, 680, _R),
    Country("IE", "Ireland", 0.380, 0.13, 0.120, 270, _R),
    Country("IL", "Israel", 0.170, 0.06, 0.070, 450, _R),
    Country("XK", "Kosovo", 0.090, 0.05, 0.080, 700, _R),
    Country("LV", "Latvia", 0.270, 0.06, 0.100, 100, _R),
    Country("LT", "Lithuania", 0.240, 0.06, 0.090, 90, _R),
    Country("LU", "Luxembourg", 0.250, 0.08, 0.080, 90, _R),
    Country("MT", "Malta", 0.130, 0.105, 0.090, 400, _R),
    Country("MD", "Moldova", 0.140, 0.05, 0.060, 450, _R),
    Country("ME", "Montenegro", 0.120, 0.05, 0.080, 400, _R),
    Country("MA", "Morocco", 0.120, 0.05, 0.080, 600, _R),
    Country("NZ", "New Zealand", 0.220, 0.08, 0.090, 100, _R),
    Country("MK", "North Macedonia", 0.110, 0.05, 0.070, 550, _R),
    Country("NO", "Norway", 0.140, 0.08, 0.100, 30, _R),
    Country("PT", "Portugal", 0.260, 0.06, 0.110, 100, _R),
    Country("RO", "Romania", 0.280, 0.07, 0.050, 230, _R),
    Country("SA", "Saudi Arabia", 0.050, 0.03, 0.020, 560, _R),
    Country("RS", "Serbia", 0.120, 0.05, 0.050, 500, _R),
    Country("SK", "Slovakia", 0.220, 0.06, 0.080, 110, _R),
    Country("SI", "Slovenia", 0.230, 0.06, 0.100, 200, _R),
    Country("SE", "Sweden", 0.210, 0.06, 0.150, 40, _R),
    Country("CH", "Switzerland", 0.290, 0.10, 0.120, 40, _R),
    Country("TH", "Thailand", 0.110, 0.05, 0.060, 480, _R),
    Country("UA", "Ukraine", 0.070, 0.04, 0.030, 200, _R),
    Country("AE", "United Arab Emirates", 0.080, 0.04, 0.040, 400, _R),
    Country("VN", "Vietnam", 0.080, 0.05, 0.050, 450, _R),
)
COUNTRIES = tuple(sorted(_COUNTRIES, key=lambda c: c.name))


def get_country(code: str) -> Country:
    for c in COUNTRIES:
        if c.code == code:
            return c
    raise KeyError(code)
