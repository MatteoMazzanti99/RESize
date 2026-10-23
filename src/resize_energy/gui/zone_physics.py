"""Movement of the icons in the Compare zone (no Qt, so it can be tested anywhere)."""

from __future__ import annotations

import math

ICON_SIZE = 46


def advance(items: dict[str, list[float]], width: float, height: float,
            size: float = ICON_SIZE) -> None:
    """One animation step: every item is [x, y, vx, vy]; walls and other icons bounce it."""
    for item in items.values():
        item[0] += item[2]
        item[1] += item[3]
        if item[0] < 0:
            item[0], item[2] = 0.0, abs(item[2])
        elif item[0] > width - size:
            item[0], item[2] = max(0.0, width - size), -abs(item[2])
        if item[1] < 0:
            item[1], item[3] = 0.0, abs(item[3])
        elif item[1] > height - size:
            item[1], item[3] = max(0.0, height - size), -abs(item[3])
    keys = list(items)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            ia, ib = items[a], items[b]
            dx, dy = ib[0] - ia[0], ib[1] - ia[1]
            if math.hypot(dx, dy) < size:
                ia[2], ib[2] = ib[2], ia[2]
                ia[3], ib[3] = ib[3], ia[3]
                if dx == 0 and dy == 0:
                    ib[0] += 1.0
