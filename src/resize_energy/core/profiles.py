"""Hourly production profiles for one year (8760 values) used by the hydrogen module.

Real shapes come from NASA POWER hourly data (wind speed at 50 m and solar radiation on a
horizontal plane, same year and place, so wind and sun are correlated as in reality).
When the network is not available, :func:`synthetic_pv_profile` and
:func:`synthetic_wind_profile` build a plausible but invented year: good for learning and
tests, not for a real project.
"""

from __future__ import annotations

import json
import math
import random
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from resize_energy.core import wind
from resize_energy.core.nasa_power import USER_AGENT, NasaPowerError
from resize_energy.core.wind_design import TurbineSpec

HOURS = 8760
HOURLY_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
DEFAULT_YEAR = 2019  # not a leap year: exactly 8760 hours
DAYS_BEFORE_MONTH = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


@dataclass(frozen=True)
class HourlyWeather:
    """One year of hourly data: wind speed at 50 m [m/s] and horizontal radiation [W/m2]."""

    wind50_ms: tuple[float, ...]
    ghi_w_m2: tuple[float, ...]
    year: int
    source: str = "NASA POWER"


def hour_index(key: str) -> int:
    """Index 0..8759 of a NASA POWER key 'YYYYMMDDHH' (non-leap year), or -1 for 29 February."""
    month, day, hour = int(key[4:6]), int(key[6:8]), int(key[8:10])
    if month == 2 and day == 29:
        return -1
    return (DAYS_BEFORE_MONTH[month - 1] + day - 1) * 24 + hour


def build_hourly_url(lat: float, lon: float, year: int = DEFAULT_YEAR) -> str:
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("latitude must be within +-90 and longitude within +-180")
    query = urllib.parse.urlencode({
        "parameters": "WS50M,ALLSKY_SFC_SW_DWN",
        "community": "RE",
        "longitude": f"{lon:.4f}",
        "latitude": f"{lat:.4f}",
        "start": f"{year}0101",
        "end": f"{year}1231",
        "format": "JSON",
    })
    return f"{HOURLY_URL}?{query}"


def _fill(values: list[float | None], default: float) -> list[float]:
    """Replace missing values (None) by the previous valid one, or ``default`` at the start."""
    out: list[float] = []
    last = default
    for v in values:
        if v is not None:
            last = v
        out.append(last)
    return out


def parse_hourly(data: dict[str, Any], year: int = DEFAULT_YEAR) -> HourlyWeather:
    """Turn a NASA POWER hourly answer into two 8760-value series (fill values -999 repaired)."""
    try:
        params = data["properties"]["parameter"]
        wind_raw, ghi_raw = params["WS50M"], params["ALLSKY_SFC_SW_DWN"]
    except (KeyError, TypeError) as exc:
        raise NasaPowerError("The NASA POWER answer has no hourly wind and radiation.") from exc
    series: list[list[float | None]] = []
    for raw in (wind_raw, ghi_raw):
        values: list[float | None] = [None] * HOURS
        for key, value in raw.items():
            try:
                i = hour_index(str(key))
                v = float(value)
            except (ValueError, IndexError):
                continue
            if 0 <= i < HOURS and v > -990:
                values[i] = v
        valid = sum(v is not None for v in values)
        if valid < HOURS * 0.9:
            raise NasaPowerError("NASA POWER returned too many missing hours for this place.")
        series.append(values)
    wind_mean = sum(v for v in series[0] if v is not None) / sum(v is not None for v in series[0])
    return HourlyWeather(
        tuple(max(0.0, v) for v in _fill(series[0], wind_mean)),
        tuple(max(0.0, v) for v in _fill(series[1], 0.0)),
        year,
    )


