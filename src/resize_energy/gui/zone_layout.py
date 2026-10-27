"""Layout and motion of the icons in the Compare zone (no Qt, so it can be tested anywhere).

The icons stand facing each other with a "VS" between neighbours, bob gently, pop in when
dropped and rush towards the middle when the comparison starts.
"""

from __future__ import annotations

import math

ICON_SIZE = 46
CLASH_SECONDS = 0.65


def slot_centres(n: int, width: float, height: float) -> list[tuple[float, float]]:
    """Centres of ``n`` icons, evenly spread on a line in the middle of the arena."""
    cy = height / 2.0 - 6.0
    return [(width * (i + 1) / (n + 1), cy) for i in range(n)]


def vs_centres(centres: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Where the 'VS' badges go: halfway between neighbouring icons."""
    return [((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            for a, b in zip(centres, centres[1:], strict=False)]


def bob(t_seconds: float, index: int, amplitude: float = 3.0) -> float:
    """Vertical offset of an icon that breathes up and down."""
    return amplitude * math.sin(2.0 * math.pi * 0.55 * t_seconds + index * 1.3)


def pop_scale(age_seconds: float) -> float:
    """Size factor of an icon dropped ``age_seconds`` ago: grows from 0.3 with a small overshoot."""
    if age_seconds >= 0.3:
        return 1.0
    x = max(0.0, age_seconds) / 0.3
    c1, c3 = 1.70158, 2.70158
    ease = 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2   # ease-out-back
    return 0.3 + 0.7 * ease


def clash_x(x: float, centre_x: float, progress: float) -> float:
    """Horizontal position of an icon during the clash (progress 0..1): in, hit, back a bit."""
    p = min(1.0, max(0.0, progress))
    if p < 0.55:
        k = (p / 0.55) ** 2 * 0.62          # accelerate towards the middle
    else:
        k = 0.62 - ((p - 0.55) / 0.45) * 0.12   # recoil
    return x + (centre_x - x) * k


def flash_alpha(progress: float) -> int:
    """Opacity (0..255) of the flash at the moment of the hit."""
    d = abs(progress - 0.55)
    return int(max(0.0, 1.0 - d / 0.14) * 200)


def autoscroll_step(y: float, top: float, bottom: float, margin: float = 90.0,
                    max_step: float = 26.0) -> int:
    """Pixels to scroll while a drag is held at height ``y`` in a view spanning top..bottom.

    Negative scrolls up, positive scrolls down; zero in the middle of the view. The step grows
    from 0 at the inner edge of the margin to ``max_step`` at (and beyond) the view edge.
    """
    if bottom - top < 2 * margin:
        margin = max(1.0, (bottom - top) / 2.0)
    if y < top + margin:
        return -round(max_step * min(1.0, (top + margin - y) / margin))
    if y > bottom - margin:
        return round(max_step * min(1.0, (y - (bottom - margin)) / margin))
    return 0
