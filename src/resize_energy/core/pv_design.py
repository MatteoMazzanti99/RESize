"""Preliminary design of a grid-connected PV plant: array, strings and yield.

Pure calculation, no GUI. The datasheet values (module, inverter) are supplied by the user,
with generic defaults so the wizard works out of the box.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from resize_energy.core import pv


@dataclass(frozen=True)
class ModuleSpec:
    """PV module datasheet values at STC."""

    name: str = "Generic 410 Wp mono"
    p_stc_w: float = 410.0
    voc_v: float = 37.5
    vmp_v: float = 31.5
    isc_a: float = 13.9
    imp_a: float = 13.0
    temp_coeff_voc_pct_per_c: float = -0.27
    temp_coeff_vmp_pct_per_c: float = -0.34
    area_m2: float = 1.95


@dataclass(frozen=True)
class InverterSpec:
    """Inverter datasheet values."""

    name: str = "Generic 4 kW inverter"
    p_ac_kw: float = 4.0
    vdc_max_v: float = 1000.0
    mppt_vmin_v: float = 200.0
    mppt_vmax_v: float = 800.0
    imax_per_mppt_a: float = 26.0
    n_mppt: int = 2


@dataclass(frozen=True)
class PVInputs:
    """All inputs of the preliminary design."""

    annual_demand_kwh: float
    annual_irradiation_kwh_m2: float
    coverage: float = 1.0
    performance_ratio: float = 0.80
    t_min_c: float = -10.0
    t_cell_max_c: float = 70.0
    module: ModuleSpec = field(default_factory=ModuleSpec)
    inverter: InverterSpec = field(default_factory=InverterSpec)


@dataclass(frozen=True)
class PVDesign:
    """Result of the preliminary design."""

    target_kwp: float
    modules_target: int
    n_series_min: int
    n_series_max: int
    string_capacity: int
    feasible: bool
    n_series: int
    n_parallel: int
    n_modules: int
    dc_power_kwp: float
    dc_ac_ratio: float
    annual_energy_kwh: float
    specific_yield_kwh_per_kwp: float
    achieved_coverage: float
    array_area_m2: float
    voc_cold_string_v: float
    vmp_hot_string_v: float
    vmp_cold_string_v: float


def size_pv_system(inp: PVInputs) -> PVDesign:
    """Size array, string layout and expected yield.

    Steps: (1) target peak power from the demand; (2) admissible modules per string from the
    inverter voltage limits at the temperature extremes; (3) pick the string length and the
    number of parallel strings giving a module count closest to the target, within the
    inverter's current capacity.
    """
    mod, inv = inp.module, inp.inverter

    target_kwp = pv.required_peak_power_kwp(
        inp.annual_demand_kwh,
        inp.annual_irradiation_kwh_m2,
        inp.performance_ratio,
        inp.coverage,
    )
    modules_target = max(1, math.ceil(target_kwp * 1000.0 / mod.p_stc_w))

    n_max = min(
        pv.max_modules_per_string(
            inv.vdc_max_v, mod.voc_v, mod.temp_coeff_voc_pct_per_c, inp.t_min_c
        ),
        pv.max_modules_for_mppt_window(
            inv.mppt_vmax_v, mod.vmp_v, mod.temp_coeff_vmp_pct_per_c, inp.t_min_c
        ),
    )
    n_min = pv.min_modules_per_string(
        inv.mppt_vmin_v, mod.vmp_v, mod.temp_coeff_vmp_pct_per_c, inp.t_cell_max_c
    )

    strings_per_mppt = max(1, math.floor(inv.imax_per_mppt_a / mod.isc_a))
    string_capacity = strings_per_mppt * inv.n_mppt

    feasible = n_min <= n_max and n_max >= 1
    if feasible:
        best: tuple[int, int, int] | None = None  # (|error|, -n_series, n_parallel)
        for n_series in range(max(1, n_min), n_max + 1):
            n_parallel = min(string_capacity, max(1, round(modules_target / n_series)))
            error = abs(n_series * n_parallel - modules_target)
            candidate = (error, -n_series, n_parallel)
            if best is None or candidate < best:
                best = candidate
        assert best is not None
        n_series, n_parallel = -best[1], best[2]
    else:
        n_series, n_parallel = max(1, n_min), 1

    n_modules = n_series * n_parallel
    dc_kwp = n_modules * mod.p_stc_w / 1000.0
    h = inp.annual_irradiation_kwh_m2
    energy = dc_kwp * h * inp.performance_ratio
    demand = inp.annual_demand_kwh

    return PVDesign(
        target_kwp=target_kwp,
        modules_target=modules_target,
        n_series_min=n_min,
        n_series_max=n_max,
        string_capacity=string_capacity,
        feasible=feasible,
        n_series=n_series,
        n_parallel=n_parallel,
        n_modules=n_modules,
        dc_power_kwp=dc_kwp,
        dc_ac_ratio=pv.dc_ac_ratio(dc_kwp, inv.p_ac_kw),
        annual_energy_kwh=energy,
        specific_yield_kwh_per_kwp=h * inp.performance_ratio,
        achieved_coverage=(energy / demand) if demand > 0 else float("inf"),
        array_area_m2=n_modules * mod.area_m2,
        voc_cold_string_v=n_series
        * pv.module_voltage_at_temperature(mod.voc_v, mod.temp_coeff_voc_pct_per_c, inp.t_min_c),
        vmp_hot_string_v=n_series
        * pv.module_voltage_at_temperature(
            mod.vmp_v, mod.temp_coeff_vmp_pct_per_c, inp.t_cell_max_c
        ),
        vmp_cold_string_v=n_series
        * pv.module_voltage_at_temperature(mod.vmp_v, mod.temp_coeff_vmp_pct_per_c, inp.t_min_c),
    )
