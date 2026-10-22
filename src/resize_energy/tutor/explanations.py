"""'Why?' texts shown next to each calculation. Offline, no AI required."""

from __future__ import annotations

EXPLANATIONS: dict[str, dict[str, str]] = {
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
    "pv.max_modules_per_string": {
        "title": "Maximum modules per string",
        "formula": "N_max = floor(Vdc,max / Voc(T_min)),  Voc(T) = Voc,stc * (1 + beta * (T - 25))",
        "why": (
            "Voc rises as the cell gets colder. On the coldest morning, with no load, the "
            "string voltage must remain below the inverter's absolute maximum DC voltage "
            "or the device can be damaged."
        ),
        "assumptions": "Linear temperature coefficient; T_min taken from site climate data.",
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
}
