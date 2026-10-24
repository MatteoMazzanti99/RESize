"""A coarse, offline answer to "is this latitude/longitude in that country?".

Each country is a few latitude/longitude boxes that follow its shape roughly (mainland and
islands). The check is meant to catch clearly wrong choices, such as a site in Italy with the
country set to Australia. Near a border the boxes of two countries overlap, so a site close to
a border may pass for either: do not use it for anything else.
"""

from __future__ import annotations

Box = tuple[float, float, float, float]   # south, north, west, east (degrees)

MARGIN_DEG = 0.25   # about 25 km: a site just outside a box still counts as inside

BOXES: dict[str, tuple[Box, ...]] = {
    "AU": ((-44.0, -10.0, 112.0, 154.0),),
    "BR": ((-34.0, 5.5, -74.0, -34.0),),
    "CA": ((41.6, 83.2, -141.0, -52.0),),
    "CN": ((18.0, 53.6, 73.5, 135.1),),
    "FR": ((42.3, 51.1, -5.2, 2.6), (42.4, 46.2, 2.6, 7.1), (46.2, 49.5, 2.6, 8.3),
           (49.5, 51.1, 2.6, 6.2), (43.2, 44.2, 7.1, 7.8), (41.3, 43.1, 8.5, 9.6)),
    "DE": ((47.2, 55.1, 5.8, 15.1),),
    "IN": ((6.7, 35.7, 68.0, 97.5),),
    "IT": ((43.7, 47.1, 6.6, 13.9), (41.2, 43.7, 10.0, 14.2), (40.8, 41.4, 12.4, 14.2),
           (37.9, 41.4, 14.0, 18.6), (36.6, 38.4, 12.3, 15.7), (38.8, 41.3, 8.1, 9.9),
           (35.4, 35.7, 12.4, 12.8)),
    "JP": ((24.0, 45.6, 122.9, 146.0),),
    "MX": ((14.5, 32.8, -118.5, -86.7),),
    "NL": ((50.7, 53.6, 3.3, 7.3),),
    "PL": ((49.0, 54.9, 14.1, 24.2),),
    "ZA": ((-35.0, -22.0, 16.4, 33.0),),
    "KR": ((33.0, 38.7, 124.5, 131.9),),
    "ES": ((36.0, 42.6, -9.4, 3.4), (42.6, 43.8, -9.4, -1.3), (38.6, 40.2, 1.1, 4.4),
           (27.5, 29.5, -18.3, -13.3)),
    "TR": ((35.8, 42.2, 25.6, 44.9),),
    "GB": ((49.9, 58.7, -6.4, 1.8), (54.0, 55.3, -8.2, -5.4), (59.0, 60.9, -2.0, -0.7)),
    "US": ((24.4, 49.5, -125.0, -66.9), (51.0, 71.5, -180.0, -129.0), (18.8, 22.4, -160.6, -154.7)),
}


def _inside(box: Box, lat: float, lon: float, margin: float) -> bool:
    south, north, west, east = box
    return south - margin <= lat <= north + margin and west - margin <= lon <= east + margin


def in_country(code: str, lat: float, lon: float, margin: float = MARGIN_DEG) -> bool | None:
    """True/False if the point is in the country; None when the country has no boxes."""
    boxes = BOXES.get(code)
    if boxes is None:
        return None
    return any(_inside(b, lat, lon, margin) for b in boxes)


def countries_at(lat: float, lon: float) -> list[str]:
    """Codes of the countries whose boxes contain the point (without any margin)."""
    return [code for code, boxes in BOXES.items() if any(_inside(b, lat, lon, 0.0) for b in boxes)]
