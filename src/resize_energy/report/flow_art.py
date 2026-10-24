"""Small animated-looking energy-flow pictures, drawn as SVG text (Qt-free).

A picture is a row of icons joined by arrows whose thickness follows the energy they carry.
Moving dots on the arrows give the idea of flow: ``phase`` (0..1) shifts them, so the same
function gives every frame of an animation, or a still image for the PDF.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

WIDTH, HEIGHT = 900, 230

THEMES = {
    "dark": dict(bg="#101B30", panel="#18284A", line="#2B3F66", text="#EAF0FA", muted="#9DB0CC",
                 sun="#F5B941", green="#27D79B", blue="#4FA3FF", orange="#FF9F43",
                 grey="#7C8DA8", red="#FF6B6B", flow="#27D79B"),
    "light": dict(bg="#FFFFFF", panel="#EEF3F9", line="#C3CCD9", text="#0F1B2D", muted="#556377",
                  sun="#E8A400", green="#0A7452", blue="#1F5FBF", orange="#D9730D",
                  grey="#6B7A90", red="#C23B3B", flow="#0A7452"),
}


@dataclass(frozen=True)
class Node:
    icon: str            # key of ICONS
    title: str
    value: str           # the big number
    sub: str = ""        # small line under it
    color: str = "green"
    lane: int | None = None   # -1 / 0 / +1: nodes of one column stacked above / at / below the line


@dataclass(frozen=True)
class Flow:
    src: int
    dst: int
    share: float         # 0..1: thickness relative to the largest flow
    color: str = "flow"
    dashed: bool = False


# --- icons: each draws into a 120 x 90 box centred on (0, 0) -------------------------------
def _sun(t, c):
    rays = "".join(
        f'<line x1="{26 * math.cos(a):.1f}" y1="{26 * math.sin(a):.1f}" '
        f'x2="{38 * math.cos(a):.1f}" y2="{38 * math.sin(a):.1f}" stroke="{c}" '
        f'stroke-width="4" stroke-linecap="round"/>'
        for a in (i * math.pi / 4 for i in range(8)))
    return f'<circle r="18" fill="{c}"/>{rays}'


def _panels(t, c):
    cells = []
    for r in range(3):
        for k in range(4):
            x, y = -38 + k * 19, -26 + r * 18
            cells.append(f'<rect x="{x}" y="{y}" width="17" height="16" rx="2" fill="{c}" '
                         f'opacity="{0.55 + 0.15 * ((r + k) % 2):.2f}"/>')
    return "".join(cells) + f'<rect x="-40" y="-28" width="80" height="58" rx="4" fill="none" stroke="{t["line"]}" stroke-width="2"/>'


def _inverter(t, c):
    return (f'<rect x="-30" y="-26" width="60" height="52" rx="8" fill="{t["panel"]}" stroke="{c}" stroke-width="3"/>'
            f'<path d="M-18,4 q6,-14 12,0 t12,0 t12,0" fill="none" stroke="{c}" stroke-width="3.5" stroke-linecap="round"/>'
            f'<line x1="-18" y1="-12" x2="18" y2="-12" stroke="{c}" stroke-width="3" stroke-linecap="round"/>')


def _house(t, c):
    return (f'<path d="M-34,6 L0,-26 L34,6" fill="none" stroke="{c}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<rect x="-24" y="4" width="48" height="30" rx="3" fill="{c}" opacity="0.85"/>'
            f'<rect x="-6" y="16" width="12" height="18" rx="2" fill="{t["panel"]}"/>')


def _grid(t, c):
    return (f'<path d="M0,-34 L-22,34 M0,-34 L22,34 M-16,0 L16,0 M-10,-18 L10,-18 M-19,18 L19,18" '
            f'fill="none" stroke="{c}" stroke-width="4" stroke-linecap="round"/>'
            f'<path d="M-40,-22 Q0,-10 40,-22" fill="none" stroke="{c}" stroke-width="2.5" opacity="0.7"/>')


def _turbine(t, c):
    blades = "".join(
        f'<path d="M0,-8 L-3,-40 L3,-40 Z" fill="{c}" transform="rotate({a} 0 -8)"/>'
        for a in (0, 120, 240))
    return (f'<path d="M-3,-8 L-6,36 L6,36 L3,-8 Z" fill="{t["grey"]}"/>{blades}'
            f'<circle cx="0" cy="-8" r="5" fill="{t["text"]}"/>')


def _wind(t, c):
    """Wind itself: three streaks, the outer two curling away from each other."""
    return (f'<path d="M-40,-14 H14 q16,0 16,-10 q0,-9 -11,-8" fill="none" stroke="{c}" stroke-width="4.5" stroke-linecap="round"/>'
            f'<path d="M-30,2 H34" fill="none" stroke="{c}" stroke-width="4.5" stroke-linecap="round"/>'
            f'<path d="M-40,18 H8 q16,0 16,10 q0,9 -11,8" fill="none" stroke="{c}" stroke-width="4.5" stroke-linecap="round"/>')


def _battery(t, c):
    return (f'<rect x="-34" y="-20" width="62" height="40" rx="7" fill="none" stroke="{c}" stroke-width="4"/>'
            f'<rect x="28" y="-8" width="8" height="16" rx="2" fill="{c}"/>'
            f'<rect x="-28" y="-14" width="14" height="28" rx="3" fill="{c}"/>'
            f'<rect x="-10" y="-14" width="14" height="28" rx="3" fill="{c}"/>'
            f'<rect x="8" y="-14" width="14" height="28" rx="3" fill="{c}" opacity="0.35"/>')


def _tank(t, c):
    return (f'<rect x="-22" y="-32" width="44" height="64" rx="18" fill="{t["panel"]}" stroke="{c}" stroke-width="4"/>'
            f'<text x="0" y="8" text-anchor="middle" font-size="22" font-weight="700" fill="{c}">H2</text>')


def _electrolyser(t, c):
    return (f'<rect x="-34" y="-24" width="68" height="48" rx="6" fill="{t["panel"]}" stroke="{c}" stroke-width="3"/>'
            f'<line x1="0" y1="-24" x2="0" y2="24" stroke="{c}" stroke-width="3" stroke-dasharray="4 4"/>'
            f'<text x="-17" y="6" text-anchor="middle" font-size="16" font-weight="700" fill="{c}">H2</text>'
            f'<text x="17" y="6" text-anchor="middle" font-size="16" font-weight="700" fill="{c}">O2</text>')


def _flame(t, c):
    return (f'<path d="M0,-34 C10,-18 24,-8 18,10 C14,24 -14,24 -18,10 C-22,-2 -6,-8 0,-34 Z" fill="{c}"/>'
            f'<path d="M0,-6 C6,2 10,8 6,16 C2,20 -6,18 -6,12 C-6,6 -2,4 0,-6 Z" fill="{t["bg"]}" opacity="0.7"/>')


def _collector(t, c):
    return (f'<path d="M-38,22 L-22,-24 L38,-24 L22,22 Z" fill="{c}" opacity="0.8"/>'
            f'<path d="M-30,6 L30,6 M-26,-8 L34,-8" stroke="{t["bg"]}" stroke-width="2" opacity="0.6"/>'
            f'<line x1="-30" y1="26" x2="26" y2="26" stroke="{t["grey"]}" stroke-width="4" stroke-linecap="round"/>')


def _tap(t, c):
    return (f'<path d="M-26,-12 h30 a14,14 0 0 1 14,14 v6" fill="none" stroke="{c}" stroke-width="7" stroke-linecap="round"/>'
            f'<circle cx="-26" cy="-12" r="3" fill="{c}"/>'
            f'<path d="M18,22 q-7,10 0,14 q7,-4 0,-14z" fill="{c}"/>')


def _snow(t, c):
    arms = "".join(
        f'<line x1="0" y1="0" x2="{30 * math.cos(a):.1f}" y2="{30 * math.sin(a):.1f}" stroke="{c}" stroke-width="4" stroke-linecap="round"/>'
        for a in (i * math.pi / 3 for i in range(6)))
    return arms + f'<circle r="5" fill="{c}"/>'


def _engine(t, c):
    return (f'<rect x="-30" y="-14" width="60" height="38" rx="6" fill="{t["panel"]}" stroke="{c}" stroke-width="4"/>'
            f'<rect x="-18" y="-26" width="36" height="12" rx="3" fill="{c}"/>'
            f'<path d="M-30,4 h-8 M30,4 h8" stroke="{c}" stroke-width="5" stroke-linecap="round"/>'
            f'<path d="M-14,4 l7,-8 l7,12 l7,-12 l7,8" fill="none" stroke="{c}" stroke-width="3" stroke-linejoin="round"/>')


def _digester(t, c):
    return (f'<path d="M-34,26 V-4 a34,30 0 0 1 68,0 V26 Z" fill="{t["panel"]}" stroke="{c}" stroke-width="4"/>'
            f'<path d="M-34,8 q17,-9 34,0 t34,0" fill="none" stroke="{c}" stroke-width="3" opacity="0.8"/>'
            f'<circle cx="-8" cy="17" r="3" fill="{c}"/><circle cx="8" cy="20" r="2.5" fill="{c}"/>')


def _hot_tank(t, c):
    return (f'<rect x="-24" y="-32" width="48" height="64" rx="16" fill="{t["panel"]}" stroke="{c}" stroke-width="4"/>'
            f'<path d="M-24,-6 q6,-6 12,0 t12,0 t12,0 t12,0" fill="none" stroke="{c}" stroke-width="3"/>'
            f'<path d="M-24,10 q6,-6 12,0 t12,0 t12,0 t12,0" fill="none" stroke="{c}" stroke-width="3"/>')


ICONS = {"hot_tank": _hot_tank, "engine": _engine, "digester": _digester, "sun": _sun, "panels": _panels, "inverter": _inverter, "house": _house, "grid": _grid,
         "turbine": _turbine, "wind": _wind, "battery": _battery, "tank": _tank, "electrolyser": _electrolyser,
         "flame": _flame, "collector": _collector, "tap": _tap, "snow": _snow}


def _columns(nodes: list[Node]) -> list[list[int]]:
    """Group the nodes into columns: a node with a lane other than 0 shares the column of the
    other nodes that have a lane (a fork), every other node has a column of its own."""
    cols: list[list[int]] = []
    for i, node in enumerate(nodes):
        if node.lane is not None and cols and nodes[cols[-1][0]].lane is not None:
            cols[-1].append(i)
        else:
            cols.append([i])
    return cols


def _path_point(points: list[tuple[float, float]], u: float) -> tuple[float, float]:
    lengths = [math.dist(points[k], points[k + 1]) for k in range(len(points) - 1)]
    target = u * sum(lengths)
    for k, length in enumerate(lengths):
        if target <= length or k == len(lengths) - 1:
            f = target / length if length else 0.0
            (x1, y1), (x2, y2) = points[k], points[k + 1]
            return x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
        target -= length
    return points[-1]


def picture_size(nodes: list[Node]) -> tuple[int, int]:
    """Width and height of the picture of ``nodes``."""
    forked = any(node.lane is not None for node in nodes)
    return WIDTH, (250 if forked else HEIGHT)


def flow_svg(nodes: list[Node], flows: list[Flow], phase: float = 0.0, theme: str = "light",
             width: int = WIDTH, height: int | None = None) -> str:
    """The picture as SVG text. ``phase`` in [0, 1) moves the dots along the arrows."""
    t = THEMES[theme]
    cols = _columns(nodes)
    forked = any(node.lane is not None for node in nodes)
    height = height or (250 if forked else HEIGHT)
    cy = 125 if forked else 82
    lane_dy = 78
    n = len(cols)
    pos: dict[int, tuple[float, float, bool]] = {}      # node -> (x, y, label to the right)
    for ci, col in enumerate(cols):
        x = width * (ci + 0.5) / n
        for i in col:
            lane = nodes[i].lane
            fork = lane is not None
            pos[i] = (x - (62 if fork else 0), cy + (lane or 0) * lane_dy, fork)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}" font-family="Poppins, Segoe UI, Arial, sans-serif">',
             f'<rect width="{width}" height="{height}" rx="14" fill="{t["bg"]}"/>']
    top = max((f.share for f in flows), default=1.0) or 1.0
    for f in flows:
        x1, y1, _ = pos[f.src]
        x2, y2, _ = pos[f.dst]
        x1 += 50
        x2 -= 50
        w = 3 + 11 * f.share / top
        col = t[f.color]
        dash = ' stroke-dasharray="7 7"' if f.dashed else ""
        tip = x2 - 8
        if abs(y2 - y1) < 1:
            pts = [(x1, y1), (tip, y2)]
        else:
            mid = x1 + (tip - x1) * 0.45
            pts = [(x1, y1), (mid, y1), (mid, y2), (tip, y2)]
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        parts.append(f'<polyline points="{path}" fill="none" stroke="{col}" stroke-opacity="0.28" '
                     f'stroke-width="{w:.1f}" stroke-linecap="round" stroke-linejoin="round"{dash}/>')
        parts.append(f'<path d="M{tip - 8:.1f},{y2 - 9:.1f} L{tip + 8:.1f},{y2:.1f} '
                     f'L{tip - 8:.1f},{y2 + 9:.1f} Z" fill="{col}"/>')
        length = sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1))
        count = max(2, int(length / 38))
        for k in range(count):
            u = (k / count + phase) % 1.0
            x, y = _path_point(pts, u)
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{max(2.6, w / 2.4):.1f}" '
                         f'fill="{col}" opacity="{0.35 + 0.65 * math.sin(math.pi * u):.2f}"/>')
    for i, node in enumerate(nodes):
        x, y, right = pos[i]
        col = t[node.color]
        parts.append(f'<g transform="translate({x:.1f},{y:.1f})">{ICONS[node.icon](t, col)}</g>')
        if right:
            tx = x + 48
            parts.append(f'<text x="{tx:.1f}" y="{y - 12:.1f}" font-size="12.5" '
                         f'fill="{t["muted"]}">{_esc(node.title)}</text>')
            parts.append(f'<text x="{tx:.1f}" y="{y + 9:.1f}" font-size="19" font-weight="700" '
                         f'fill="{t["text"]}">{_esc(node.value)}</text>')
            if node.sub:
                parts.append(f'<text x="{tx:.1f}" y="{y + 26:.1f}" font-size="11.5" '
                             f'fill="{t["muted"]}">{_esc(node.sub)}</text>')
        else:
            parts.append(f'<text x="{x:.1f}" y="{y + 62:.1f}" text-anchor="middle" '
                         f'font-size="12.5" fill="{t["muted"]}">{_esc(node.title)}</text>')
            parts.append(f'<text x="{x:.1f}" y="{y + 84:.1f}" text-anchor="middle" '
                         f'font-size="19" font-weight="700" fill="{t["text"]}">{_esc(node.value)}</text>')
            if node.sub:
                parts.append(f'<text x="{x:.1f}" y="{y + 101:.1f}" text-anchor="middle" '
                             f'font-size="11.5" fill="{t["muted"]}">{_esc(node.sub)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
