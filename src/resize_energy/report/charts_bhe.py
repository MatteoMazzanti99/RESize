"""Charts of the borehole-field design (no Qt)."""

from __future__ import annotations

from resize_energy.core.bhe_design import BheDesign, BheInputs
from resize_energy.report.charts import AMBER, BLUE, GREEN, RED, ChartSpec, Series, _scaled


def bhe_charts(inp: BheInputs, d: BheDesign) -> dict[str, ChartSpec]:
    out: dict[str, ChartSpec] = {}
    labels = ["Heating", "Cooling", "Design, with the penalty"]
    values = [d.length_heating_m, d.length_cooling_m, d.total_length_m]
    colors = [RED, BLUE, GREEN]
    out["bhe_lengths"] = ChartSpec(
        "hbars", "Length of borehole needed", tuple(labels),
        (Series("length", tuple(values), colors=tuple(colors)),),
        x_label="Total borehole length [m]", decimals=0,
        caption=f"The {d.governing} case governs. The temperature penalty of the neighbouring "
                f"boreholes lengthens the field from {d.length_first_m:,.0f} to "
                f"{d.total_length_m:,.0f} m.")
    out_kwh = [d.ground_extracted_kwh, d.ground_injected_kwh]
    scaled, unit, dec = _scaled(out_kwh)
    out["bhe_balance"] = ChartSpec(
        "hbars", "Yearly heat exchanged with the ground",
        ("Taken from the ground (heating)", "Given to the ground (cooling)"),
        (Series("energy", scaled, colors=(RED, BLUE)),),
        x_label=f"Energy per year [{unit}]", decimals=dec,
        caption="The closer the two bars, the smaller the drift of the ground temperature "
                "over the years and the shorter the field.")
    if len(d.steps) > 2:
        xs = tuple(float(k) for k in range(len(d.steps)))
        out["bhe_iteration"] = ChartSpec(
            "lines", "Iteration on the temperature penalty", (),
            (Series("total length [m]", tuple(s.length_m for s in d.steps), AMBER, x=xs),),
            x_label="Iteration", y_label="Total length [m]",
            hlines=((d.total_length_m, f"final {d.total_length_m:,.0f} m"),), height=250,
            caption="The length settles when the number of boreholes and the penalty stop "
                    "changing.")
    return out
