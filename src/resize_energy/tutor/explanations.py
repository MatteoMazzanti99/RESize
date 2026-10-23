"""'Why?' texts shown next to each calculation. Offline, no AI required.

Each entry has: title, formula, why, assumptions and (optional) reference.
References are standards or datasets to look up; check the current edition before citing.
"""

from __future__ import annotations

EXPLANATIONS: dict[str, dict[str, str]] = {
    "pv.irradiation": {
        "title": "Solar resource: in-plane irradiation H",
        "formula": "H = annual solar energy on the tilted module plane [kWh/m2 per year]",
        "why": (
            "Everything starts from how much sunlight reaches the modules. Tilt and azimuth "
            "change it: for Italy, modules facing south at about 30 degrees collect close to "
            "the maximum over the year. Because modules are rated at 1 kW/m2, H is numerically "
            "the number of 'equivalent full-power hours' per year, so it converts kWp into kWh."
        ),
        "assumptions": (
            "A typical-year average is used; real years vary by a few percent. Shading by "
            "buildings, trees or terrain is not included unless it is in the PVGIS horizon."
        ),
        "reference": "PVGIS (European Commission, Joint Research Centre), PVcalc tool.",
    },
    "pv.performance_ratio": {
        "title": "Performance ratio PR",
        "formula": "PR = E_ac / (P_dc,kWp * H)    ->    specific yield = H * PR  [kWh/kWp]",
        "why": (
            "PR is the share of the ideal energy that actually reaches the AC side. It groups "
            "all losses: cell temperature, reflection, soiling, mismatch, cables, inverter. "
            "Well-designed plants are typically between 0.75 and 0.85; hot sites and "
            "poor ventilation push it down."
        ),
        "assumptions": "A single constant value for the whole year; no degradation over the years.",
        "reference": "IEC 61724-1 (PV system performance monitoring), definition of PR.",
    },
    "pv.required_peak_power": {
        "title": "Required PV peak power",
        "formula": "P_kWp = coverage * E_demand / (H * PR)",
        "why": (
            "Modules are rated at STC (1 kW/m2). Over a year a 1 kWp array receives H kWh/m2 "
            "of in-plane irradiation, i.e. H 'equivalent full-power hours', and delivers a "
            "fraction PR of it after losses (temperature, soiling, wiring, inverter...). "
            "Dividing the target energy by H * PR gives the kWp to install."
        ),
        "assumptions": "PR is assumed constant over the year; self-consumption and storage are ignored.",
    },
    "pv.temperature_extremes": {
        "title": "Temperature extremes",
        "formula": "V(T) = V_stc * (1 + beta * (T - 25)),   beta in %/degC (negative for silicon)",
        "why": (
            "Module voltage depends on cell temperature: higher when cold, lower when hot. "
            "The string must be safe at the coldest morning (T_min) and still work at the "
            "hottest cell temperature (T_cell,max, usually 65-70 degC on a sunny summer day, "
            "much higher than the ambient air)."
        ),
        "assumptions": "T_min is the lowest expected ambient temperature at the site (e.g. -10 degC).",
        "reference": "IEC 62548 (PV array design requirements), voltage correction at minimum temperature.",
    },
    "pv.max_modules_per_string": {
        "title": "Maximum modules per string",
        "formula": "N_max = floor(Vdc,max / Voc(T_min)),  Voc(T) = Voc,stc * (1 + beta * (T - 25))",
        "why": (
            "Voc rises as the cell gets colder. On the coldest morning, with no load, the "
            "string voltage must remain below the inverter's absolute maximum DC voltage "
            "or the device can be damaged."
        ),
        "assumptions": "Linear temperature coefficient; T_min taken from site climate data.",
        "reference": "IEC 62548 (PV array design requirements).",
    },
    "pv.min_modules_per_string": {
        "title": "Minimum modules per string",
        "formula": "N_min = ceil(V_mppt,min / Vmp(T_cell,max))",
        "why": (
            "Vmp drops when cells are hot. At the hottest operating point the string must "
            "still sit inside the inverter's MPPT window, otherwise it loses tracking and energy."
        ),
        "assumptions": "T_cell,max typically 65-70 degC for ground/roof mounting.",
    },
    "pv.mppt_window_cold": {
        "title": "MPPT window at low temperature",
        "formula": "N_max,mppt = floor(V_mppt,max / Vmp(T_min))",
        "why": (
            "Vmp is higher on cold days too. If the string's working voltage rises above the "
            "top of the MPPT window the inverter cannot track the maximum power point and "
            "limits the output, so the string length is capped by this as well."
        ),
        "assumptions": "Linear temperature coefficient for Vmp; T_min from site climate data.",
    },
    "pv.string_layout": {
        "title": "String layout (series and parallel)",
        "formula": (
            "strings per MPPT = floor(I_max,MPPT / Isc);   N_modules = N_series * N_parallel"
        ),
        "why": (
            "Modules in series add their voltages (limited by the window above); strings in "
            "parallel add their currents (limited by each MPPT input of the inverter, checked "
            "against the short-circuit current Isc). The program picks the combination whose "
            "module count is closest to the target, preferring longer strings (fewer cables)."
        ),
        "assumptions": (
            "All strings equal and equally oriented; a real plant may split orientations "
            "across different MPPT inputs."
        ),
    },
    "pv.dc_ac_ratio": {
        "title": "DC/AC ratio",
        "formula": "DC/AC = P_dc,kWp / P_ac,kW",
        "why": (
            "The array rarely produces its rated power, so the inverter can be slightly "
            "undersized. A ratio of about 1.1-1.3 trades small clipping losses for a lower "
            "cost per kWh."
        ),
        "assumptions": "Optimal value depends on tilt, climate and tariff structure.",
    },
    "pv.annual_energy": {
        "title": "Expected annual energy",
        "formula": "E = P_dc,kWp * H * PR",
        "why": (
            "With the installed (not the target) power, this is the energy the plant is expected "
            "to deliver in a typical year, and the share of the demand it covers. The installed "
            "power differs from the target because modules come in whole units."
        ),
        "assumptions": (
            "Yearly totals only: how much of this energy is used on site, versus exported, "
            "depends on the hourly load profile and is not evaluated here."
        ),
    },
}

