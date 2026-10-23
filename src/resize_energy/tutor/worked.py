"""Worked examples: the formula of each topic filled in with the user's own numbers."""

from __future__ import annotations

import math

from resize_energy.core import pv
from resize_energy.core.pv_design import PVDesign, PVInputs
from resize_energy.core.pv_extra import battery_view
from resize_energy.tutor.econ_support import worked_economics


def worked_example(key: str, inp: PVInputs, design: PVDesign) -> str | None:
    """Plain-text substitution of the user's values into the formula, or None if unknown."""
    m, inv = inp.module, inp.inverter
    h = inp.annual_irradiation_kwh_m2
    pr = inp.performance_ratio
    t_min, t_hot = inp.t_min_c, inp.t_cell_max_c

    if key == "pv.irradiation":
        return (
            f"H = {h:,.0f} kWh/m2 per year\n"
            f"Equivalent full-power hours = H / (1 kW/m2) = {h:,.0f} h"
        )

    if key == "pv.performance_ratio":
        if inp.shading_loss > 0:
            return (
                f"PR = {pr:.2f}; with shading {inp.shading_loss:.1%}: "
                f"{pr:.2f} x (1 - {inp.shading_loss:.3f}) = {design.performance_ratio_effective:.3f}\n"
                f"Specific yield = H x PR = {h:,.0f} x {design.performance_ratio_effective:.3f} = "
                f"{design.specific_yield_kwh_per_kwp:,.0f} kWh/kWp"
            )
        return (
            f"PR = {pr:.2f}\n"
            f"Specific yield = H x PR = {h:,.0f} x {pr:.2f} = "
            f"{design.specific_yield_kwh_per_kwp:,.0f} kWh/kWp"
        )

    if key == "pv.shading":
        if inp.shading_loss <= 0:
            return "No obstacle: no shading loss."
        return (f"Shading loss {inp.shading_loss:.1%} of the yearly energy -> "
                f"{design.annual_energy_kwh:,.0f} kWh instead of "
                f"{design.annual_energy_kwh / (1 - inp.shading_loss):,.0f} kWh")

    if key == "pv.monthly" and design.monthly_kwh:
        best = max(range(12), key=lambda i: design.monthly_kwh[i])
        worst = min(range(12), key=lambda i: design.monthly_kwh[i])
        names = "JFMAMJJASOND"
        return (f"Best month ({names[best]}): {design.monthly_kwh[best]:,.0f} kWh; worst "
                f"({names[worst]}): {design.monthly_kwh[worst]:,.0f} kWh; flat demand "
                f"{inp.annual_demand_kwh / 12:,.0f} kWh a month")

    if key == "pv.battery":
        b = battery_view(inp.latitude_deg, inp.annual_demand_kwh, design.dc_power_kwp,
                         design.specific_yield_kwh_per_kwp)
        return (f"Battery {b.capacity_kwh:.1f} kWh: self-sufficiency "
                f"{b.self_sufficiency_without:.0%} -> {b.self_sufficiency:.0%}, self-consumption "
                f"{b.self_consumption_without:.0%} -> {b.self_consumption:.0%}; net present "
                f"value of the battery {b.npv:,.0f} euro")

    if key == "pv.required_peak_power":
        return (
            f"P = {inp.coverage:.0%} x {inp.annual_demand_kwh:,.0f} kWh / "
            f"({h:,.0f} kWh/m2 x {pr:.2f}) = {design.target_kwp:.2f} kWp\n"
            f"Modules = {design.target_kwp:.2f} kWp / {m.p_stc_w:.0f} Wp, rounded up = "
            f"{design.modules_target}"
        )

    if key == "pv.temperature_extremes":
        voc_cold = pv.module_voltage_at_temperature(m.voc_v, m.temp_coeff_voc_pct_per_c, t_min)
        vmp_hot = pv.module_voltage_at_temperature(m.vmp_v, m.temp_coeff_vmp_pct_per_c, t_hot)
        return (
            f"T_min = {t_min:.0f} degC, T_cell,max = {t_hot:.0f} degC\n"
            f"Voc goes from {m.voc_v:.2f} V (25 degC) to {voc_cold:.2f} V at T_min\n"
            f"Vmp goes from {m.vmp_v:.2f} V (25 degC) to {vmp_hot:.2f} V at T_cell,max"
        )

    if key == "pv.max_modules_per_string":
        beta = m.temp_coeff_voc_pct_per_c
        voc_cold = pv.module_voltage_at_temperature(m.voc_v, beta, t_min)
        n = pv.max_modules_per_string(inv.vdc_max_v, m.voc_v, beta, t_min)
        return (
            f"Voc({t_min:.0f} degC) = {m.voc_v:.2f} x (1 + ({beta:.2f}/100) x "
            f"({t_min:.0f} - 25)) = {voc_cold:.2f} V\n"
            f"N_max = floor({inv.vdc_max_v:.0f} V / {voc_cold:.2f} V) = {n}"
        )

    if key == "pv.mppt_window_cold":
        beta = m.temp_coeff_vmp_pct_per_c
        vmp_cold = pv.module_voltage_at_temperature(m.vmp_v, beta, t_min)
        n = pv.max_modules_for_mppt_window(inv.mppt_vmax_v, m.vmp_v, beta, t_min)
        return (
            f"Vmp({t_min:.0f} degC) = {vmp_cold:.2f} V\n"
            f"N_max,mppt = floor({inv.mppt_vmax_v:.0f} V / {vmp_cold:.2f} V) = {n}\n"
            f"Upper limit used = min(voltage limit, MPPT limit) = {design.n_series_max}"
        )

    if key == "pv.min_modules_per_string":
        beta = m.temp_coeff_vmp_pct_per_c
        vmp_hot = pv.module_voltage_at_temperature(m.vmp_v, beta, t_hot)
        n = pv.min_modules_per_string(inv.mppt_vmin_v, m.vmp_v, beta, t_hot)
        return (
            f"Vmp({t_hot:.0f} degC) = {vmp_hot:.2f} V\n"
            f"N_min = ceil({inv.mppt_vmin_v:.0f} V / {vmp_hot:.2f} V) = {n}"
        )

    if key == "pv.string_layout":
        per_mppt = max(1, math.floor(inv.imax_per_mppt_a / m.isc_a))
        lines = [
            f"Admissible string length: {design.n_series_min} to {design.n_series_max}",
            f"Strings per MPPT = floor({inv.imax_per_mppt_a:.1f} A / {m.isc_a:.2f} A) = {per_mppt}; "
            f"MPPT inputs = {inv.n_mppt}; maximum strings = {design.string_capacity}",
        ]
        if design.feasible:
            lines.append(
                f"Target {design.modules_target} modules -> chosen {design.n_series} in series x "
                f"{design.n_parallel} in parallel = {design.n_modules} modules"
            )
        else:
            lines.append("No valid string length exists for this module and inverter pair.")
        return "\n".join(lines)

    if key == "pv.dc_ac_ratio":
        return (
            f"DC/AC = {design.dc_power_kwp:.2f} kWp / {inv.p_ac_kw:.1f} kW = "
            f"{design.dc_ac_ratio:.2f}"
        )

    if key == "pv.annual_energy":
        text = (
            f"E = {design.dc_power_kwp:.2f} kWp x {h:,.0f} kWh/m2 x {pr:.2f} = "
            f"{design.annual_energy_kwh:,.0f} kWh per year"
        )
        if inp.annual_demand_kwh > 0:
            text += (
                f"\nThis covers {design.achieved_coverage:.0%} of the "
                f"{inp.annual_demand_kwh:,.0f} kWh demand"
            )
        return text

    if key in ("pv.economics", "pv.sensitivity"):
        return worked_economics(key, inp.economics, design.economics, design.dc_power_kwp,
                                inp.annual_demand_kwh)

    return None
