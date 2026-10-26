"""Wind rose of a site: how often the wind comes from each direction, and how strong it is.

The rose is built from hourly wind speed and direction at 50 m from NASA POWER (the MERRA-2
reanalysis, the same service as the mean wind speed). Twelve sectors of 30 degrees are used,
centred on 0, 30, 60 ... degrees (0 = wind from the north, 90 = from the east), which is the
sector set of the wake model. Pure calculation and download code, no GUI.
"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from resize_energy.core.nasa_power import USER_AGENT, NasaPowerError

SECTORS = 12
HOURLY_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
DEFAULT_YEARS = (2019, 2020, 2021)
MIN_HOURS = 5000          # fewer valid hours than this is not a wind rose


@dataclass(frozen=True)
class WindRose:
    """Frequency and relative strength of the wind in each sector."""

    frequency: tuple[float, ...]       # share of the hours, sums to 1
    speed_factor: tuple[float, ...]    # sector mean speed / overall mean speed
    mean_speed_ms: float               # overall mean speed of the series, at 50 m
    hours: int                         # valid hours used
    years: tuple[int, ...] = ()
    source: str = "NASA POWER"

    def __post_init__(self) -> None:
        if len(self.frequency) != len(self.speed_factor) or not self.frequency:
            raise ValueError("a wind rose needs one frequency and one speed factor per sector")
        if abs(sum(self.frequency) - 1.0) > 1e-6:
            raise ValueError("the sector frequencies must add up to 1")

    @property
    def sectors(self) -> int:
        return len(self.frequency)

    def energy_share(self) -> tuple[float, ...]:
        """Share of the wind energy (frequency x speed^3) coming from each sector."""
        raw = [f * s ** 3 for f, s in zip(self.frequency, self.speed_factor, strict=True)]
        total = sum(raw)
        return tuple(r / total for r in raw) if total > 0 else self.frequency

    def prevailing_deg(self) -> float:
        """Direction of the wind energy (circular mean of the sectors, 0-360 degrees)."""
        return prevailing_direction(self.energy_share())

    def to_dict(self) -> dict[str, Any]:
        return {"frequency": [round(v, 6) for v in self.frequency],
                "speed_factor": [round(v, 4) for v in self.speed_factor],
                "mean_speed_ms": round(self.mean_speed_ms, 3), "hours": self.hours,
                "years": list(self.years), "source": self.source}

    @staticmethod
    def from_dict(d: Any) -> WindRose:
        try:
            freq = tuple(float(v) for v in d["frequency"])
            total = sum(freq)
            freq = tuple(v / total for v in freq)       # undo the rounding of the file
            return WindRose(freq, tuple(float(v) for v in d["speed_factor"]),
                            float(d["mean_speed_ms"]), int(d["hours"]),
                            tuple(int(y) for y in d.get("years", ())),
                            str(d.get("source", "NASA POWER")))
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"the saved wind rose is damaged ({exc})") from exc


def prevailing_direction(weights: Sequence[float]) -> float:
    """Circular mean direction [deg, 0-360) of sector weights (sector i is centred on i*360/n)."""
    n = len(weights)
    x = sum(w * math.sin(math.radians(i * 360.0 / n)) for i, w in enumerate(weights))
    y = sum(w * math.cos(math.radians(i * 360.0 / n)) for i, w in enumerate(weights))
    return math.degrees(math.atan2(x, y)) % 360.0


def sector_of(direction_deg: float, sectors: int = SECTORS) -> int:
    """Index of the sector a direction belongs to (sector i covers i*30 +- 15 degrees)."""
    width = 360.0 / sectors
    return int(((direction_deg % 360.0) + width / 2.0) // width) % sectors


def rose_from_series(speeds: Sequence[float], directions: Sequence[float],
                     years: tuple[int, ...] = (), sectors: int = SECTORS) -> WindRose:
    """Build the rose from paired hourly speeds [m/s] and directions [deg]."""
    if len(speeds) != len(directions):
        raise ValueError("speeds and directions must have the same length")
    count = [0] * sectors
    total = [0.0] * sectors
    for v, d in zip(speeds, directions, strict=True):
        if v < 0 or not (math.isfinite(v) and math.isfinite(d)):
            continue
        s = sector_of(d, sectors)
        count[s] += 1
        total[s] += v
    n = sum(count)
    if n < MIN_HOURS:
        raise ValueError(f"only {n} valid hours: not enough for a wind rose")
    mean = sum(total) / n
    if mean <= 0:
        raise ValueError("the wind is calm in the whole series")
    freq = tuple(c / n for c in count)
    factor = tuple((total[i] / count[i]) / mean if count[i] else 0.0 for i in range(sectors))
    return WindRose(freq, factor, mean, n, years)


def uniform_rose(mean_speed_ms: float = 6.0, sectors: int = SECTORS) -> WindRose:
    """A rose with the wind equally likely from every direction."""
    return WindRose((1.0 / sectors,) * sectors, (1.0,) * sectors, mean_speed_ms, 0)


# --- download ---------------------------------------------------------------------------------
def build_url(lat: float, lon: float, year: int) -> str:
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("latitude must be within +-90 and longitude within +-180")
    query = urllib.parse.urlencode({
        "parameters": "WS50M,WD50M", "community": "RE",
        "longitude": f"{lon:.4f}", "latitude": f"{lat:.4f}",
        "start": f"{year}0101", "end": f"{year}1231", "format": "JSON",
    })
    return f"{HOURLY_URL}?{query}"


def parse_hourly_pairs(data: dict[str, Any]) -> tuple[list[float], list[float]]:
    """Paired hourly (speed, direction) values from a NASA POWER hourly answer; missing -999
    values are dropped hour by hour."""
    try:
        params = data["properties"]["parameter"]
        speed_raw, dir_raw = params["WS50M"], params["WD50M"]
    except (KeyError, TypeError) as exc:
        raise NasaPowerError("The NASA POWER answer has no hourly wind speed and direction.") from exc
    speeds: list[float] = []
    directions: list[float] = []
    for key, value in speed_raw.items():
        try:
            v, d = float(value), float(dir_raw[key])
        except (KeyError, TypeError, ValueError):
            continue
        if v > -990 and d > -990:
            speeds.append(v)
            directions.append(d)
    return speeds, directions


def _download(url: str, timeout: float, urlopen: Callable[..., Any]) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise NasaPowerError(f"NASA POWER answered HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise NasaPowerError(f"Could not reach NASA POWER ({exc}).") from exc
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise NasaPowerError(
            f"NASA POWER did not return JSON (it starts with: {raw[:80]!r}).") from exc


def fetch_wind_rose(lat: float, lon: float, years: Sequence[int] = DEFAULT_YEARS,
                    timeout: float = 60.0,
                    urlopen: Callable[..., Any] = urllib.request.urlopen) -> WindRose:
    """Download the hourly wind of ``years`` and build the rose. A year that cannot be read is
    skipped; the call fails only when none can. Raises NasaPowerError with a readable text."""
    speeds: list[float] = []
    directions: list[float] = []
    used: list[int] = []
    last_error: NasaPowerError | None = None
    for year in years:
        try:
            v, d = parse_hourly_pairs(_download(build_url(lat, lon, year), timeout, urlopen))
        except NasaPowerError as exc:
            last_error = exc
            continue
        speeds += v
        directions += d
        used.append(year)
    if not used:
        raise last_error or NasaPowerError("No year of wind data could be read.")
    try:
        return rose_from_series(speeds, directions, tuple(used))
    except ValueError as exc:
        raise NasaPowerError(f"NASA POWER has no usable wind rose for this place ({exc}).") from exc
