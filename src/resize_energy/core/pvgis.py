"""Client for the PVGIS ``PVcalc`` API (European Commission JRC).

Network access is isolated in :func:`fetch_pvcalc`; :func:`parse_pvcalc` is pure and unit-tested.
Azimuth convention (PVGIS): 0 = south, 90 = west, -90 = east.
Docs: https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

PVGIS_VERSION = "v5_3"
PVCALC_URL = f"https://re.jrc.ec.europa.eu/api/{PVGIS_VERSION}/PVcalc"

# Tried in order when the server answers 403/404 (version moved or endpoint refused).
PVCALC_URLS = (
    PVCALC_URL,
    "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc",
    "https://re.jrc.ec.europa.eu/api/PVcalc",
)

USER_AGENT = "Mozilla/5.0 (compatible; RESize/0.1; +https://github.com/MatteoMazzanti99/RESize)"


# Header sets tried in order for each endpoint when the reply is not valid JSON.
HEADER_PROFILES: tuple[dict[str, str], ...] = (
    {"User-Agent": USER_AGENT, "Accept": "application/json"},
    {"User-Agent": "python-requests/2.32", "Accept": "*/*"},
)


class PVGISError(RuntimeError):
    """Raised when PVGIS cannot be reached or returns unexpected data."""


@dataclass(frozen=True)
class PVGISResult:
    annual_irradiation_kwh_m2: float  # in-plane irradiation H(i)_y
    annual_yield_kwh_per_kwp: float  # E_y for 1 kWp with the requested losses
    implied_performance_ratio: float  # E_y / H(i)_y


def build_url(
    lat: float,
    lon: float,
    tilt_deg: float,
    azimuth_deg: float,
    loss_pct: float = 14.0,
    peakpower_kw: float = 1.0,
    base: str = PVCALC_URL,
) -> str:
    """URL of a PVcalc request for a fixed, free-standing 1 kWp reference system.

    Numbers are always formatted with a decimal point, whatever the system language is.
    """
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("latitude must be in [-90, 90] and longitude in [-180, 180]")
    params = {
        "lat": f"{lat:.5f}",
        "lon": f"{lon:.5f}",
        "peakpower": f"{peakpower_kw:g}",
        "loss": f"{loss_pct:g}",
        "angle": f"{tilt_deg:g}",
        "aspect": f"{azimuth_deg:g}",
        "outputformat": "json",
    }
    return f"{base}?{urllib.parse.urlencode(params)}"


def parse_pvcalc(data: dict, peakpower_kw: float = 1.0) -> PVGISResult:
    """Extract the annual figures from a PVcalc JSON response."""
    if not isinstance(data, dict):
        raise PVGISError("Unexpected PVGIS response: not a JSON object")
    if "outputs" not in data and "message" in data:
        raise PVGISError(f"PVGIS replied: {data['message']}")
    try:
        totals = data["outputs"]["totals"]["fixed"]
        h_y = float(totals["H(i)_y"])
        e_y = float(totals["E_y"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PVGISError(f"Unexpected PVGIS response format (missing {exc})") from exc
    if h_y <= 0:
        raise PVGISError("PVGIS returned a non-positive irradiation")
    yield_per_kwp = e_y / peakpower_kw
    return PVGISResult(
        annual_irradiation_kwh_m2=h_y,
        annual_yield_kwh_per_kwp=yield_per_kwp,
        implied_performance_ratio=yield_per_kwp / h_y,
    )


def _error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace").strip()
    except Exception:  # noqa: BLE001 - best effort only
        body = ""
    return f" - server said: {body[:200]}" if body else ""


def fetch_pvcalc(
    lat: float,
    lon: float,
    tilt_deg: float,
    azimuth_deg: float,
    loss_pct: float = 14.0,
    timeout: float = 25.0,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
) -> PVGISResult:
    """Query PVGIS and return the annual irradiation and yield.

    ``urlopen`` can be replaced in tests. On HTTP 403/404 the next known endpoint is tried.
    """
    last_error: PVGISError | None = None
    for base in PVCALC_URLS:
        url = build_url(lat, lon, tilt_deg, azimuth_deg, loss_pct, base=base)
        for headers in HEADER_PROFILES:
            request = urllib.request.Request(url, headers=headers)
            try:
                with urlopen(request, timeout=timeout) as response:  # noqa: S310
                    raw = response.read()
                    content_type = _content_type(response)
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 529):
                    raise PVGISError(
                        f"PVGIS is busy (error {exc.code}): wait a few seconds and try again"
                    ) from exc
                last_error = PVGISError(f"PVGIS error {exc.code}{_error_detail(exc)} (URL: {url})")
                if exc.code in (403, 404):
                    break  # try the next endpoint
                raise last_error from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                raise PVGISError(f"Could not get data from PVGIS: {exc}") from exc
            try:
                payload = json.loads(raw.decode("utf-8-sig", errors="replace"))
            except json.JSONDecodeError:
                last_error = PVGISError(_not_json_message(raw, content_type, url))
                continue  # try the other header profile, then the next endpoint
            return parse_pvcalc(payload)
    assert last_error is not None
    raise last_error


def _content_type(response: Any) -> str:
    headers = getattr(response, "headers", None)
    if headers is None:
        return "unknown"
    return str(headers.get("Content-Type", "unknown"))


def _not_json_message(raw: bytes, content_type: str, url: str) -> str:
    """Readable description of a reply that is not JSON, with the start of its body."""
    text = " ".join(raw.decode("utf-8", errors="replace").split())
    if not text:
        shown = "an empty reply"
    else:
        shown = f"this text: {text[:250]!r}"
    return (
        f"PVGIS did not return JSON (content type: {content_type}); it sent {shown} "
        f"(URL: {url})"
    )
