"""Building blocks of the vertical closed-loop (borehole heat exchanger) design: ASHRAE method.

Pure functions, no GUI. Lengths in m, temperatures in degC, powers in W, conductivities in
W/(m K), resistances in (m K)/W. Sign convention: heat taken from the ground is positive, heat
given to the ground (cooling) is negative.

The method is the one of Kavanaugh and Rafferty (ASHRAE, 1997): the ground is a cylindrical
source with three heat pulses (10 years of net load, the design month, the design day), each
with its own ground resistance, plus the resistance of the borehole itself.
"""

from __future__ import annotations

import math

# Pulse lengths of the classic method [days]: 10 years, one month, six hours.
YEARS_DAYS = 3650.0
MONTH_DAYS = 30.0
DAY_PULSE_DAYS = 0.25


def thermal_diffusivity(conductivity: float, density: float, cp: float) -> float:
    """alpha = lambda / (rho cp) [m2/s]."""
    if min(conductivity, density, cp) <= 0:
        raise ValueError("conductivity, density and specific heat must be > 0")
    return conductivity / (density * cp)


def g_function(fourier: float) -> float:
    """Line-source fit of the ground response: G = 0.0758 ln(Fo) + 0.1009 (never below 0)."""
    if fourier <= 0:
        raise ValueError("the Fourier number must be > 0")
    return max(0.0, 0.0758 * math.log(fourier) + 0.1009)


def fourier_number(alpha: float, time_s: float, borehole_diameter: float) -> float:
    """Fo = 4 alpha t / Db^2."""
    return 4.0 * alpha * time_s / borehole_diameter ** 2


def ground_resistances(conductivity: float, alpha: float, borehole_diameter: float,
                       years: float = 10.0) -> tuple[float, float, float]:
    """Annual, monthly and daily ground resistances (R_ga, R_gm, R_gd).

    R_ga = (G_f - G_1) / lambda,  R_gm = (G_1 - G_2) / lambda,  R_gd = G_2 / lambda, with the
    Fourier numbers of tau_f = years + 30 d + 6 h, tau_f - tau_1, tau_f - tau_2.
    """
    if borehole_diameter <= 0 or years <= 0:
        raise ValueError("borehole diameter and years must be > 0")
    day = 86400.0
    tau1 = years * 365.0 * day
    tau2 = tau1 + MONTH_DAYS * day
    tau_f = tau2 + DAY_PULSE_DAYS * day
    g_f = g_function(fourier_number(alpha, tau_f, borehole_diameter))
    g_1 = g_function(fourier_number(alpha, tau_f - tau1, borehole_diameter))
    g_2 = g_function(fourier_number(alpha, tau_f - tau2, borehole_diameter))
    return (g_f - g_1) / conductivity, (g_1 - g_2) / conductivity, g_2 / conductivity


def reynolds(mass_flow_kg_s: float, inner_diameter: float, viscosity: float) -> float:
    """Re = 4 m / (pi d mu) for the flow in one pipe of the U-tube."""
    if inner_diameter <= 0 or viscosity <= 0:
        raise ValueError("diameter and viscosity must be > 0")
    return 4.0 * mass_flow_kg_s / (math.pi * inner_diameter * viscosity)


def film_coefficient(re: float, prandtl: float, fluid_conductivity: float,
                     inner_diameter: float) -> float:
    """Inner heat-transfer coefficient h_i [W/(m2 K)]: laminar Nu = 4.36, else Dittus-Boelter."""
    if re < 2300.0:
        nu = 4.36
    else:
        nu = 0.023 * re ** 0.8 * prandtl ** 0.35
    return nu * fluid_conductivity / inner_diameter


def pipe_resistance(d_out: float, d_in: float, pipe_conductivity: float, h_inner: float,
                    n_pipes: int = 2) -> float:
    """R_pp = [ln(de/di) / (2 pi lambda_p) + 1 / (pi di h_i)] / n_pipes."""
    if d_in <= 0 or d_out <= d_in:
        raise ValueError("the outer pipe diameter must exceed the inner one")
    if pipe_conductivity <= 0 or h_inner <= 0 or n_pipes < 1:
        raise ValueError("pipe conductivity, film coefficient and pipe count must be > 0")
    wall = math.log(d_out / d_in) / (2.0 * math.pi * pipe_conductivity)
    film = 1.0 / (math.pi * d_in * h_inner)
    return (wall + film) / n_pipes


def grout_resistance(borehole_diameter: float, d_out: float, spacing: float,
                     grout_conductivity: float) -> float:
    """Resistance of the grout between the pipes and the borehole wall (line-source expression).

    R_gr = 1/(2 pi lambda_gr) [ ln(Db/de) - 3/4 + (D/Db)^2 - 1/4 ln(1 - (D/Db)^8)
                                - 1/2 ln(sqrt2 D/de) - 1/4 ln(2 D/de) ]
    """
    if grout_conductivity <= 0:
        raise ValueError("the grout conductivity must be > 0")
    if not 0 < d_out < borehole_diameter:
        raise ValueError("the pipe must be thinner than the borehole")
    if not d_out < spacing < borehole_diameter:
        raise ValueError("the pipe spacing must fit inside the borehole")
    x = spacing / borehole_diameter
    bracket = (math.log(borehole_diameter / d_out) - 0.75 + x ** 2
               - 0.25 * math.log(1.0 - x ** 8)
               - 0.5 * math.log(math.sqrt(2.0) * spacing / d_out)
               - 0.25 * math.log(2.0 * spacing / d_out))
    return bracket / (2.0 * math.pi * grout_conductivity)


