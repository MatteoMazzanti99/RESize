"""Deeper looks at a PV plant: shading by a nearby obstacle, month-by-month energy, battery.

Pure calculation, no GUI. The sun is the clear-sky sun of the latitude; irradiance on the
modules is not modelled, only the share of the sun's energy that an obstacle blocks.
"""

from __future__ import annotations

import math
from functools import lru_cache

from resize_energy.core import battery_design as bd
from resize_energy.core import profiles as prof
from resize_energy.core.hydrogen import MONTH_OF_HOUR


def sun_position(day: int, hour_mid: float, lat_deg: float) -> tuple[float, float]:
    """(elevation, azimuth) in degrees; azimuth 0 = south, positive towards the west."""
    phi = math.radians(lat_deg)
    decl = math.radians(23.45) * math.sin(2.0 * math.pi * (284 + day + 1) / 365.0)
    omega = math.radians(15.0 * (hour_mid - 12.0))
    sin_el = (math.sin(phi) * math.sin(decl)
              + math.cos(phi) * math.cos(decl) * math.cos(omega))
    elevation = math.degrees(math.asin(max(-1.0, min(1.0, sin_el))))
    az = math.degrees(math.atan2(
        math.sin(omega), math.cos(omega) * math.sin(phi) - math.tan(decl) * math.cos(phi)))
    return elevation, az


def shading_loss(lat_deg: float, obstacle_elevation_deg: float, az_from_deg: float,
                 az_to_deg: float, diffuse_share: float = 0.35) -> float:
    """Share of the yearly energy lost to an obstacle seen at ``obstacle_elevation_deg``
    above the horizon between the azimuths ``az_from`` and ``az_to`` (0 = south).

    Only the direct (beam) part of the sunlight is blocked; the diffuse part, ``diffuse_share``
    of the total, still arrives. Weights are the clear-sky sine of the sun's elevation.
    """
    if not -90.0 <= lat_deg <= 90.0:
        raise ValueError("latitude must be between -90 and 90")
    if not 0.0 <= obstacle_elevation_deg < 90.0:
        raise ValueError("obstacle height must be between 0 and 90 degrees")
    if az_to_deg < az_from_deg:
        raise ValueError("the end azimuth must not be before the start azimuth")
    if not 0.0 <= diffuse_share < 1.0:
        raise ValueError("diffuse share must be in [0, 1)")
    total = blocked = 0.0
    for day in range(0, 365, 3):
        for hour in range(24):
            el, az = sun_position(day, hour + 0.5, lat_deg)
            if el <= 0.0:
                continue
            w = math.sin(math.radians(el))
            total += w
            if el < obstacle_elevation_deg and az_from_deg <= az <= az_to_deg:
                blocked += w
    return (1.0 - diffuse_share) * blocked / total if total > 0 else 0.0


def monthly_energy_kwh(lat_deg: float, annual_kwh: float) -> tuple[float, ...]:
    """The yearly energy spread over the 12 months with the clear-sky/cloud shape of the site."""
    if annual_kwh < 0:
        raise ValueError("energy cannot be negative")
    unit = prof.synthetic_pv_profile(lat_deg, 1000.0)
    months = [0.0] * 12
    for t, v in enumerate(unit):
        months[MONTH_OF_HOUR[t]] += v
    total = sum(months)
    return tuple(annual_kwh * m / total for m in months)


@lru_cache(maxsize=8)
def battery_view(lat_deg: float, annual_demand_kwh: float, pv_kwp: float,
                 yield_kwh_per_kwp: float, load_kind: str = "residential") -> bd.BatteryDesign:
    """The plant with a battery of one average day of consumption (the Battery module
    gives the full study)."""
    daily = annual_demand_kwh / 365.0
    inp = bd.BatteryInputs(annual_demand_kwh=annual_demand_kwh, load_kind=load_kind,
                           use_pv=True, pv_kwp=pv_kwp, mode="given",
                           capacity_kwh=max(1.0, round(daily, 1)))
    profiles = bd.BatteryProfiles(prof.synthetic_pv_profile(lat_deg, yield_kwh_per_kwp), None,
                                  "synthetic")
    return bd.size_battery(inp, profiles)
