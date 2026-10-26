"""Satellite picture under the wind-farm map: web-mercator tiles around the site (Qt-free).

The site centre (the latitude and longitude typed in the wizard) is the origin of the local
east/north frame of the layout. Tiles of Esri World Imagery are downloaded, kept in a cache folder
and placed on the map at their true size in metres. Any failure gives an empty result with a
readable note: the map is then drawn without the picture.
"""

from __future__ import annotations

import math
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TILE_URL = ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/"
            "tile/{z}/{y}/{x}")
ATTRIBUTION = "Imagery: Esri, Maxar, Earthstar Geographics and the GIS User Community"
EARTH_M_PER_PX_Z0 = 156543.03392      # metres per pixel at the equator, zoom 0
TILE_PX = 256
MAX_TILES = 20
MAX_ZOOM = 18


@dataclass(frozen=True)
class Tile:
    west_m: float          # east coordinate of the left edge, metres from the site centre
    north_m: float         # north coordinate of the top edge
    size_m: float          # true side length in metres
    data: bytes            # JPEG


@dataclass(frozen=True)
class Satellite:
    tiles: tuple[Tile, ...] = ()
    attribution: str = ATTRIBUTION
    note: str = ""         # why there are no tiles, when it failed

    @property
    def ok(self) -> bool:
        return bool(self.tiles)


def _world_px(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    n = TILE_PX * 2 ** zoom
    x = (lon + 180.0) / 360.0 * n
    s = math.sin(math.radians(max(-85.0511, min(85.0511, lat))))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def metres_per_pixel(lat: float, zoom: int) -> float:
    return EARTH_M_PER_PX_Z0 * math.cos(math.radians(lat)) / 2 ** zoom


def choose_zoom(lat: float, lon: float, window: tuple[float, float, float, float],
                max_tiles: int = MAX_TILES) -> int:
    """The sharpest zoom for which the window needs at most ``max_tiles`` tiles."""
    for z in range(MAX_ZOOM, 0, -1):
        if len(tile_grid(lat, lon, window, z)) <= max_tiles:
            return z
    return 1


def tile_grid(lat: float, lon: float, window: tuple[float, float, float, float],
              zoom: int) -> list[tuple[int, int]]:
    """(x, y) of the tiles covering the window (x_lo, x_hi, y_lo, y_hi), metres from the centre."""
    x_lo, x_hi, y_lo, y_hi = window
    cx, cy = _world_px(lat, lon, zoom)
    mpp = metres_per_pixel(lat, zoom)
    n = 2 ** zoom
    x0 = math.floor((cx + x_lo / mpp) / TILE_PX)
    x1 = math.floor((cx + x_hi / mpp) / TILE_PX)
    y0 = math.floor((cy - y_hi / mpp) / TILE_PX)
    y1 = math.floor((cy - y_lo / mpp) / TILE_PX)
    return [(x % n, y) for y in range(max(y0, 0), min(y1, n - 1) + 1) for x in range(x0, x1 + 1)]


def _cache_dir() -> Path:
    return Path.home() / ".cache" / "resize_energy" / "tiles"


def _get(url: str, cache: Path | None, timeout: float,
         urlopen: Callable[..., Any]) -> bytes:
    if cache is not None and cache.exists():
        return cache.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": "RESize/0.1 (education)"})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    if data[:2] != b"\xff\xd8" and data[:4] != b"\x89PNG":
        raise ValueError("the server did not send a picture")
    if cache is not None:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(data)
        except OSError:
            pass
    return data


def fetch_satellite(lat: float, lon: float, window: tuple[float, float, float, float],
                    timeout: float = 15.0, urlopen: Callable[..., Any] = urllib.request.urlopen,
                    cache_dir: Path | None = None) -> Satellite:
    """Tiles covering ``window`` (metres east/north of the site centre). Never raises."""
    if not (-85.0 < lat < 85.0 and -180.0 <= lon <= 180.0):
        return Satellite(note="The satellite picture needs a latitude between -85 and 85.")
    try:
        zoom = choose_zoom(lat, lon, window)
        cx, cy = _world_px(lat, lon, zoom)
        mpp = metres_per_pixel(lat, zoom)
        base = cache_dir if cache_dir is not None else _cache_dir()
        tiles = []
        for x, y in tile_grid(lat, lon, window, zoom):
            data = _get(TILE_URL.format(z=zoom, x=x, y=y), base / f"{zoom}_{x}_{y}.jpg",
                        timeout, urlopen)
            # x may have wrapped round the date line: place the tile by its unwrapped column
            col = x
            n = 2 ** zoom
            if abs(col * TILE_PX - cx) > n * TILE_PX / 2:
                col += n if col * TILE_PX < cx else -n
            tiles.append(Tile((col * TILE_PX - cx) * mpp, -(y * TILE_PX - cy) * mpp,
                              TILE_PX * mpp, data))
        return Satellite(tuple(tiles))
    except Exception as exc:   # noqa: BLE001 - any network or format problem just drops the picture
        return Satellite(note=f"The satellite picture could not be downloaded ({exc}).")
