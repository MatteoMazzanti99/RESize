"""Building blocks of run-of-river hydropower sizing: flow-duration curve, penstock, turbine.

Pure functions, no GUI. Flows in m3/s, heads in m, power in kW, energy in kWh.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

RHO_WATER = 1000.0          # kg/m3
G = 9.81                    # m/s2
NU_WATER = 1.0e-6           # kinematic viscosity at about 20 degC, m2/s
HOURS_PER_YEAR = 8760.0
Z_Q95 = 1.6449              # standard normal quantile of 95 %


# --- flow-duration curve -----------------------------------------------------------------------
def lognormal_fdc(mean_flow: float, q95: float) -> tuple[float, float]:
    """(mu, sigma) of a log-normal flow-duration curve with the given mean flow and Q95.

    ln Q is normal: mean = exp(mu + sigma^2 / 2) and Q95 = exp(mu - 1.6449 sigma). Eliminating
    mu leaves sigma^2 / 2 + 1.6449 sigma = ln(mean / Q95), which is solved in closed form.
    """
    if mean_flow <= 0 or q95 <= 0:
        raise ValueError("the mean flow and Q95 must be > 0")
    if q95 >= mean_flow:
        raise ValueError("Q95 (the flow exceeded 95 % of the time) must be lower than the mean flow")
    ratio = math.log(mean_flow / q95)
    sigma = -Z_Q95 + math.sqrt(Z_Q95 ** 2 + 2.0 * ratio)
    mu = math.log(mean_flow) - sigma ** 2 / 2.0
    return mu, sigma


def flow_exceeded(p: float, mu: float, sigma: float) -> float:
    """Flow exceeded for a fraction ``p`` of the time (0 < p < 1) on the log-normal curve."""
    if not 0.0 < p < 1.0:
        raise ValueError("the exceedance must be between 0 and 1 (exclusive)")
    return math.exp(mu + sigma * NormalDist().inv_cdf(1.0 - p))


# --- penstock ----------------------------------------------------------------------------------
def penstock_diameter(flow: float, velocity: float) -> float:
    """Diameter of a full circular pipe carrying ``flow`` at ``velocity``: D = sqrt(4 Q / pi v)."""
    if flow <= 0 or velocity <= 0:
        raise ValueError("flow and velocity must be > 0")
    return math.sqrt(4.0 * flow / (math.pi * velocity))


def friction_factor(reynolds: float, relative_roughness: float) -> float:
    """Darcy friction factor, Swamee-Jain explicit formula (turbulent flow, Re > 5000)."""
    if reynolds <= 0:
        raise ValueError("Reynolds number must be > 0")
    if reynolds < 2300.0:
        return 64.0 / reynolds
    return 0.25 / math.log10(relative_roughness / 3.7 + 5.74 / reynolds ** 0.9) ** 2


def head_loss(flow: float, diameter: float, length: float, roughness_m: float,
              local_k: float) -> float:
    """Head lost in the penstock [m]: (f L / D + K) v^2 / 2g (Darcy-Weisbach plus local losses)."""
    if flow <= 0:
        return 0.0
    if diameter <= 0 or length < 0 or roughness_m < 0 or local_k < 0:
        raise ValueError("diameter must be > 0 and length, roughness and K >= 0")
    area = math.pi * diameter ** 2 / 4.0
    v = flow / area
    re = v * diameter / NU_WATER
    f = friction_factor(re, roughness_m / diameter)
    return (f * length / diameter + local_k) * v ** 2 / (2.0 * G)


def hydraulic_power_kw(flow: float, head: float, efficiency: float = 1.0) -> float:
    """P = rho g Q H eta [kW]."""
    return RHO_WATER * G * flow * head * efficiency / 1000.0


# --- turbines ----------------------------------------------------------------------------------
@dataclass(frozen=True)
class TurbineType:
    key: str
    name: str
    head_min: float            # m, usual range of net head
    head_max: float
    min_flow_fraction: float   # lowest flow, as a fraction of the design flow, it can work at
    efficiency: float          # best efficiency of the turbine alone


# Ranges of net head (Table 6.3) and best efficiencies (Table 6.7) of the ESHA Guide; the lowest
# working flows follow its section 6.2.1 (Kaplan 15-30 %, Pelton 10-30 %) and 6.2.5 (Francis
# about one half). Crossflow has no figure there: 0.2 and 0.80 are RESize's typical values.
TURBINES: dict[str, TurbineType] = {t.key: t for t in (
    TurbineType("kaplan", "Kaplan (axial flow)", 2.0, 40.0, 0.30, 0.91),
    TurbineType("francis", "Francis", 25.0, 350.0, 0.50, 0.94),
    TurbineType("pelton", "Pelton", 50.0, 1300.0, 0.30, 0.90),
    TurbineType("crossflow", "Crossflow (Banki-Michell)", 5.0, 200.0, 0.20, 0.80),
)}


def choose_turbine(net_head: float, design_flow: float) -> str:
    """The turbine type that fits the head and the flow (a rule of thumb, not a quotation).

    Inside the head ranges of the ESHA Guide the flow decides: large flows go to the reaction
    turbines (Kaplan at low head, Francis at medium head), small flows to the impulse ones
    (crossflow, Pelton).
    """
    if net_head <= 0 or design_flow <= 0:
        raise ValueError("head and flow must be > 0")
    if net_head < 40.0:
        return "kaplan" if design_flow >= 1.0 else "crossflow"
    if net_head < 150.0:
        if design_flow >= 0.5:
            return "francis"
        return "pelton" if net_head >= 50.0 else "crossflow"
    if net_head < 350.0 and design_flow >= 3.0:
        return "francis"
    return "pelton"


def generator_efficiency(power_kw: float) -> float:
    """Typical generator efficiency from the ESHA Guide (Table 6.8), interpolated in ln(P)."""
    table = ((10.0, 0.910), (50.0, 0.940), (100.0, 0.950), (250.0, 0.955),
             (500.0, 0.960), (1000.0, 0.970))
    if power_kw <= table[0][0]:
        return table[0][1]
    if power_kw >= table[-1][0]:
        return table[-1][1]
    for (p0, e0), (p1, e1) in zip(table, table[1:], strict=False):
        if p0 <= power_kw <= p1:
            u = math.log(power_kw / p0) / math.log(p1 / p0)
            return e0 + u * (e1 - e0)
    return table[-1][1]