def fetch_hourly(
    lat: float, lon: float, year: int = DEFAULT_YEAR, timeout: float = 60.0,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
) -> HourlyWeather:
    """Query NASA POWER (one request, about 1 MB). Raises NasaPowerError with a clear text."""
    url = build_hourly_url(lat, lon, year)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise NasaPowerError(f"NASA POWER answered HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise NasaPowerError(f"Could not reach NASA POWER ({exc}).") from exc
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise NasaPowerError(
            f"NASA POWER did not return JSON (it starts with: {raw[:80]!r})."
        ) from exc
    return parse_hourly(data, year)


def pv_profile_from_ghi(ghi_w_m2: Sequence[float], yield_kwh_per_kwp: float) -> tuple[float, ...]:
    """Power of 1 kWp hour by hour [kW]: the radiation shape scaled to the annual yield.

    The yield (from PVGIS, with the real tilt and losses) fixes the energy; the radiation
    series fixes when it is produced.
    """
    if len(ghi_w_m2) != HOURS:
        raise ValueError("a year of 8760 hourly values is needed")
    total = sum(ghi_w_m2)
    if total <= 0 or yield_kwh_per_kwp <= 0:
        raise ValueError("radiation and yield must be > 0")
    k = yield_kwh_per_kwp / total
    return tuple(g * k for g in ghi_w_m2)


def wind_profile_from_speeds(
    speeds_ref_ms: Sequence[float], ref_height_m: float, power_fn: Callable[[float], float],
    rated_kw: float, hub_height_m: float, alpha: float = 0.14, speed_factor: float = 1.0,
    efficiency: float = 1.0,
) -> tuple[float, ...]:
    """Power per kW of rated power, hour by hour: shear to hub height, power curve, losses.

    ``speed_factor`` rescales the whole series (to match a mean speed measured by the user)
    and ``efficiency`` is availability times (1 - other losses).
    """
    if len(speeds_ref_ms) != HOURS:
        raise ValueError("a year of 8760 hourly values is needed")
    out = []
    for v in speeds_ref_ms:
        vh = wind.shear_power_law(max(v, 0.0) * speed_factor, ref_height_m, hub_height_m, alpha)
        out.append(power_fn(vh) / rated_kw * efficiency)
    return tuple(out)


def synthetic_pv_profile(lat: float, yield_kwh_per_kwp: float, seed: int = 1) -> tuple[float, ...]:
    """Invented but physical year: clear-sky shape of the latitude times daily cloudiness."""
    rng = random.Random(seed)
    phi = math.radians(lat)
    values: list[float] = []
    for day in range(365):
        decl = math.radians(23.45) * math.sin(2 * math.pi * (284 + day + 1) / 365)
        clouds = min(1.0, max(0.15, rng.gauss(0.62, 0.30)))
        for hour in range(24):
            omega = math.radians(15.0 * (hour + 0.5 - 12.0))
            cos_z = (math.sin(phi) * math.sin(decl)
                     + math.cos(phi) * math.cos(decl) * math.cos(omega))
            values.append(max(0.0, cos_z) * clouds)
    return pv_profile_from_ghi(values, yield_kwh_per_kwp)


def synthetic_wind_series(mean_ms: float, k: float, seed: int = 2,
                          autocorrelation: float = 0.95) -> tuple[float, ...]:
    """Hourly wind speeds with a Weibull distribution and hour-to-hour persistence."""
    rng = random.Random(seed)
    scale = wind.weibull_scale_from_mean(mean_ms, k)
    z = rng.gauss(0.0, 1.0)
    noise = math.sqrt(1.0 - autocorrelation ** 2)
    out = []
    for _ in range(HOURS):
        z = autocorrelation * z + noise * rng.gauss(0.0, 1.0)
        u = min(max(0.5 * (1.0 + math.erf(z / math.sqrt(2.0))), 1e-9), 1 - 1e-9)
        out.append(scale * (-math.log(1.0 - u)) ** (1.0 / k))
    return tuple(out)


def turbine_unit_profile(
    series_50m_ms: Sequence[float], target_mean_50m_ms: float, hub_height_m: float,
    alpha: float, turbine: TurbineSpec, rho: float, efficiency: float,
) -> tuple[float, ...]:
    """Hourly power per kW of rated power of the chosen turbine at the user's wind speed.

    The hourly series (any year, at 50 m) is rescaled so that its mean equals the mean wind
    speed chosen by the user, then passed through shear, the power curve and the losses.
    """
    mean = sum(series_50m_ms) / len(series_50m_ms)
    if mean <= 0 or target_mean_50m_ms <= 0:
        raise ValueError("wind speeds must be > 0")

    def power(v: float) -> float:
        if turbine.power_curve:
            return wind.curve_power_kw(v, turbine.power_curve, turbine.cut_out_ms, rho)
        return wind.generic_power_kw(v, turbine.rated_power_kw, turbine.cut_in_ms,
                                     turbine.rated_speed_ms, turbine.cut_out_ms, rho)

    return wind_profile_from_speeds(
        series_50m_ms, 50.0, power, turbine.rated_power_kw, hub_height_m, alpha,
        speed_factor=target_mean_50m_ms / mean, efficiency=efficiency)
