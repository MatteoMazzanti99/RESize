"""Building blocks of biomass sizing: fuel energy, load-duration coverage, biogas.

Pure functions, no GUI. Energies in kWh, masses in kg or t, volumes in normal m3 (Nm3).
"""

from __future__ import annotations

import math

# Heat to evaporate 1 kg of water at 25 degC (2.443 MJ/kg) in kWh/kg: it is lost with the
# flue gas, so it is subtracted when the lower heating value (LHV) is computed.
EVAPORATION_KWH_PER_KG = 2.443 / 3.6
# Lower heating value of methane: 35.8 MJ/Nm3.
CH4_LHV_KWH_PER_NM3 = 9.97
# Density of biogas (about 55 % CH4, 45 % CO2) at normal conditions, kg/Nm3.
BIOGAS_DENSITY_KG_PER_NM3 = 1.2
HOURS_PER_YEAR = 8760.0


def lhv_as_received(lhv_dry_kwh_per_kg: float, moisture_wb: float) -> float:
    """LHV of the fuel as burnt [kWh/kg]: LHV_dry (1 - M) - 0.679 M, M = moisture (wet basis)."""
    if not 0.0 <= moisture_wb < 1.0:
        raise ValueError("moisture (wet basis) must be in [0, 1)")
    return lhv_dry_kwh_per_kg * (1.0 - moisture_wb) - EVAPORATION_KWH_PER_KG * moisture_wb


def load_exponent(load_factor: float) -> float:
    """Exponent n of the load-duration curve P(t) = P_peak (1 - t/T)^n with the given load factor.

    The mean of that curve is P_peak / (n + 1), so n = 1 / load_factor - 1.
    """
    if not 0.0 < load_factor <= 1.0:
        raise ValueError("load factor must be in (0, 1]")
    return 1.0 / load_factor - 1.0


def covered_fraction(power_ratio: float, load_factor: float) -> float:
    """Share of the yearly heat covered by a plant of ``power_ratio`` = P_plant / P_peak.

    With the load-duration curve above: f(x) = (n + 1) x - n x^((n + 1) / n), for x in [0, 1].
    The plant is assumed to follow the load down to zero (no minimum load).
    """
    x = min(max(power_ratio, 0.0), 1.0)
    n = load_exponent(load_factor)
    if n < 1e-9:
        return x
    return (n + 1.0) * x - n * x ** ((n + 1.0) / n)


def power_ratio_for_coverage(coverage: float, load_factor: float) -> float:
    """Inverse of :func:`covered_fraction`: the P_plant / P_peak that covers ``coverage``."""
    if not 0.0 < coverage <= 1.0:
        raise ValueError("coverage must be in (0, 1]")
    if coverage >= 1.0:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(80):  # f is increasing: plain bisection is enough
        mid = 0.5 * (lo + hi)
        if covered_fraction(mid, load_factor) < coverage:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def deliveries_per_year(mass_t: float, truck_volume_m3: float, bulk_density_kg_m3: float) -> int:
    """Number of truck loads per year (whole loads, rounded up)."""
    payload_t = truck_volume_m3 * bulk_density_kg_m3 / 1000.0
    return math.ceil(mass_t / payload_t)


def digester_volume_m3(substrate_t_per_day: float, hrt_days: float, fill_fraction: float = 0.9,
                       density_t_per_m3: float = 1.0) -> float:
    """Total digester volume: working volume = daily feed x HRT / density, plus gas headspace."""
    if not 0.0 < fill_fraction <= 1.0:
        raise ValueError("fill fraction must be in (0, 1]")
    return substrate_t_per_day * hrt_days / density_t_per_m3 / fill_fraction


def organic_loading_rate(volatile_solids_kg_per_day: float, working_volume_m3: float) -> float:
    """OLR [kg VS / (m3 d)]: volatile solids fed per day per m3 of working volume."""
    return volatile_solids_kg_per_day / working_volume_m3
