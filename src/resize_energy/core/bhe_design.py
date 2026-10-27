"""Preliminary design of a vertical closed-loop ground-source field (borehole heat exchangers).

ASHRAE (Kavanaugh and Rafferty) length method for heating and for cooling, the larger length
governs; the number of boreholes follows from the maximum drilling depth and the temperature
penalty of the neighbours is iterated to convergence. Pure calculation, no GUI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from resize_energy.core import bhe
from resize_energy.core import economics as eco

HOURS_PER_YEAR = 8760.0
MONTH_HOURS = 31.0 * 24.0
SECONDS_PER_YEAR = HOURS_PER_YEAR * 3600.0


@dataclass(frozen=True)
class BheInputs:
    # --- building loads (on the building side of the heat pump) ---
    heating_kwh_per_year: float = 120_000.0
    heating_peak_kw: float = 80.0
    cooling_kwh_per_year: float = 60_000.0
    cooling_peak_kw: float = 70.0
    design_month_heating_share: float = 0.20     # of the annual heating energy
    design_month_cooling_share: float = 0.30     # of the annual cooling energy
    # --- heat pump ---
    cop_design: float = 3.8
    cop_seasonal: float = 4.7
    eer_design: float = 3.3
    eer_seasonal: float = 4.1
    fluid_in_heating_c: float = 6.0              # fluid back from the ground, entering the HP
    fluid_out_heating_c: float = 2.0             # fluid leaving the HP, sent to the ground
    fluid_in_cooling_c: float = 28.0             # fluid back from the ground, entering the HP
    fluid_out_cooling_c: float = 32.0            # fluid leaving the HP, sent to the ground
    # --- ground ---
    ground_temp_c: float = 14.0
    ground_conductivity: float = 1.8
    ground_density: float = 2200.0
    ground_cp: float = 1000.0
    # --- borehole ---
    pipe_outer_mm: float = 32.0
    pipe_inner_mm: float = 26.2
    pipe_spacing_mm: float = 45.2
    pipe_conductivity: float = 0.4
    borehole_diameter_mm: float = 150.0
    grout_conductivity: float = 1.2
    short_circuit_factor: float = 1.05
    # --- heat-carrier fluid (water with 25 % propylene glycol) ---
    fluid_cp: float = 3900.0
    fluid_density: float = 1020.0
    fluid_viscosity: float = 0.0045
    fluid_conductivity: float = 0.45
    # --- field ---
    spacing_m: float = 6.0
    max_depth_m: float = 150.0
    available_area_m2: float = 0.0               # 0 = not checked
    columns: int = 0                             # 0 = about square
    pulse_years: float = 10.0
    storage_years: float = 1.0                   # years of net imbalance ("storage" method)
    penalty_method: str = "neighbours"           # or "storage" (the course formula)
    # --- cost ---
    drilling_eur_per_m: float = 60.0
    life_years: float = 25.0
    discount_rate: float = 0.04
    om_fraction: float = 0.005


@dataclass(frozen=True)
class BheStep:
    penalty_c: float
    length_m: float
    boreholes: int
    error: float                                 # relative change of the length


@dataclass(frozen=True)
class BheDesign:
    length_heating_m: float
    length_cooling_m: float
    length_first_m: float                         # governing length with no penalty
    governing: str
    total_length_m: float
    boreholes: int
    depth_m: float
    columns: int
    rows: int
    area_needed_m2: float
    fits_area: bool | None
    penalty_c: float
    r_b: float
    r_pp: float
    r_gr: float
    r_ga: float
    r_gm: float
    r_gd: float
    plf_heating: float
    plf_cooling: float
    q_annual_w: float                            # net annual load on the ground (+ = extracted)
    q_ground_heating_w: float
    q_ground_cooling_w: float
    flow_per_borehole_kg_s: float
    reynolds: float
    peak_w_per_m: float
    ground_extracted_kwh: float
    ground_injected_kwh: float
    steps: tuple[BheStep, ...]
    capex: float
    om_per_year: float
    warnings: tuple[str, ...]


def _check(i: BheInputs) -> None:
    if i.heating_kwh_per_year < 0 or i.cooling_kwh_per_year < 0:
        raise ValueError("the energies cannot be negative")
    if i.heating_kwh_per_year <= 0 and i.cooling_kwh_per_year <= 0:
        raise ValueError("give a heating demand, a cooling demand, or both")
    for energy, peak, name in ((i.heating_kwh_per_year, i.heating_peak_kw, "heating"),
                               (i.cooling_kwh_per_year, i.cooling_peak_kw, "cooling")):
        if energy > 0 and peak <= 0:
            raise ValueError(f"the {name} peak power must be > 0")
        if energy > peak * HOURS_PER_YEAR:
            raise ValueError(f"the {name} peak is too low for the annual energy "
                             f"(it needs {energy / HOURS_PER_YEAR:,.0f} kW or more)")
    if min(i.cop_design, i.cop_seasonal) <= 1.0 or min(i.eer_design, i.eer_seasonal) <= 0.0:
        raise ValueError("COP must be > 1 and EER > 0")
    if not (0 < i.design_month_heating_share <= 1 and 0 < i.design_month_cooling_share <= 1):
        raise ValueError("the design-month shares must be in (0, 1]")
    if i.fluid_in_heating_c <= i.fluid_out_heating_c:
        raise ValueError("in heating the fluid must come back to the heat pump warmer than it "
                         "leaves it")
    if i.fluid_out_cooling_c <= i.fluid_in_cooling_c:
        raise ValueError("in cooling the fluid must leave the heat pump warmer than it enters")
    if i.spacing_m <= 0 or i.max_depth_m <= 0 or i.pulse_years <= 0:
        raise ValueError("spacing, maximum depth and pulse years must be > 0")
    if i.penalty_method not in ("neighbours", "storage"):
        raise ValueError("penalty method must be 'neighbours' or 'storage'")
    if i.columns < 0 or i.available_area_m2 < 0 or i.storage_years < 0:
        raise ValueError("columns, area and storage years cannot be negative")
    if i.drilling_eur_per_m < 0 or i.om_fraction < 0 or i.life_years <= 0:
        raise ValueError("costs and lifetime must be positive")


def _ground_heat_w(i: BheInputs) -> tuple[float, float]:
    """Peak load on the ground, heating (+) and cooling (-), in W."""
    heating = i.heating_peak_kw * 1000.0 * (1.0 - 1.0 / i.cop_design) \
        if i.heating_kwh_per_year > 0 else 0.0
    cooling = -i.cooling_peak_kw * 1000.0 * (1.0 + 1.0 / i.eer_design) \
        if i.cooling_kwh_per_year > 0 else 0.0
    return heating, cooling


def annual_load_w(i: BheInputs) -> float:
    """Net annual average load on the ground, extraction positive [W]."""
    extracted = i.heating_kwh_per_year * (1.0 - 1.0 / i.cop_seasonal)
    injected = i.cooling_kwh_per_year * (1.0 + 1.0 / i.eer_seasonal)
    return (extracted - injected) * 1000.0 / HOURS_PER_YEAR


def _plf(energy: float, share: float, peak_kw: float) -> float:
    if energy <= 0 or peak_kw <= 0:
        return 0.0
    return min(1.0, energy * share / (peak_kw * MONTH_HOURS))


def _columns(i: BheInputs, n: int) -> int:
    if i.columns > 0:
        return min(i.columns, n)
    return max(1, math.ceil(math.sqrt(n)))


def _flow_per_bore(i: BheInputs, mode: str, q_ground_w: float, n: int) -> float:
    delta = (i.fluid_in_heating_c - i.fluid_out_heating_c if mode == "heating"
             else i.fluid_out_cooling_c - i.fluid_in_cooling_c)
    return abs(q_ground_w) / (i.fluid_cp * delta) / n


NOMINAL_FILM = 1000.0       # W/(m2 K): film coefficient used for the first estimate of n


def _borehole_resistance(i: BheInputs, mass_flow: float | None
                         ) -> tuple[float, float, float, float]:
    """(R_b, R_pp, R_gr, Re) at the given flow in one borehole (None: nominal film)."""
    d_out, d_in = i.pipe_outer_mm / 1000.0, i.pipe_inner_mm / 1000.0
    db, spacing = i.borehole_diameter_mm / 1000.0, i.pipe_spacing_mm / 1000.0
    if mass_flow is None:
        re, h = 0.0, NOMINAL_FILM
    else:
        re = bhe.reynolds(mass_flow, d_in, i.fluid_viscosity)
        pr = i.fluid_cp * i.fluid_viscosity / i.fluid_conductivity
        h = bhe.film_coefficient(re, pr, i.fluid_conductivity, d_in)
    r_pp = bhe.pipe_resistance(d_out, d_in, i.pipe_conductivity, h)
    r_gr = bhe.grout_resistance(db, d_out, spacing, i.grout_conductivity)
    return r_pp + r_gr, r_pp, r_gr, re


def _lengths(i: BheInputs, n: int | None, penalty: float, r_ground: tuple[float, float, float],
             q_a: float, q_h: float, q_c: float, plf_h: float, plf_c: float
             ) -> tuple[float, float, tuple[float, float, float, float]]:
    """(L_heating, L_cooling, resistances of the governing mode) for n boreholes."""
    r_ga, r_gm, r_gd = r_ground
    l_h = l_c = 0.0
    res_h = res_c = (0.0, 0.0, 0.0, 0.0)
    if i.heating_kwh_per_year > 0:
        res_h = _borehole_resistance(
            i, None if n is None else _flow_per_bore(i, "heating", q_h, n))
        t_mean = (i.fluid_in_heating_c + i.fluid_out_heating_c) / 2.0
        l_h = max(0.0, bhe.required_length(q_a, q_h, r_ga, res_h[0], r_gm, r_gd, plf_h,
                                           i.short_circuit_factor, i.ground_temp_c, t_mean,
                                           penalty, True))
    if i.cooling_kwh_per_year > 0:
        res_c = _borehole_resistance(
            i, None if n is None else _flow_per_bore(i, "cooling", q_c, n))
        t_mean = (i.fluid_in_cooling_c + i.fluid_out_cooling_c) / 2.0
        l_c = max(0.0, bhe.required_length(q_a, q_c, r_ga, res_c[0], r_gm, r_gd, plf_c,
                                           i.short_circuit_factor, i.ground_temp_c, t_mean,
                                           penalty, False))
    return l_h, l_c, (res_h if l_h >= l_c else res_c)


def size_bhe_field(i: BheInputs) -> BheDesign:
    _check(i)
    alpha = bhe.thermal_diffusivity(i.ground_conductivity, i.ground_density, i.ground_cp)
    r_ground = bhe.ground_resistances(i.ground_conductivity, alpha,
                                      i.borehole_diameter_mm / 1000.0, i.pulse_years)
    q_a = annual_load_w(i)
    q_h, q_c = _ground_heat_w(i)
    plf_h = _plf(i.heating_kwh_per_year, i.design_month_heating_share, i.heating_peak_kw)
    plf_c = _plf(i.cooling_kwh_per_year, i.design_month_cooling_share, i.cooling_peak_kw)
    svc = i.ground_density * i.ground_cp
    q_stored = q_a * SECONDS_PER_YEAR * i.storage_years

    penalty = 0.0
    l_h, l_c, res = _lengths(i, None, penalty, r_ground, q_a, q_h, q_c, plf_h, plf_c)
    n = max(1, math.ceil(max(l_h, l_c) / i.max_depth_m))
    l_h, l_c, res = _lengths(i, n, penalty, r_ground, q_a, q_h, q_c, plf_h, plf_c)
    length = max(l_h, l_c)
    first = length
    steps = [BheStep(0.0, length, max(1, math.ceil(length / i.max_depth_m)), 0.0)]
    converged = False
    for _ in range(100):
        n = max(1, math.ceil(length / i.max_depth_m))
        cols = _columns(i, n)
        depth = max(length / n, 1.0)
        if i.penalty_method == "storage":
            target = bhe.temperature_penalty(
                n, cols, bhe.theta_p1(q_stored, svc, i.spacing_m, depth)) if q_stored else 0.0
        else:
            target = bhe.line_source_penalty(n, cols, i.spacing_m, alpha, i.ground_conductivity,
                                             i.pulse_years, q_a / length if length > 0 else 0.0)
        penalty = 0.5 * (penalty + target)              # damped: keeps the iteration stable
        l_h, l_c, res = _lengths(i, n, penalty, r_ground, q_a, q_h, q_c, plf_h, plf_c)
        new = max(l_h, l_c)
        err = abs(new - length) / length if length > 0 else 0.0
        n_new = max(1, math.ceil(new / i.max_depth_m))
        steps.append(BheStep(penalty, new, n_new, err))
        length = new
        if err < 1e-4 and n_new == n and abs(penalty - target) < 1e-3:
            converged = True
            break
    n = max(1, math.ceil(length / i.max_depth_m))
    cols = _columns(i, n)
    rows = math.ceil(n / cols)
    depth = length / n
    governing = "heating" if l_h >= l_c else "cooling"
    area = n * i.spacing_m ** 2
    fits = None if i.available_area_m2 <= 0 else area <= i.available_area_m2
    gov_flow = _flow_per_bore(i, governing, q_h if governing == "heating" else q_c, n)
    r_b, r_pp, r_gr, re = res
    peak_ground = max(abs(q_h), abs(q_c))
    capex = length * i.drilling_eur_per_m
    notes: list[str] = []
    if not converged:
        notes.append("the iteration on the temperature penalty did not settle: the yearly "
                     "heat imbalance of the ground is too large for this field")
    if re < 2300.0:
        notes.append("the flow in the pipes is laminar (Re < 2300): the borehole resistance is "
                     "high; a higher flow or a thinner pipe helps")
    if depth > 150.0:
        notes.append("boreholes deeper than 150 m need a full authorisation in several "
                     "regions: check the local rules")
    if fits is False:
        notes.append(f"the field needs {area:,.0f} m2 but only {i.available_area_m2:,.0f} m2 "
                     "are available: use deeper boreholes, a smaller spacing or less load")
    if abs(q_a) * 8.76 > 0.30 * max(i.heating_kwh_per_year * (1.0 - 1.0 / i.cop_seasonal),
                                    i.cooling_kwh_per_year * (1.0 + 1.0 / i.eer_seasonal)):
        notes.append("the yearly heat balance of the ground is far from zero: the ground "
                     "drifts in temperature over the years")
    return BheDesign(
        length_heating_m=l_h, length_cooling_m=l_c, length_first_m=first, governing=governing,
        total_length_m=length, boreholes=n, depth_m=depth, columns=cols, rows=rows,
        area_needed_m2=area, fits_area=fits, penalty_c=penalty, r_b=r_b, r_pp=r_pp, r_gr=r_gr,
        r_ga=r_ground[0], r_gm=r_ground[1], r_gd=r_ground[2], plf_heating=plf_h,
        plf_cooling=plf_c, q_annual_w=q_a, q_ground_heating_w=q_h, q_ground_cooling_w=q_c,
        flow_per_borehole_kg_s=gov_flow, reynolds=re,
        peak_w_per_m=peak_ground / length if length > 0 else 0.0,
        ground_extracted_kwh=i.heating_kwh_per_year * (1.0 - 1.0 / i.cop_seasonal),
        ground_injected_kwh=i.cooling_kwh_per_year * (1.0 + 1.0 / i.eer_seasonal),
        steps=tuple(steps), capex=capex, om_per_year=capex * i.om_fraction,
        warnings=tuple(notes))


def annualised_cost(d: BheDesign, i: BheInputs) -> float:
    """Yearly cost of the field: CAPEX x CRF + O&M [euro]."""
    return d.capex * eco.capital_recovery_factor(i.discount_rate, i.life_years) + d.om_per_year
