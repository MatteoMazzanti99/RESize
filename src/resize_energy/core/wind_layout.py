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


Ring = tuple[tuple[float, float], ...]


def _in_ring(points: np.ndarray, ring: Ring) -> np.ndarray:
    """Even-odd test of every point (m, 2) against a ring, vectorised."""
    x, y = points[:, 0], points[:, 1]
    inside = np.zeros(len(points), dtype=bool)
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if y1 == y2:
            continue
        crosses = (y1 > y) != (y2 > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            x_at = (x2 - x1) * (y - y1) / (y2 - y1) + x1
        inside ^= crosses & (x < x_at)
    return inside


def _dist_to_ring(points: np.ndarray, ring: Ring) -> np.ndarray:
    """Distance of every point to the edges of a ring."""
    a = np.array(ring, dtype=float)
    b = np.roll(a, -1, axis=0)
    ab = b - a
    ab2 = np.maximum((ab ** 2).sum(axis=1), 1e-12)
    ap = points[:, None, :] - a[None, :, :]
    t = np.clip((ap * ab[None]).sum(axis=2) / ab2[None], 0.0, 1.0)
    nearest = a[None] + t[..., None] * ab[None]
    return np.sqrt(((points[:, None, :] - nearest) ** 2).sum(axis=2)).min(axis=1)


@dataclass(frozen=True)
class SiteArea:
    """The land of the farm: a rectangle centred on the origin, or a polygon.

    Rectangle: ``rotation_deg`` is the compass bearing of its length axis (0: the length runs
    north-south, 90: east-west). Polygon: ``polygon`` is the boundary in metres east/north, with
    ``exclusions`` (houses, roads, wetlands...) where nothing may stand; turbines also keep
    ``setback_m`` from the boundary and from every exclusion. ``width_m`` and ``length_m`` are
    then the size of its bounding box."""

    width_m: float
    length_m: float
    rotation_deg: float = 0.0
    polygon: Ring = ()
    exclusions: tuple[Ring, ...] = ()
    setback_m: float = 0.0

    def __post_init__(self) -> None:
        if self.width_m <= 0 or self.length_m <= 0:
            raise ValueError("the site width and length must be > 0")
        if self.setback_m < 0:
            raise ValueError("the setback cannot be negative")

    @classmethod
    def from_polygon(cls, boundary: Ring, exclusions: tuple[Ring, ...] = (),
                     setback_m: float = 0.0) -> SiteArea:
        if len(boundary) < 3:
            raise ValueError("the site boundary needs at least three corners")
        xs, ys = [p[0] for p in boundary], [p[1] for p in boundary]
        return cls(max(xs) - min(xs), max(ys) - min(ys), 0.0, tuple(boundary),
                   tuple(tuple(r) for r in exclusions), setback_m)

    @property
    def is_polygon(self) -> bool:
        return bool(self.polygon)

    def bounds(self) -> tuple[float, float, float, float]:
        """(x_lo, x_hi, y_lo, y_hi) of the local frame that holds the area."""
        if self.is_polygon:
            xs, ys = [p[0] for p in self.polygon], [p[1] for p in self.polygon]
            return min(xs), max(xs), min(ys), max(ys)
        return -self.width_m / 2.0, self.width_m / 2.0, -self.length_m / 2.0, self.length_m / 2.0

    def allowed(self, points: np.ndarray, setback: float | None = None) -> np.ndarray:
        """Which of the points (m, 2), in the local frame, may host a turbine."""
        pts = np.asarray(points, dtype=float).reshape(-1, 2)
        if not self.is_polygon:
            x_lo, x_hi, y_lo, y_hi = self.bounds()
            return ((pts[:, 0] >= x_lo - 1e-9) & (pts[:, 0] <= x_hi + 1e-9)
                    & (pts[:, 1] >= y_lo - 1e-9) & (pts[:, 1] <= y_hi + 1e-9))
        gap = self.setback_m if setback is None else setback
        ok = _in_ring(pts, self.polygon)
        if gap > 0 and ok.any():
            ok &= _dist_to_ring(pts, self.polygon) >= gap - 1e-9
        for ring in self.exclusions:
            if not ok.any():
                break
            bad = _in_ring(pts, ring)
            if gap > 0:
                bad |= _dist_to_ring(pts, ring) < gap - 1e-9
            ok &= ~bad
        return ok

    def sample_point(self, rng: np.random.Generator) -> np.ndarray:
        x_lo, x_hi, y_lo, y_hi = self.bounds()
        return np.array([rng.uniform(x_lo, x_hi), rng.uniform(y_lo, y_hi)])

    @property
    def area_km2(self) -> float:
        """Area of the land, exclusion zones taken out (no setback)."""
        if not self.is_polygon:
            return self.width_m * self.length_m / 1e6
        return self.usable_area_km2(0.0)

    def usable_area_km2(self, setback: float | None = None) -> float:
        """Area where a turbine may stand (setbacks and exclusions taken out)."""
        if not self.is_polygon:
            return self.width_m * self.length_m / 1e6
        x_lo, x_hi, y_lo, y_hi = self.bounds()
        n = 160
        gx = x_lo + (np.arange(n) + 0.5) * (x_hi - x_lo) / n
        gy = y_lo + (np.arange(n) + 0.5) * (y_hi - y_lo) / n
        grid = np.array([(x, y) for y in gy for x in gx])
        share = float(self.allowed(grid, setback).mean())
        return share * (x_hi - x_lo) * (y_hi - y_lo) / 1e6

    def to_world(self, x: float, y: float) -> tuple[float, float]:
        """Local (across, along) metres -> (east, north) metres."""
        r = math.radians(self.rotation_deg)
        return x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)

    def corners(self) -> list[tuple[float, float]]:
        if self.is_polygon:
            return list(self.polygon)
        hw, hl = self.width_m / 2.0, self.length_m / 2.0
        return [self.to_world(x, y) for x, y in ((-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl))]

    def contains(self, east: float, north: float, tol: float = 1e-6) -> bool:
        if self.is_polygon:
            gap = max(self.setback_m - tol, 0.0)
            return bool(self.allowed(np.array([[east, north]]), gap)[0])
        r = math.radians(self.rotation_deg)
        x = east * math.cos(r) - north * math.sin(r)
        y = east * math.sin(r) + north * math.cos(r)
        return abs(x) <= self.width_m / 2 + tol and abs(y) <= self.length_m / 2 + tol


