"""'Why?' texts of the deeper PV topics (shading, month by month, battery)."""

from __future__ import annotations

PV_EXTRA_EXPLANATIONS: dict[str, dict[str, str]] = {
    "pv.shading": {
        "title": "Shading by a nearby obstacle",
        "formula": "loss = (1 - diffuse share) * beam energy blocked / total energy",
        "why": (
            "A tree, a chimney or a building that rises above the horizon hides the sun when "
            "the sun is low and behind it. You describe it with an angle (how high it appears "
            "above the horizon, seen from the modules) and the range of directions it covers "
            "(0 is south, negative east, positive west). Only the direct light is blocked; the "
            "diffuse light of the sky, about a third of the total, still reaches the modules. "
            "A low obstacle matters little because the sun is low only early and late, when "
            "there is little energy anyway; a tall one to the south can cost a quarter of the year."
        ),
        "assumptions": (
            "A flat band of constant height; clear-sky sun path of the latitude; a fixed diffuse "
            "share of 35 %. The electrical effect of partial shading (bypass diodes, mismatch "
            "between strings) is not modelled: it can make the real loss larger."
        ),
        "reference": "Quaschning and Hanitsch, Numerical simulation of photovoltaic generators with shaded cells, 1995.",
    },
    "pv.monthly": {
        "title": "Production month by month",
        "formula": "E_month = E_year * (clear-sky and cloud weight of the month)",
        "why": (
            "The yearly energy hides a large seasonal swing: at 45 degrees north a PV plant "
            "makes four or five times more in June than in December. Your consumption is "
            "usually flatter, so the plant covers more than 100 % of the demand in summer and "
            "much less in winter. This is why the yearly coverage can be 100 % while you still "
            "buy a lot of electricity in winter."
        ),
        "assumptions": "A typical sun and cloud pattern of the latitude, not a measured year.",
        "reference": "PVGIS monthly outputs (JRC); Duffie and Beckman, Solar Engineering of Thermal Processes.",
    },
    "pv.battery": {
        "title": "What a battery would add",
        "formula": "self-sufficiency = 1 - import / load;  battery = one average day of consumption",
        "why": (
            "Without a battery only the energy produced at the moment you consume it is used "
            "on site; the rest is exported at a low price. A battery of about one day of "
            "consumption moves the midday surplus to the evening. Look at both numbers: "
            "self-sufficiency usually rises a lot, the money gain much less, and with today's "
            "prices the battery often does not repay itself. The Battery module studies "
            "this in detail with the size and the prices you choose."
        ),
        "assumptions": (
            "A typical home load shape, an invented production year, default battery costs "
            "and prices of 0.25 and 0.08 euro/kWh."
        ),
        "reference": "Luthander et al., Applied Energy 2015; see the Battery module for the method.",
    },
}
