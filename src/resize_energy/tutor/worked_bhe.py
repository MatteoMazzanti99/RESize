"""Worked examples of the borehole-field topics, with the user's own numbers."""

from __future__ import annotations

import math

from resize_energy.core import bhe
from resize_energy.core import economics as eco
from resize_energy.core.bhe_design import BheDesign, BheInputs


def bhe_worked_example(key: str, inp: BheInputs, d: BheDesign) -> str | None:
    if key == "bhe.loads":
        lines = []
        if inp.heating_kwh_per_year > 0:
            lines.append(f"Heating: {inp.heating_peak_kw:,.0f} x (1 - 1/{inp.cop_design}) = "
                         f"{d.q_ground_heating_w / 1000:,.1f} kW from the ground")
        if inp.cooling_kwh_per_year > 0:
            lines.append(f"Cooling: {inp.cooling_peak_kw:,.0f} x (1 + 1/{inp.eer_design}) = "
                         f"{-d.q_ground_cooling_w / 1000:,.1f} kW into the ground")
        lines.append(f"Q_a = ({d.ground_extracted_kwh:,.0f} - {d.ground_injected_kwh:,.0f}) / 8760 = "
                     f"{d.q_annual_w / 1000:,.2f} kW "
                     f"({'heat taken out' if d.q_annual_w >= 0 else 'heat stored in the ground'})")
        return "\n".join(lines)
    if key == "bhe.length":
        gov = d.governing
        return (f"L_heating = {d.length_heating_m:,.0f} m;  L_cooling = {d.length_cooling_m:,.0f} m\n"
                f"The {gov} case governs: L = {d.total_length_m:,.0f} m "
                f"(without the penalty: {d.length_first_m:,.0f} m)\n"
                f"R_b = {d.r_b:.3f},  R_ga = {d.r_ga:.3f},  R_gm = {d.r_gm:.3f},  "
                f"R_gd = {d.r_gd:.3f} m K/W;  PLF = {d.plf_heating:.2f} (heating), "
                f"{d.plf_cooling:.2f} (cooling);  F_sc = {inp.short_circuit_factor}")
    if key == "bhe.ground":
        alpha = bhe.thermal_diffusivity(inp.ground_conductivity, inp.ground_density,
                                        inp.ground_cp)
        day = 86400.0
        tau_f = (inp.pulse_years * 365.0 + bhe.MONTH_DAYS + bhe.DAY_PULSE_DAYS) * day
        fo = bhe.fourier_number(alpha, tau_f, inp.borehole_diameter_mm / 1000.0)
        return (f"alpha = {inp.ground_conductivity} / ({inp.ground_density:,.0f} x "
                f"{inp.ground_cp:,.0f}) = {alpha:.3e} m2/s\n"
                f"Fo_f = 4 x {alpha:.3e} x {tau_f:,.0f} s / {inp.borehole_diameter_mm / 1000:.3f}^2 = "
                f"{fo:.1f};  G_f = {bhe.g_function(fo):.3f}\n"
                f"R_ga = {d.r_ga:.3f},  R_gm = {d.r_gm:.3f},  R_gd = {d.r_gd:.3f} m K/W")
    if key == "bhe.borehole":
        d_out, d_in = inp.pipe_outer_mm / 1000.0, inp.pipe_inner_mm / 1000.0
        wall = math.log(d_out / d_in) / (2 * math.pi * inp.pipe_conductivity)
        return (f"Flow in each borehole: {d.flow_per_borehole_kg_s:.2f} kg/s, "
                f"Re = {d.reynolds:,.0f} ({'turbulent' if d.reynolds >= 2300 else 'laminar'})\n"
                f"Pipe wall: ln({d_out * 1000:.1f}/{d_in * 1000:.1f}) / (2 pi x "
                f"{inp.pipe_conductivity}) = {wall:.3f} m K/W per leg\n"
                f"R_pp = {d.r_pp:.3f},  R_gr = {d.r_gr:.3f},  R_b = {d.r_b:.3f} m K/W")
    if key == "bhe.penalty":
        steps = ", ".join(f"{s.penalty_c:+.2f}" for s in d.steps[:6])
        extra = "" if len(d.steps) <= 6 else f", ... ({len(d.steps)} steps)"
        n4, n3, n2, n1 = bhe.neighbour_counts(d.boreholes, d.columns)
        return (f"{d.boreholes} boreholes in {d.rows} rows x {d.columns} columns: "
                f"N4 = {n4}, N3 = {n3}, N2 = {n2}, N1 = {n1}\n"
                f"Penalty at each step [K]: {steps}{extra}\n"
                f"Final penalty: {d.penalty_c:+.2f} K "
                f"({'the ground warms' if d.penalty_c < 0 else 'the ground cools'}); "
                f"length {d.length_first_m:,.0f} -> {d.total_length_m:,.0f} m")
    if key == "bhe.field":
        return (f"N = ceil({d.total_length_m:,.0f} / {inp.max_depth_m:,.0f}) = {d.boreholes}\n"
                f"depth = {d.total_length_m:,.0f} / {d.boreholes} = {d.depth_m:,.1f} m\n"
                f"area = {d.boreholes} x {inp.spacing_m}^2 = {d.area_needed_m2:,.0f} m2 "
                f"({d.rows} x {d.columns} grid)")
    if key == "bhe.economics":
        crf = eco.capital_recovery_factor(inp.discount_rate, inp.life_years)
        return (f"CAPEX = {d.total_length_m:,.0f} m x {inp.drilling_eur_per_m:,.0f} euro/m = "
                f"{d.capex:,.0f} euro\n"
                f"CRF = {crf:.4f};  annual cost = {d.capex:,.0f} x {crf:.4f} + "
                f"{d.om_per_year:,.0f} = {d.capex * crf + d.om_per_year:,.0f} euro\n"
                f"{d.total_length_m / (max(abs(d.q_ground_heating_w), abs(d.q_ground_cooling_w)) / 1000):.1f} "
                "m of borehole per kW of peak ground load")
    return None
