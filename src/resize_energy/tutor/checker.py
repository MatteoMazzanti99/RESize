"""Deterministic design checker: works offline, no AI, repeatable results."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from resize_energy.core.pv_design import PVDesign, PVInputs

Severity = Literal["error", "warning", "info", "ok"]


@dataclass(frozen=True)
class Finding:
    severity: Severity
    code: str
    message: str
    explanation_key: str | None = None


def check_pv_design(inp: PVInputs, design: PVDesign) -> list[Finding]:
    """Check a PV design against common sizing rules. Returns one finding per rule."""
    out: list[Finding] = []
    inv = inp.inverter
    mod = inp.module

    # 1. String length window
    if not design.feasible:
        out.append(Finding(
            "error", "string_window",
            f"No valid string length: the minimum ({design.n_series_min} modules) exceeds the "
            f"maximum ({design.n_series_max}). Choose a module/inverter pair with a wider "
            "voltage window.",
            "pv.max_modules_per_string",
        ))
    else:
        out.append(Finding(
            "ok", "string_window",
            f"String length {design.n_series} is inside the admissible range "
            f"{design.n_series_min}-{design.n_series_max}.",
            "pv.max_modules_per_string",
        ))

    # 2. Absolute voltage limit (cold Voc)
    if design.voc_cold_string_v > inv.vdc_max_v:
        out.append(Finding(
            "error", "voc_cold",
            f"Cold open-circuit voltage {design.voc_cold_string_v:.0f} V exceeds the inverter "
            f"limit {inv.vdc_max_v:.0f} V: the inverter could be damaged.",
            "pv.max_modules_per_string",
        ))
    elif design.voc_cold_string_v > 0.95 * inv.vdc_max_v:
        out.append(Finding(
            "warning", "voc_cold",
            f"Cold open-circuit voltage {design.voc_cold_string_v:.0f} V is within 5% of the "
            f"inverter limit ({inv.vdc_max_v:.0f} V): little safety margin.",
            "pv.max_modules_per_string",
        ))

    # 3. MPPT window at the temperature extremes
    if design.vmp_hot_string_v < inv.mppt_vmin_v:
        out.append(Finding(
            "error", "mppt_low",
            f"Hot-weather Vmp {design.vmp_hot_string_v:.0f} V falls below the MPPT minimum "
            f"{inv.mppt_vmin_v:.0f} V: energy is lost on hot days.",
            "pv.min_modules_per_string",
        ))
    if design.vmp_cold_string_v > inv.mppt_vmax_v:
        out.append(Finding(
            "warning", "mppt_high",
            f"Cold-weather Vmp {design.vmp_cold_string_v:.0f} V exceeds the MPPT maximum "
            f"{inv.mppt_vmax_v:.0f} V: the inverter will clip or limit power on cold days.",
            "pv.mppt_window_cold",
        ))

    # 4. Current per MPPT input
    strings_per_mppt = math.ceil(design.n_parallel / max(1, inv.n_mppt))
    current = strings_per_mppt * mod.isc_a
    if current > inv.imax_per_mppt_a:
        out.append(Finding(
            "error", "mppt_current",
            f"{strings_per_mppt} string(s) per MPPT give {current:.1f} A short-circuit current, "
            f"above the input limit {inv.imax_per_mppt_a:.1f} A.",
            "pv.string_layout",
        ))

    # 5. DC/AC ratio
    r = design.dc_ac_ratio
    if r < 1.0:
        out.append(Finding(
            "warning", "dc_ac",
            f"DC/AC ratio {r:.2f} < 1.0: the inverter is oversized and costs more per kWh.",
            "pv.dc_ac_ratio",
        ))
    elif r > 1.5:
        out.append(Finding(
            "error", "dc_ac",
            f"DC/AC ratio {r:.2f} > 1.5: expect heavy clipping losses.",
            "pv.dc_ac_ratio",
        ))
    elif r > 1.3:
        out.append(Finding(
            "warning", "dc_ac",
            f"DC/AC ratio {r:.2f} > 1.3: noticeable clipping losses, check them with a "
            "hourly simulation.",
            "pv.dc_ac_ratio",
        ))
    else:
        out.append(Finding(
            "ok", "dc_ac",
            f"DC/AC ratio {r:.2f} is in a typical range (1.0-1.3).",
            "pv.dc_ac_ratio",
        ))

    # 6. Performance ratio plausibility
    pr = inp.performance_ratio
    if pr < 0.6 or pr > 0.9:
        out.append(Finding(
            "warning", "pr_range",
            f"Performance ratio {pr:.2f} is outside the usual 0.70-0.85 range: double-check "
            "the loss assumptions.",
            "pv.required_peak_power",
        ))

    # 7. Coverage actually achieved vs requested
    target_cov = inp.coverage
    if inp.annual_demand_kwh > 0:
        got = design.achieved_coverage
        if got < 0.9 * target_cov:
            out.append(Finding(
                "warning", "coverage_low",
                f"The layout covers {got:.0%} of the demand versus the {target_cov:.0%} "
                "requested: the inverter's current or string limits cap the array size.",
                "pv.required_peak_power",
            ))
        elif got > 1.1 * target_cov and target_cov > 0:
            out.append(Finding(
                "info", "coverage_high",
                f"The layout covers {got:.0%} of the demand versus {target_cov:.0%} requested "
                "(modules come in discrete sizes).",
                "pv.required_peak_power",
            ))
    return out
