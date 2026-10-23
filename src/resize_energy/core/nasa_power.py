"""Long-term mean wind speed and temperature from NASA POWER (climatology endpoint).

NASA POWER is a free service built on the MERRA-2 reanalysis (grid of about 50 km). Its values
are smooth: in hilly terrain or near the coast the real wind can differ a lot, so treat the
result as a first estimate and replace it with a measurement or an atlas value when you can.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

BASE_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
USER_AGENT = "RESize (open-source educational sizing tool)"
REFERENCE_HEIGHT_M = 50.0


class NasaPowerError(RuntimeError):
    """Raised with a message that can be shown to the user as it is."""


@dataclass(frozen=True)
class WindClimate:
    mean_speed_50m_ms: float
    mean_temperature_c: float | None
    elevation_m: float | None


def build_url(lat: float, lon: float) -> str:
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("latitude must be within +-90 and longitude within +-180")
    query = urllib.parse.urlencode({
        "parameters": "WS50M,T2M",
        "community": "RE",
        "longitude": f"{lon:.4f}",
        "latitude": f"{lat:.4f}",
        "format": "JSON",
    })
    return f"{BASE_URL}?{query}"


def parse_climatology(data: dict[str, Any]) -> WindClimate:
    """Extract the annual means from a NASA POWER climatology response."""
    try:
        params = data["properties"]["parameter"]
        speed = float(params["WS50M"]["ANN"])
    except (KeyError, TypeError, ValueError) as exc:
        raise NasaPowerError("The NASA POWER answer has no annual WS50M value.") from exc
    if speed < 0:  # NASA uses -999 for missing data
        raise NasaPowerError("NASA POWER has no wind data for this location.")
    temperature: float | None = None
    try:
        t = float(params["T2M"]["ANN"])
        temperature = t if t > -90 else None
    except (KeyError, TypeError, ValueError):
        pass
    elevation: float | None = None
    try:
        elevation = float(data["geometry"]["coordinates"][2])
    except (KeyError, TypeError, ValueError, IndexError):
        pass
    return WindClimate(speed, temperature, elevation)


def fetch_wind_climate(
    lat: float, lon: float, timeout: float = 25.0,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
) -> WindClimate:
    """Query NASA POWER. Raises NasaPowerError with a readable message on any failure."""
    url = build_url(lat, lon)
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
    return parse_climatology(data)