def required_length(q_annual_w: float, q_peak_ground_w: float, r_ga: float, r_b: float,
                    r_gm: float, r_gd: float, plf_month: float, f_sc: float,
                    t_ground: float, t_fluid_mean: float, t_penalty: float,
                    heating: bool = True) -> float:
    """Borehole length [m] for one mode (heating or cooling).

    L = [Qa R_ga + Qg (R_b + PLF R_gm + R_gd F_sc)] / [t_g - t_fluid - t_p]

    q_annual_w is the net annual average load on the ground and q_peak_ground_w the peak load on
    the ground (both positive when heat is taken from the ground). The result is positive for a
    consistent case: a cooling case, with negative loads, has a negative denominator as well.
    """
    denominator = t_ground - t_fluid_mean - t_penalty
    if abs(denominator) < 1e-6 or (denominator > 0) != heating:
        raise ValueError("the fluid temperature (with the ground drift) leaves no usable "
                         "temperature difference to the ground: change the fluid "
                         "temperatures or reduce the yearly heat imbalance")
    numerator = q_annual_w * r_ga + q_peak_ground_w * (r_b + plf_month * r_gm + r_gd * f_sc)
    return numerator / denominator


def neighbour_counts(n: int, columns: int) -> tuple[int, int, int, int]:
    """(N4, N3, N2, N1): boreholes with 4, 3, 2 and 1 neighbours in a grid filled row by row."""
    if n < 1 or columns < 1:
        raise ValueError("need at least one borehole and one column")
    cells = {(k // columns, k % columns) for k in range(n)}
    counts = [0, 0, 0, 0, 0]
    for r, c in cells:
        counts[sum((r + dr, c + dc) in cells
                   for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))] += 1
    return counts[4], counts[3], counts[2], counts[1]


def temperature_penalty(n: int, columns: int, theta_p1: float) -> float:
    """theta_p = (N4 + 0.5 N3 + 0.25 N2 + 0.1 N1) / N * theta_p1."""
    n4, n3, n2, n1 = neighbour_counts(n, columns)
    return (n4 + 0.5 * n3 + 0.25 * n2 + 0.1 * n1) / n * theta_p1


def theta_p1(q_stored_j: float, volumetric_heat_capacity: float, spacing: float,
             depth: float) -> float:
    """Ground temperature drift of a borehole with four neighbours: Q / (S_vc ds^2 L).

    Positive when heat has been taken from the ground (it cools), negative when heat has been
    stored in it (it warms).
    """
    if min(volumetric_heat_capacity, spacing, depth) <= 0:
        raise ValueError("heat capacity, spacing and depth must be > 0")
    return q_stored_j / (volumetric_heat_capacity * spacing ** 2 * depth)


def exp_integral_e1(x: float) -> float:
    """Exponential integral E1(x) for x > 0 (series below 1, continued fraction above)."""
    if x <= 0:
        raise ValueError("E1 needs a positive argument")
    if x < 1.0:
        total, term = -0.5772156649015329 - math.log(x), 1.0
        for k in range(1, 40):
            term *= -x / k
            total -= term / k
        return total
    b, c, d = x + 1.0, 1e300, 1.0 / (x + 1.0)
    h = d
    for k in range(1, 100):
        a = -k * k
        b += 2.0
        d = 1.0 / (a * d + b)
        c = b + a / c
        delta = c * d
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h * math.exp(-x)


def line_source_penalty(n: int, columns: int, spacing: float, alpha: float,
                        conductivity: float, years: float, load_per_m: float) -> float:
    """Temperature penalty from the neighbours [K], positive when the ground is cooled.

    Each borehole is a line source of ``load_per_m`` W/m (positive when heat is taken out);
    the rise at a neighbour at distance d after t years is q/(4 pi lambda) E1(d2/(4 alpha t)).
    The mean over the field of the sum over all the other boreholes is returned.
    """
    if n < 1 or columns < 1 or spacing <= 0 or years <= 0:
        raise ValueError("need boreholes, columns, spacing and years > 0")
    if n == 1 or load_per_m == 0.0:
        return 0.0
    t = years * 365.0 * 86400.0
    # boreholes fill a grid row by row: group the pairs by their offset (rows, columns) so that
    # E1 is evaluated once per offset instead of once per pair
    lens = [min(columns, n - r * columns) for r in range((n + columns - 1) // columns)]
    rows = len(lens)
    total = 0.0
    for dr in range(rows):
        for dc in range(-(columns - 1), columns):
            if dr == 0 and dc == 0:
                continue
            pairs = 0
            for ra in range(rows - dr):
                na, nb = lens[ra], lens[ra + dr]
                pairs += max(0, min(na, nb - dc) - max(0, -dc))
            if pairs == 0:
                continue
            d2 = (dr * spacing) ** 2 + (dc * spacing) ** 2
            weight = 2 if dr > 0 else 1        # the pair (a, b) and the pair (b, a)
            total += weight * pairs * exp_integral_e1(d2 / (4.0 * alpha * t))
    return load_per_m / (4.0 * math.pi * conductivity) * total / n
