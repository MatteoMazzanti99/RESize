"""Which country is a latitude/longitude in? An offline answer from real borders.

The borders come from Natural Earth (1:10 million, public domain), simplified to about 200 m
and stored in ``data/borders.json.gz`` (see ``tools/build_borders.py``). On land a point is in
the country whose polygon contains it, exactly up to the accuracy of the data (a few hundred
metres). Near the coast, or at sea, the data is not that exact, so a point up to
``SEA_KM`` from the coast of a country still counts as being in it (offshore plants).
The data is accurate to about 1-2 km along borders (it was drawn for 1:10 million maps), so
:func:`distance_to_country_km` lets callers tell "clearly elsewhere" from "right at the border".
Natural Earth draws borders the way they are in practice; it takes no position on disputes.
"""

from __future__ import annotations

import gzip
import json
import math
from functools import lru_cache
from importlib.resources import files

SEA_KM = 25.0      # a site in the sea within this distance of the coast belongs to that country
_KM_PER_DEG = 111.2

Ring = list[tuple[float, float]]            # (lon, lat)


class _Polygon:
    __slots__ = ("rings", "bbox")

    def __init__(self, rings: list[Ring]) -> None:
        self.rings = rings
        lons = [p[0] for p in rings[0]]
        lats = [p[1] for p in rings[0]]
        self.bbox = (min(lons), min(lats), max(lons), max(lats))

    def contains(self, lon: float, lat: float) -> bool:
        w, s, e, n = self.bbox
        if not (w <= lon <= e and s <= lat <= n):
            return False
        if not _in_ring(self.rings[0], lon, lat):
            return False
        return not any(_in_ring(hole, lon, lat) for hole in self.rings[1:])


def _in_ring(ring: Ring, lon: float, lat: float) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


@lru_cache(maxsize=1)
def _load() -> dict[str, tuple[str, list[_Polygon]]]:
    raw = files("resize_energy").joinpath("data", "borders.json.gz").read_bytes()
    data = json.loads(gzip.decompress(raw))
    scale = data["scale"]
    out: dict[str, tuple[str, list[_Polygon]]] = {}
    for code, entry in data["countries"].items():
        polys = []
        for rings in entry["polys"]:
            decoded: list[Ring] = []
            for flat in rings:
                x = y = 0
                ring: Ring = []
                for k in range(0, len(flat), 2):
                    x += flat[k]
                    y += flat[k + 1]
                    ring.append((x / scale, y / scale))
                ring.append(ring[0])
                decoded.append(ring)
            polys.append(_Polygon(decoded))
        out[code] = (entry["name"], polys)
    return out


def _distance_km(polys: list[_Polygon], lon: float, lat: float, limit_km: float) -> float:
    """Distance from the point to the outline of the polygons (inf if farther than the limit)."""
    kx = _KM_PER_DEG * math.cos(math.radians(lat))
    ky = _KM_PER_DEG
    margin = limit_km / min(kx, ky) if kx > 1e-6 else 360.0
    best = math.inf
    for poly in polys:
        w, s, e, n = poly.bbox
        if not (w - margin <= lon <= e + margin and s - margin <= lat <= n + margin):
            continue
        ring = poly.rings[0]
        for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False):
            ax, ay = (x1 - lon) * kx, (y1 - lat) * ky
            bx, by = (x2 - lon) * kx, (y2 - lat) * ky
            dx, dy = bx - ax, by - ay
            norm = dx * dx + dy * dy
            t = 0.0 if norm == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / norm))
            d = math.hypot(ax + t * dx, ay + t * dy)
            best = min(best, d)
    return best if best <= limit_km else math.inf


def distance_to_country_km(code: str, lat: float, lon: float, limit_km: float = 5.0) -> float:
    """Distance from the point to the outline of the country (inf if farther than the limit)."""
    entry = _load().get(code)
    return math.inf if entry is None else _distance_km(entry[1], lon, lat, limit_km)


def country_at(lat: float, lon: float) -> str | None:
    """Code of the country that contains the point (None at sea or when not found)."""
    for code, (_name, polys) in _load().items():
        if any(p.contains(lon, lat) for p in polys):
            return code
    return None


def country_near(lat: float, lon: float) -> str | None:
    """The country that contains the point, or else the nearest one within ``SEA_KM``."""
    code = country_at(lat, lon)
    if code is not None:
        return code
    best, best_code = math.inf, None
    for c, (_name, polys) in _load().items():
        d = _distance_km(polys, lon, lat, SEA_KM)
        if d < best:
            best, best_code = d, c
    return best_code


def country_name(code: str) -> str:
    entry = _load().get(code)
    return entry[0] if entry else code


def in_country(code: str, lat: float, lon: float) -> bool | None:
    """True/False if the point is in the country ``code``; None if the code is unknown."""
    countries = _load()
    if code not in countries:
        return None
    return country_near(lat, lon) == code