# Order in which the topics follow the design steps (used by the GUI panel and the report).
TOPIC_ORDER: tuple[str, ...] = (
    "pv.irradiation",
    "pv.performance_ratio",
    "pv.required_peak_power",
    "pv.temperature_extremes",
    "pv.max_modules_per_string",
    "pv.mppt_window_cold",
    "pv.min_modules_per_string",
    "pv.string_layout",
    "pv.dc_ac_ratio",
    "pv.annual_energy",
)


# The wind module keeps its texts in its own file; they share the same lookup table.
from resize_energy.tutor.explanations_wind import WIND_EXPLANATIONS  # noqa: E402

EXPLANATIONS.update(WIND_EXPLANATIONS)

# Same for the technology comparison (economics and carbon).
from resize_energy.tutor.explanations_compare import COMPARE_EXPLANATIONS  # noqa: E402

EXPLANATIONS.update(COMPARE_EXPLANATIONS)

# And for the biomass module.
from resize_energy.tutor.explanations_biomass import BIOMASS_EXPLANATIONS  # noqa: E402

EXPLANATIONS.update(BIOMASS_EXPLANATIONS)

# And for the green hydrogen module.
from resize_energy.tutor.explanations_hydrogen import HYDROGEN_EXPLANATIONS  # noqa: E402

EXPLANATIONS.update(HYDROGEN_EXPLANATIONS)

# And for the battery storage module.
from resize_energy.tutor.explanations_battery import BATTERY_EXPLANATIONS  # noqa: E402

EXPLANATIONS.update(BATTERY_EXPLANATIONS)
