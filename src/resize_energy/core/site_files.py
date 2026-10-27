"""Read the boundary of a wind site and its exclusion zones from KML, KMZ or GeoJSON files.

Qt-free. Files hold longitude/latitude; the program works in metres east and north of the site
centre, so the polygons are projected with the same small-area formula as the satellite tiles
(111 319 m per degree, the east-west one scaled by the cosine of the latitude).
"""

from __future__ import annotations

import io
import json
import math
import re
import zipfile
from dataclasses import dataclass, field
from xml.etree import ElementTree

M_PER_DEG = 111319.49           # metres per degree of latitude (sphere of the web-mercator tiles)

Ring = tuple[tuple[float, float], ...]


class SiteFileError(ValueError):
    """The file cannot be used; the message says why in plain words."""


@dataclass(frozen=True)
class SiteShape:
    """A site boundary and its exclusion zones, in metres east/north of ``lat``, ``lon``."""

    lat: float
    lon: float
    boundary: Ring
    exclusions: tuple[Ring, ...] = field(default_factory=tuple)
    name: str = ""

    def to_dict(self) -> dict:
        return {"lat": self.lat, "lon": self.lon, "name": self.name,
                "boundary": [list(p) for p in self.boundary],
                "exclusions": [[list(p) for p in r] for r in self.exclusions]}

    @classmethod
    def from_dict(cls, d: dict) -> SiteShape:
        try:
            return cls(float(d["lat"]), float(d["lon"]),
                       tuple((float(x), float(y)) for x, y in d["boundary"]),
                       tuple(tuple((float(x), float(y)) for x, y in r) for r in d["exclusions"]),
                       str(d.get("name", "")))
        except (KeyError, TypeError, ValueError) as exc:
            raise SiteFileError(f"the saved site shape is damaged ({exc})") from exc


def ring_area(ring: Ring) -> float:
    """Unsigned area (shoelace) of a ring in the units of its points squared."""
    s = 0.0
    for i, (x1, y1) in enumerate(ring):
        x2, y2 = ring[(i + 1) % len(ring)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _clean(ring: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring = ring[:-1]
    out = []
    for p in ring:
        if not out or p != out[-1]:
            out.append(p)
    return out


def _ring_ok(ring: list[tuple[float, float]]) -> bool:
    return (len(ring) >= 3 and all(-180 <= x <= 180 and -90 <= y <= 90 for x, y in ring)
            and ring_area(tuple(ring)) > 0.0)


# --- GeoJSON ---------------------------------------------------------------------------------
def _geo_polygons(geom: dict, out: list[tuple[list, list[list]]]) -> None:
    kind = geom.get("type")
    coords = geom.get("coordinates")
    if kind == "Polygon" and coords:
        out.append((coords[0], coords[1:]))
    elif kind == "MultiPolygon" and coords:
        for poly in coords:
            if poly:
                out.append((poly[0], poly[1:]))
    elif kind == "GeometryCollection":
        for g in geom.get("geometries", []):
            _geo_polygons(g, out)
    elif kind == "Feature" and geom.get("geometry"):
        _geo_polygons(geom["geometry"], out)
    elif kind == "FeatureCollection":
        for f in geom.get("features", []):
            _geo_polygons(f, out)


def _parse_geojson(text: str) -> list[tuple[list, list[list]]]:
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SiteFileError("the file is not valid GeoJSON") from exc
    out: list[tuple[list, list[list]]] = []
    if isinstance(doc, dict):
        _geo_polygons(doc, out)
    return out


# --- KML -------------------------------------------------------------------------------------
def _coords(text: str | None) -> list[tuple[float, float]]:
    pts = []
    for tok in re.split(r"\s+", (text or "").strip()):
        parts = tok.split(",")
        if len(parts) >= 2:
            try:
                pts.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    return pts


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_kml(text: str) -> list[tuple[list, list[list]]]:
    try:
        root = ElementTree.fromstring(text.encode("utf-8"))
    except ElementTree.ParseError as exc:
        raise SiteFileError("the file is not valid KML") from exc
    out: list[tuple[list, list[list]]] = []
    for poly in root.iter():
        if _local(poly.tag) != "Polygon":
            continue
        outer: list = []
        holes: list[list] = []
        for boundary in poly:
            kind = _local(boundary.tag)
            if kind not in ("outerBoundaryIs", "innerBoundaryIs"):
                continue
            for ring in boundary.iter():
                if _local(ring.tag) == "coordinates":
                    pts = _coords(ring.text)
                    if kind == "outerBoundaryIs":
                        outer = pts
                    else:
                        holes.append(pts)
        if outer:
            out.append((outer, holes))
    return out


def _read_text(data: bytes, name: str) -> tuple[str, str]:
    """(text, kind) of the file content; kind is 'kml' or 'geojson'."""
    lower = name.lower()
    if lower.endswith(".kmz") or data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                kml = next((n for n in z.namelist() if n.lower().endswith(".kml")), None)
                if kml is None:
                    raise SiteFileError("the KMZ file has no KML inside")
                return z.read(kml).decode("utf-8", "replace"), "kml"
        except zipfile.BadZipFile as exc:
            raise SiteFileError("the KMZ file is damaged") from exc
    text = data.decode("utf-8-sig", "replace")
    if lower.endswith((".kml", ".xml")) or text.lstrip().startswith("<"):
        return text, "kml"
    return text, "geojson"


def read_polygons(data: bytes, name: str = "") -> list[tuple[Ring, list[Ring]]]:
    """Every polygon of the file as (outer ring, holes) in (lon, lat); invalid ones are dropped."""
    text, kind = _read_text(data, name)
    raw = _parse_kml(text) if kind == "kml" else _parse_geojson(text)
    out = []
    for outer, holes in raw:
        ring = _clean([(float(p[0]), float(p[1])) for p in outer])
        if not _ring_ok(ring):
            continue
        good = [tuple(r) for r in (_clean([(float(p[0]), float(p[1])) for p in h])
                                   for h in holes) if _ring_ok(r)]
        out.append((tuple(ring), good))
    if not out:
        raise SiteFileError("no polygon was found in the file (draw the site as a polygon)")
    return out


def project(ring: Ring, lat0: float, lon0: float) -> Ring:
    """(lon, lat) -> (east, north) metres from (lat0, lon0)."""
    kx = M_PER_DEG * math.cos(math.radians(lat0))
    return tuple(((lon - lon0) * kx, (lat - lat0) * M_PER_DEG) for lon, lat in ring)


def site_from_file(data: bytes, name: str = "") -> SiteShape:
    """The biggest polygon of the file is the site; its holes become exclusion zones.

    The origin is the centre of the bounding box of the site."""
    polys = read_polygons(data, name)
    outer, holes = max(polys, key=lambda p: ring_area(p[0]))
    lons = [p[0] for p in outer]
    lats = [p[1] for p in outer]
    lon0, lat0 = (min(lons) + max(lons)) / 2.0, (min(lats) + max(lats)) / 2.0
    if max(lons) - min(lons) > 2.0 or max(lats) - min(lats) > 2.0:
        raise SiteFileError("the polygon is larger than 2 degrees: this is not a wind farm site")
    return SiteShape(lat0, lon0, project(outer, lat0, lon0),
                     tuple(project(h, lat0, lon0) for h in holes), name)


def exclusions_from_file(data: bytes, name: str, lat0: float, lon0: float) -> tuple[Ring, ...]:
    """Every polygon of the file, as exclusion zones around the site centre (lat0, lon0)."""
    rings = []
    for outer, _holes in read_polygons(data, name):
        rings.append(project(outer, lat0, lon0))
    return tuple(rings)