def _hex_lattice(area: SiteArea, spacing: float) -> np.ndarray:
    """Points of a hexagonal lattice (local coordinates) that fit in the area."""
    x_lo, x_hi, y_lo, y_hi = area.bounds()
    dy = spacing * math.sqrt(3.0) / 2.0
    rows = int((y_hi - y_lo) // dy) + 1
    pts = []
    for r in range(rows):
        y = y_lo + r * dy
        if y > y_hi + 1e-9:
            break
        shift = spacing / 2.0 if r % 2 else 0.0
        x0 = x_lo + shift
        cols = int((x_hi - x_lo - shift) // spacing) + 1
        pts += [(x0 + c * spacing, y) for c in range(cols) if x0 + c * spacing <= x_hi + 1e-9]
    lattice = np.array(pts, dtype=float).reshape(-1, 2)
    if area.is_polygon and len(lattice):
        lattice = lattice[area.allowed(lattice)]
    return lattice


def max_turbines(area: SiteArea, min_distance_m: float) -> int:
    """How many turbines fit at the minimum distance (a hexagonal lattice, a good estimate)."""
    if area.is_polygon:
        return len(_hex_lattice(area, min_distance_m))
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
        x_lo, x_hi, y_lo, y_hi = area.bounds()
        t0, t1 = max(cost, 0.01) * 0.15, 1e-5
        for step in range(steps):
            temp = t0 * (t1 / t0) ** (step / steps)
            k = int(rng.integers(n))
            if rng.random() < 0.25:
                q = area.sample_point(rng)
            else:
                reach = (0.5 + 3.0 * (1.0 - step / steps)) * min_dist
                q = pos[k] + rng.normal(0.0, reach / 2.0, 2)
                q = np.array([min(max(q[0], x_lo), x_hi), min(max(q[1], y_lo), y_hi)])
            if area.is_polygon and not area.allowed(q[None])[0]:
                continue
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
