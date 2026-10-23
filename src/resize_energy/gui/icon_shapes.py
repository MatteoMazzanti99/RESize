"""Technology icons as plain geometry on a 24 x 24 grid (no Qt, so it can be tested).

Each icon is a list of shapes ``(points, closed, filled)``. The GUI draws them with a round pen in
the accent colour (see ``icons.py``); curves are already flattened into short segments.
"""

from __future__ import annotations

import math

Point = tuple[float, float]
Shape = tuple[list[Point], bool, bool]  # points, closed, filled

GRID = 24.0
STROKE = 1.7  # pen width on the 24-unit grid


def cubic(p0: Point, p1: Point, p2: Point, p3: Point, steps: int = 14) -> list[Point]:
    """Points of a cubic Bezier curve (without the start point)."""
    out: list[Point] = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1 - t
        x = u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]
        out.append((x, y))
    return out


def circle(cx: float, cy: float, r: float, steps: int = 24) -> list[Point]:
    return [(cx + r * math.cos(2 * math.pi * i / steps), cy + r * math.sin(2 * math.pi * i / steps))
            for i in range(steps)]


def blade(hub: Point, angle_deg: float, length: float, half_width: float) -> list[Point]:
    """A slim triangle from the hub outwards."""
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    px, py = -dy, dx
    tip = (hub[0] + length * dx, hub[1] + length * dy)
    return [(hub[0] + half_width * px, hub[1] + half_width * py), tip,
            (hub[0] - half_width * px, hub[1] - half_width * py)]


def _photovoltaic() -> list[Shape]:
    panel = [(6.0, 5.0), (21.0, 5.0), (18.0, 15.0), (3.0, 15.0)]
    return [
        (panel, True, False),
        ([(11.0, 5.0), (8.0, 15.0)], False, False),
        ([(16.0, 5.0), (13.0, 15.0)], False, False),
        ([(4.5, 10.0), (19.5, 10.0)], False, False),
        ([(10.5, 15.0), (10.5, 20.0)], False, False),
        ([(6.5, 20.5), (14.5, 20.5)], False, False),
    ]


def _wind() -> list[Shape]:
    hub = (12.0, 9.5)
    tower = [(11.2, 21.5), (12.8, 21.5), (12.3, 11.0), (11.7, 11.0)]
    return [
        (tower, True, True),
        (blade(hub, -75, 9.0, 0.45), True, True),
        (blade(hub, 45, 9.0, 0.45), True, True),
        (blade(hub, 165, 9.0, 0.45), True, True),
        (circle(*hub, 1.5), True, True),
    ]


def _biomass() -> list[Shape]:
    start = (4.5, 19.5)
    leaf = [start]
    leaf += cubic(start, (3.5, 9.5), (10.0, 4.0), (20.0, 4.0))
    leaf += cubic((20.0, 4.0), (20.5, 14.5), (15.0, 20.5), start)
    return [
        (leaf, True, False),
        ([(4.5, 19.5), (14.0, 10.0)], False, False),
    ]


def _hydrogen() -> list[Shape]:
    top = (12.0, 2.5)
    drop = [top]
    drop += cubic(top, (12.0, 2.5), (5.0, 10.5), (5.0, 15.0))
    drop += cubic((5.0, 15.0), (5.0, 19.0), (8.2, 21.8), (12.0, 21.8))
    drop += cubic((12.0, 21.8), (15.8, 21.8), (19.0, 19.0), (19.0, 15.0))
    drop += cubic((19.0, 15.0), (19.0, 10.5), (12.0, 2.5), top)
    return [
        (drop, True, False),
        ([(9.2, 12.5), (9.2, 18.0)], False, False),   # H
        ([(14.8, 12.5), (14.8, 18.0)], False, False),
        ([(9.2, 15.25), (14.8, 15.25)], False, False),
    ]


def _battery() -> list[Shape]:
    return [
        ([(3.0, 7.0), (19.0, 7.0), (19.0, 17.0), (3.0, 17.0)], True, False),   # body
        ([(19.0, 10.0), (21.5, 10.0), (21.5, 14.0), (19.0, 14.0)], True, False),  # terminal
        ([(6.0, 10.0), (6.0, 14.0)], False, False),     # charge bars
        ([(9.5, 10.0), (9.5, 14.0)], False, False),
        ([(13.0, 10.0), (13.0, 14.0)], False, False),
    ]


def _solar_thermal() -> list[Shape]:
    sun = (9.0, 9.0)
    rays: list[Shape] = []
    for k in range(8):
        a = math.radians(45.0 * k)
        rays.append(([(sun[0] + 4.6 * math.cos(a), sun[1] + 4.6 * math.sin(a)),
                      (sun[0] + 6.6 * math.cos(a), sun[1] + 6.6 * math.sin(a))], False, False))
    return [
        (circle(*sun, 2.8), True, False),
        *rays,
        ([(11.0, 20.0), (22.0, 20.0), (22.0, 15.0), (14.0, 12.5)], False, False),  # collector
    ]


ICONS: dict[str, list[Shape]] = {
    "pv": _photovoltaic(),
    "wind": _wind(),
    "biomass": _biomass(),
    "hydrogen": _hydrogen(),
    "battery": _battery(),
    "solar": _solar_thermal(),
}
