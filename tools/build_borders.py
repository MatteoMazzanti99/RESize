"""Build src/resize_energy/data/borders.json.gz from Natural Earth (public domain).

Usage: python tools/build_borders.py path/to/ne_10m_admin_0_countries.geojson

Natural Earth "Admin 0 - Countries" 1:10m, https://www.naturalearthdata.com/ (public domain).
Each ring is simplified (Douglas-Peucker), rounded to 0.001 degree (about 100 m) and stored as
delta-encoded integers, so that the file stays small. Run it again only to refresh the data.
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

PRESET_TOLERANCE = 0.002     # degrees (about 200 m) for the countries RESize has presets for
OTHER_TOLERANCE = 0.01       # others are only used to name the country a site falls in
PRESETS = {"AU", "BR", "CA", "CN", "FR", "DE", "IN", "IT", "JP", "MX", "NL", "PL", "ZA", "KR",
           "ES", "TR", "GB", "US"}
MIN_AREA_OTHER = 0.002       # square degrees: tiny islands of other countries are dropped


def simplify(points: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    """Douglas-Peucker for a closed ring (first point == last point)."""
    if len(points) <= 4:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = points[a], points[b]
        dx, dy = x2 - x1, y2 - y1
        norm = dx * dx + dy * dy
        best, index = -1.0, -1
        for i in range(a + 1, b):
            x, y = points[i]
            if norm == 0:
                d = (x - x1) ** 2 + (y - y1) ** 2
            else:
                t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / norm))
                d = (x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2
            if d > best:
                best, index = d, i
        if best > tol * tol and index > 0:
            keep[index] = True
            stack.append((a, index))
            stack.append((index, b))
    out = [p for p, k in zip(points, keep, strict=True) if k]
    if len(out) < 4:                      # keep it a valid ring
        out = [points[0], points[len(points) // 3], points[2 * len(points) // 3], points[-1]]
    return out


def area(ring: list[tuple[float, float]]) -> float:
    s = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def encode(ring: list[tuple[float, float]]) -> list[int]:
    out: list[int] = []
    px = py = 0
    for lon, lat in ring[:-1]:                      # the closing point is implied
        x, y = round(lon * 1000), round(lat * 1000)
        out += [x - px, y - py]
        px, py = x, y
    return out


def main(path: str) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    countries: dict[str, dict] = {}
    for feature in data["features"]:
        p = feature["properties"]
        code = p["ISO_A2_EH"] if p["ISO_A2_EH"] not in ("-99", "") else p["ADM0_A3"]
        geom = feature["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        tol = PRESET_TOLERANCE if code in PRESETS else OTHER_TOLERANCE
        entry = countries.setdefault(code, {"name": p["NAME"], "polys": [], "size": 0.0})
        for poly in polys:
            outer = [tuple(c[:2]) for c in poly[0]]
            if code not in PRESETS and area(outer) < MIN_AREA_OTHER:
                continue
            rings = [encode(simplify([tuple(c[:2]) for c in ring], tol)) for ring in poly]
            entry["polys"].append(rings)
            entry["size"] = max(entry["size"], area(outer))
            if area(outer) >= entry["size"]:
                entry["name"] = p["NAME"] if p["ISO_A2_EH"] not in ("-99", "") else entry["name"]
    for entry in countries.values():
        del entry["size"]
    out = Path(__file__).resolve().parents[1] / "src" / "resize_energy" / "data" / "borders.json.gz"
    raw = json.dumps({"scale": 1000, "countries": countries}, separators=(",", ":")).encode()
    out.write_bytes(gzip.compress(raw, 9, mtime=0))
    print(f"{len(countries)} countries, {out.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main(sys.argv[1])
