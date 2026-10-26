"""Place the turbines of a wind farm inside a site area, using the wind rose.

The program, not the user, decides where every turbine stands. The area is a rectangle (width
x length, turned by a bearing); turbines must stay inside it and at least ``min_spacing`` rotor
diameters from each other. The search is a simulated annealing on a fast surrogate of the wake
loss (Jensen deficits at a typical thrust, combined by root-sum-square, weighted by the energy
that each wind direction brings); the winning layout is then evaluated with the full wake
model by the caller. Pure calculation with numpy, no GUI; the result is deterministic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

CT_SURROGATE = 0.75        # thrust coefficient used by the surrogate: a typical value below rated


@dataclass(frozen=True)
class SiteArea:
    """A rectangle centred on the origin. ``rotation_deg`` is the compass bearing of its length
    axis (0: the length runs north-south, 90: east-west)."""

    width_m: float
    length_m: float
    rotation_deg: float = 0.0

    def __post_init__(self) -> None:
        if self.width_m <= 0 or self.length_m <= 0:
            raise ValueError("the site width and length must be > 0")

    @property
    def area_km2(self) -> float:
        return self.width_m * self.length_m / 1e6

    def to_world(self, x: float, y: float) -> tuple[float, float]:
        """Local (across, along) metres -> (east, north) metres."""
        r = math.radians(self.rotation_deg)
        return x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)

    def corners(self) -> list[tuple[float, float]]:
        hw, hl = self.width_m / 2.0, self.length_m / 2.0
        return [self.to_world(x, y) for x, y in ((-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl))]

    def contains(self, east: float, north: float, tol: float = 1e-6) -> bool:
        r = math.radians(self.rotation_deg)
        x = east * math.cos(r) - north * math.sin(r)
        y = east * math.sin(r) + north * math.cos(r)
        return abs(x) <= self.width_m / 2 + tol and abs(y) <= self.length_m / 2 + tol


def _hex_lattice(area: SiteArea, spacing: float) -> np.ndarray:
    """Points of a hexagonal lattice (local coordinates) that fit in the rectangle."""
    hw, hl = area.width_m / 2.0, area.length_m / 2.0
    dy = spacing * math.sqrt(3.0) / 2.0
    rows = int(area.length_m // dy) + 1
    pts = []
    for r in range(rows):
        y = -hl + r * dy
        if y > hl + 1e-9:
            break
        x0 = -hw + (spacing / 2.0 if r % 2 else 0.0)
        cols = int((area.width_m - (spacing / 2.0 if r % 2 else 0.0)) // spacing) + 1
        pts += [(x0 + c * spacing, y) for c in range(cols) if x0 + c * spacing <= hw + 1e-9]
    return np.array(pts, dtype=float).reshape(-1, 2)


def max_turbines(area: SiteArea, min_distance_m: float) -> int:
    """How many turbines fit at the minimum distance (a hexagonal lattice, a good estimate)."""
    best = 0
    for flip in (False, True):
        a = SiteArea(area.length_m, area.width_m) if flip else SiteArea(area.width_m, area.length_m)
        best = max(best, len(_hex_lattice(a, min_distance_m)))
    return best


def _spread_subset(points: np.ndarray, n: int) -> np.ndarray:
    """``n`` well spread points out of ``points`` (farthest-point sampling)."""
    if n >= len(points):
        return points
    centre = points.mean(axis=0)
    chosen = [int(np.argmax(np.linalg.norm(points - centre, axis=1)))]
    dist = np.linalg.norm(points - points[chosen[0]], axis=1)
    while len(chosen) < n:
        nxt = int(np.argmax(dist))
        chosen.append(nxt)
        dist = np.minimum(dist, np.linalg.norm(points - points[nxt], axis=1))
    return points[chosen]


def initial_layout(n: int, area: SiteArea, min_distance_m: float) -> np.ndarray:
    """Local coordinates of ``n`` turbines on the widest hexagonal lattice that holds them."""
    if n < 1:
        raise ValueError("at least one turbine is needed")
    lo, hi = min_distance_m, max(area.width_m, area.length_m)
    if len(_hex_lattice(area, lo)) < n:
        raise ValueError(
            f"the site is too small for {n} turbines at {min_distance_m:.0f} m from each "
            f"other: about {max_turbines(area, min_distance_m)} fit. Make the area bigger or "
            "the minimum spacing smaller.")
    for _ in range(30):                                 # widest spacing that still holds n
        mid = (lo + hi) / 2.0
        if len(_hex_lattice(area, mid)) >= n:
            lo = mid
        else:
            hi = mid
    return _spread_subset(_hex_lattice(area, lo), n)


# --- surrogate of the wake loss --------------------------------------------------------------
def _overlap(r_w: np.ndarray, r0: float, d: np.ndarray) -> np.ndarray:
    """Share of the rotor disc inside the wake cone (r_w >= r0 always), vectorised."""
    out = np.zeros_like(d)
    full = d <= r_w - r0
    out[full] = 1.0
    part = (~full) & (d < r_w + r0)
    if part.any():
        rw, dd = r_w[part], d[part]
        a1 = np.clip((dd * dd + rw * rw - r0 * r0) / (2.0 * dd * rw), -1.0, 1.0)
        a2 = np.clip((dd * dd + r0 * r0 - rw * rw) / (2.0 * dd * r0), -1.0, 1.0)
        root = (-dd + rw + r0) * (dd + rw - r0) * (dd - rw + r0) * (dd + rw + r0)
        area = (rw * rw * np.arccos(a1) + r0 * r0 * np.arccos(a2)
                - 0.5 * np.sqrt(np.maximum(root, 0.0)))
        out[part] = area / (math.pi * r0 * r0)
    return out


class _Surrogate:
    """Deficits between turbines for every wind sector, in the local frame of the area."""

    def __init__(self, rotor_d: float, decay: float, weights: tuple[float, ...],
                 rotation_deg: float) -> None:
        sectors = len(weights)
        theta = np.radians(np.arange(sectors) * 360.0 / sectors - rotation_deg)
        self.dx, self.dy = -np.sin(theta), -np.cos(theta)           # direction of travel
        self.cx, self.cy = np.cos(theta), -np.sin(theta)            # across the wind
        w = np.array(weights, dtype=float)
        self.w = w / w.sum()
        self.r0 = rotor_d / 2.0
        self.decay = decay
        self.base = 1.0 - math.sqrt(1.0 - CT_SURROGATE)

    def deficits(self, src: np.ndarray, dst: np.ndarray) -> np.ndarray:
        """(sectors, len(src), len(dst)): speed deficit that each source causes on each target."""
        ddx = dst[None, :, 0] - src[:, None, 0]
        ddy = dst[None, :, 1] - src[:, None, 1]
        u = ddx[None] * self.dx[:, None, None] + ddy[None] * self.dy[:, None, None]
        cross = np.abs(ddx[None] * self.cx[:, None, None] + ddy[None] * self.cy[:, None, None])
        ahead = u > 1e-6
        r_w = self.r0 + self.decay * np.where(ahead, u, 0.0)
        frac = _overlap(r_w, self.r0, cross)
        return np.where(ahead, self.base * (self.r0 / r_w) ** 2 * frac, 0.0)

    def sum_squares(self, pos: np.ndarray) -> np.ndarray:
        """(sectors, n): sum over upwind turbines of deficit squared, for every turbine."""
        return (self.deficits(pos, pos) ** 2).sum(axis=1)

    def loss(self, ss: np.ndarray) -> float:
        """Energy lost to wakes (0-1), taking the power as the cube of the speed."""
        speed = 1.0 - np.sqrt(ss)
        return float(1.0 - (self.w * (speed ** 3).mean(axis=1)).sum())


def surrogate_loss(positions: list[tuple[float, float]], rotor_d: float, decay: float,
                   weights: tuple[float, ...]) -> float:
    """The fast wake-loss estimate of a layout in world coordinates (east, north)."""
    s = _Surrogate(rotor_d, decay, weights, 0.0)
    return s.loss(s.sum_squares(np.array(positions, dtype=float).reshape(-1, 2)))


def optimise_layout(n: int, area: SiteArea, rotor_d: float, min_spacing_d: float,
                    weights: tuple[float, ...], decay: float, steps: int = 6000,
                    seed: int = 1) -> list[tuple[float, float]]:
    """Positions (east, north) in metres of ``n`` turbines that minimise the wake loss.

    ``weights`` is the share of the wind energy of each sector. Raises ValueError when the
    turbines do not fit in the area at the minimum spacing."""
    if rotor_d <= 0 or min_spacing_d < 1.0:
        raise ValueError("the rotor diameter must be > 0 and the minimum spacing >= 1 D")
    min_dist = min_spacing_d * rotor_d
    pos = initial_layout(n, area, min_dist)
    if n > 1 and steps > 0:
        sur = _Surrogate(rotor_d, decay, weights, area.rotation_deg)
        rng = np.random.default_rng(seed)
        ss = sur.sum_squares(pos)
        cost = sur.loss(ss)
        best, best_cost = pos.copy(), cost
        hw, hl = area.width_m / 2.0, area.length_m / 2.0
        t0, t1 = max(cost, 0.01) * 0.15, 1e-5
        for step in range(steps):
            temp = t0 * (t1 / t0) ** (step / steps)
            k = int(rng.integers(n))
            if rng.random() < 0.25:
                q = np.array([rng.uniform(-hw, hw), rng.uniform(-hl, hl)])
            else:
                reach = (0.5 + 3.0 * (1.0 - step / steps)) * min_dist
                q = pos[k] + rng.normal(0.0, reach / 2.0, 2)
                q = np.array([min(max(q[0], -hw), hw), min(max(q[1], -hl), hl)])
            others = np.delete(pos, k, axis=0)
            if others.size and np.min(np.linalg.norm(others - q, axis=1)) < min_dist - 1e-9:
                continue
            out_old = sur.deficits(pos[k:k + 1], pos)[:, 0, :]
            out_new = sur.deficits(q[None], pos)[:, 0, :]
            in_new = sur.deficits(others, q[None])[:, :, 0]
            out_old[:, k] = 0.0
            out_new[:, k] = 0.0
            ss_new = ss - out_old ** 2 + out_new ** 2
            ss_new[:, k] = (in_new ** 2).sum(axis=1)
            ss_new = np.maximum(ss_new, 0.0)
            new_cost = sur.loss(ss_new)
            if new_cost < cost or rng.random() < math.exp(-(new_cost - cost) / temp):
                pos[k], ss, cost = q, ss_new, new_cost
                if cost < best_cost - 1e-12:
                    best, best_cost = pos.copy(), cost
        pos = best
    world = [area.to_world(float(x), float(y)) for x, y in pos]
    return sorted(world, key=lambda p: (round(p[1], 3), p[0]), reverse=True)
