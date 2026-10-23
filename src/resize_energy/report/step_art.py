"""Small illustrations for the input steps, drawn as SVG text (Qt-free).

Each picture is 220 x 110 on a transparent background and follows ``phase`` (0..1) with a
slow, calm movement: the sun walks along its path, the rotor turns, the battery fills.
"""

from __future__ import annotations

import math

from resize_energy.report.flow_art import THEMES

W, H = 220, 110


def _t() -> dict[str, str]:
    return THEMES["light"]


def _wrap(body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}" font-family="Poppins, Segoe UI, Arial, sans-serif">{body}</svg>')


def sun_path(phase: float) -> str:
    t = _t()
    a = math.pi * (0.12 + 0.76 * phase)                  # from east to west
    sx, sy = 110 - 80 * math.cos(a), 92 - 70 * math.sin(a)
    rays = "".join(
        f'<line x1="{sx + 11 * math.cos(k * math.pi / 4):.1f}" y1="{sy + 11 * math.sin(k * math.pi / 4):.1f}" '
        f'x2="{sx + 17 * math.cos(k * math.pi / 4):.1f}" y2="{sy + 17 * math.sin(k * math.pi / 4):.1f}" '
        f'stroke="{t["sun"]}" stroke-width="2.5" stroke-linecap="round"/>' for k in range(8))
    return _wrap(
        f'<path d="M30,92 A80,70 0 0 1 190,92" fill="none" stroke="{t["line"]}" stroke-width="2" stroke-dasharray="4 5"/>'
        f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="8.5" fill="{t["sun"]}"/>{rays}'
        f'<line x1="14" y1="92" x2="206" y2="92" stroke="{t["grey"]}" stroke-width="2.5" stroke-linecap="round"/>'
        f'<path d="M88,92 L110,72 L132,92 Z" fill="{t["blue"]}" opacity="0.85"/>'
        f'<rect x="96" y="92" width="28" height="10" fill="{t["panel"]}" stroke="{t["blue"]}" stroke-width="1.5"/>')


_DAY = (0.35, 0.3, 0.28, 0.27, 0.3, 0.45, 0.8, 1.0, 0.75, 0.5, 0.42, 0.45, 0.55, 0.5, 0.45,
        0.45, 0.55, 0.8, 1.15, 1.4, 1.3, 1.0, 0.65, 0.45)


def load_profile(phase: float) -> str:
    t = _t()
    now = int(phase * 24) % 24
    bars = "".join(
        f'<rect x="{12 + k * 8.4:.1f}" y="{98 - 62 * v:.1f}" width="6" height="{62 * v:.1f}" rx="2" '
        f'fill="{t["orange"] if k == now else t["blue"]}" opacity="{1.0 if k == now else 0.55}"/>'
        for k, v in enumerate(_DAY))
    return _wrap(bars + f'<line x1="8" y1="99" x2="212" y2="99" stroke="{t["grey"]}" stroke-width="2" stroke-linecap="round"/>'
                 f'<text x="10" y="12" font-size="10" fill="{t["muted"]}">Your day, hour by hour</text>')


def modules(phase: float) -> str:
    t = _t()
    cells = []
    for k in range(3):
        x = 12 + k * 52
        cells.append(f'<rect x="{x}" y="34" width="42" height="34" rx="3" fill="{t["blue"]}" opacity="0.8"/>'
                     f'<path d="M{x + 14},34 v34 M{x + 28},34 v34 M{x},45 h42 M{x},57 h42" stroke="{t["bg"]}" stroke-width="1.2" opacity="0.7"/>')
    wire = f'<path d="M54,51 h10 M106,51 h10 M158,51 h8" stroke="{t["grey"]}" stroke-width="2.5"/>'
    box = (f'<rect x="168" y="30" width="42" height="42" rx="7" fill="{t["panel"]}" stroke="{t["green"]}" stroke-width="3"/>'
           f'<path d="M176,52 q5,-11 10,0 t10,0 t10,0" fill="none" stroke="{t["green"]}" stroke-width="3" stroke-linecap="round"/>')
    dots = "".join(
        f'<circle cx="{12 + ((phase + k / 6) % 1) * 156:.1f}" cy="51" r="3" fill="{t["sun"]}" opacity="0.9"/>'
        for k in range(6))
    return _wrap("".join(cells) + wire + box + dots +
                 f'<text x="12" y="92" font-size="10" fill="{t["muted"]}">Modules in series make a string</text>')


def coins(phase: float) -> str:
    t = _t()
    stack = "".join(
        f'<ellipse cx="62" cy="{88 - 11 * k}" rx="30" ry="8" fill="{t["sun"]}" stroke="{t["orange"]}" stroke-width="2"/>'
        for k in range(4))
    bounce = 5 * math.sin(2 * math.pi * phase)
    top = (f'<ellipse cx="62" cy="{44 + bounce:.1f}" rx="30" ry="8" fill="{t["sun"]}" stroke="{t["orange"]}" stroke-width="2"/>'
           f'<text x="62" y="{48 + bounce:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="{t["orange"]}">€</text>')
    arrow = (f'<path d="M120,86 L146,60 L162,72 L198,30" fill="none" stroke="{t["green"]}" stroke-width="4" '
             f'stroke-linecap="round" stroke-linejoin="round"/>'
             f'<path d="M186,30 h14 v14" fill="none" stroke="{t["green"]}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    return _wrap(stack + top + arrow)


def wind(phase: float) -> str:
    t = _t()
    angle = 360 * phase
    blades = "".join(
        f'<path d="M0,0 L-4,-34 L4,-34 Z" fill="{t["blue"]}" transform="rotate({angle + a:.1f})"/>'
        for a in (0, 120, 240))
    streaks = "".join(
        f'<path d="M{12 + dx},{y} h{50 - dx}" stroke="{t["muted"]}" stroke-width="2.2" stroke-linecap="round" opacity="0.5"/>'
        for y, dx in ((30, 10), (48, 0), (66, 14)))
    return _wrap(streaks +
                 f'<path d="M132,38 L127,100 L137,100 Z" fill="{t["grey"]}"/>'
                 f'<g transform="translate(132,38)">{blades}<circle r="5" fill="{t["text"]}"/></g>')


def weibull(phase: float) -> str:
    t = _t()
    pts = []
    for k in range(0, 41):
        v = k * 0.6
        pdf = (2.0 / 7.5) * (v / 7.5) ** 1.0 * math.exp(-((v / 7.5) ** 2))
        pts.append((14 + k * 4.8, 98 - 330 * pdf * 1.0))
    area = "M14,98 " + " ".join(f"L{x:.1f},{y:.1f}" for x, y in pts) + " L206,98 Z"
    line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    mx = 14 + (0.15 + 0.7 * (0.5 - 0.5 * math.cos(2 * math.pi * phase))) * 192
    return _wrap(f'<path d="{area}" fill="{t["blue"]}" opacity="0.18"/>'
                 f'<path d="{line}" fill="none" stroke="{t["blue"]}" stroke-width="3" stroke-linejoin="round"/>'
                 f'<line x1="{mx:.1f}" y1="14" x2="{mx:.1f}" y2="98" stroke="{t["orange"]}" stroke-width="2" stroke-dasharray="3 4"/>'
                 f'<line x1="10" y1="98" x2="210" y2="98" stroke="{t["grey"]}" stroke-width="2" stroke-linecap="round"/>'
                 f'<text x="12" y="12" font-size="10" fill="{t["muted"]}">How often each wind speed blows</text>')


def turbine_curve(phase: float) -> str:
    t = _t()
    pts = []
    for k in range(0, 61):
        v = k * 0.5
        if v < 3:
            p = 0.0
        elif v < 12:
            p = (v ** 3 - 27) / (12 ** 3 - 27)
        elif v < 25:
            p = 1.0
        else:
            p = 0.0
        pts.append((14 + k * 3.2, 96 - 70 * p))
    line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    k = int(phase * 50) + 4
    x, y = pts[min(k, 60)]
    return _wrap(f'<path d="{line}" fill="none" stroke="{t["green"]}" stroke-width="3" stroke-linejoin="round"/>'
                 f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{t["orange"]}"/>'
                 f'<line x1="10" y1="97" x2="210" y2="97" stroke="{t["grey"]}" stroke-width="2" stroke-linecap="round"/>'
                 f'<text x="12" y="12" font-size="10" fill="{t["muted"]}">Power of the turbine at each speed</text>')


def battery(phase: float) -> str:
    t = _t()
    level = 0.5 + 0.45 * math.sin(2 * math.pi * phase)
    bars = "".join(
        f'<rect x="{34 + k * 33}" y="34" width="27" height="42" rx="4" fill="{t["green"]}" '
        f'opacity="{1.0 if level > (k + 0.5) / 4 else 0.18}"/>' for k in range(4))
    bolt = f'<path d="M104,8 L92,24 h10 L98,38 L114,20 h-10 Z" fill="{t["sun"]}"/>' if math.cos(2 * math.pi * phase) > 0 else ""
    return _wrap(f'<rect x="26" y="28" width="150" height="54" rx="9" fill="none" stroke="{t["green"]}" stroke-width="4"/>'
                 f'<rect x="176" y="43" width="10" height="24" rx="3" fill="{t["green"]}"/>{bars}{bolt}'
                 f'<text x="26" y="102" font-size="10" fill="{t["muted"]}">Stores the surplus</text>')


def electrolyser(phase: float) -> str:
    t = _t()
    bubbles = []
    for k in range(5):
        u = (phase + k / 5) % 1.0
        for side, col in ((-1, t["blue"]), (1, t["orange"])):
            x = 110 + side * (26 + 8 * math.sin(k * 2.1))
            bubbles.append(f'<circle cx="{x:.1f}" cy="{80 - 56 * u:.1f}" r="{2.5 + (k % 3)}" fill="{col}" opacity="{0.9 - 0.7 * u:.2f}"/>')
    return _wrap(f'<rect x="56" y="22" width="108" height="64" rx="8" fill="{t["panel"]}" stroke="{t["blue"]}" stroke-width="3.5"/>'
                 f'<line x1="110" y1="22" x2="110" y2="86" stroke="{t["blue"]}" stroke-width="3" stroke-dasharray="5 4"/>'
                 f'<text x="84" y="100" text-anchor="middle" font-size="13" font-weight="700" fill="{t["blue"]}">H2</text>'
                 f'<text x="136" y="100" text-anchor="middle" font-size="13" font-weight="700" fill="{t["orange"]}">O2</text>'
                 + "".join(bubbles))


def flame(phase: float) -> str:
    t = _t()
    s = 1.0 + 0.06 * math.sin(2 * math.pi * phase * 3)
    return _wrap(f'<g transform="translate(110,60) scale({s:.3f},{1.0 + 0.5 * (s - 1):.3f}) translate(-110,-60)">'
                 f'<path d="M110,10 C128,38 150,52 140,80 C132,100 88,100 80,80 C72,58 98,44 110,10 Z" fill="{t["red"]}"/>'
                 f'<path d="M110,52 C120,66 128,76 120,90 C114,98 100,96 100,86 C100,74 106,70 110,52 Z" fill="{t["sun"]}"/></g>'
                 f'<line x1="60" y1="102" x2="160" y2="102" stroke="{t["grey"]}" stroke-width="3" stroke-linecap="round"/>')


def collector(phase: float) -> str:
    t = _t()
    drops = "".join(
        f'<circle cx="{150 + 0 * k}" cy="{30 + ((phase + k / 3) % 1) * 56:.1f}" r="3.2" fill="{t["blue"]}" opacity="0.8"/>'
        for k in range(3))
    rays = "".join(
        f'<line x1="{26 + 16 * k}" y1="{8 + 2 * k}" x2="{40 + 16 * k}" y2="{32 + 2 * k}" stroke="{t["sun"]}" stroke-width="3" '
        f'stroke-linecap="round" opacity="{0.35 + 0.65 * ((phase * 4 + k) % 1):.2f}"/>' for k in range(5))
    return _wrap(rays +
                 f'<path d="M24,86 L52,46 L132,46 L104,86 Z" fill="{t["blue"]}" opacity="0.85"/>'
                 f'<path d="M36,70 h80 M44,58 h80" stroke="{t["bg"]}" stroke-width="1.5" opacity="0.6"/>'
                 f'<path d="M132,56 h18 v36" fill="none" stroke="{t["red"]}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
                 f'<rect x="146" y="26" width="8" height="2" fill="none"/>{drops}')


def tap(phase: float) -> str:
    t = _t()
    flow = 40 * (phase % 1.0)
    return _wrap(f'<path d="M60,34 h56 a22,22 0 0 1 22,22 v6" fill="none" stroke="{t["red"]}" stroke-width="9" stroke-linecap="round"/>'
                 f'<rect x="54" y="26" width="14" height="16" rx="3" fill="{t["red"]}"/>'
                 f'<path d="M138,70 q-9,12 0,18 q9,-6 0,-18z" fill="{t["blue"]}" opacity="{1 - flow / 80:.2f}" transform="translate(0,{flow / 3:.1f})"/>'
                 f'<text x="60" y="104" font-size="10" fill="{t["muted"]}">Hot water from the sun</text>')


def target(phase: float) -> str:
    t = _t()
    r = 4 * math.sin(2 * math.pi * phase)
    return _wrap(f'<circle cx="110" cy="56" r="44" fill="none" stroke="{t["blue"]}" stroke-width="5" opacity="0.4"/>'
                 f'<circle cx="110" cy="56" r="28" fill="none" stroke="{t["blue"]}" stroke-width="5" opacity="0.7"/>'
                 f'<circle cx="110" cy="56" r="{11 + r:.1f}" fill="{t["orange"]}"/>'
                 f'<path d="M110,56 L168,14" stroke="{t["text"]}" stroke-width="3" stroke-linecap="round"/>'
                 f'<path d="M160,12 l12,-4 l-4,12 Z" fill="{t["text"]}"/>')


def leaf(phase: float) -> str:
    t = _t()
    sway = 3 * math.sin(2 * math.pi * phase)
    return _wrap(f'<g transform="rotate({sway:.2f} 110 100)">'
                 f'<path d="M110,100 C60,86 64,34 118,16 C150,40 148,86 110,100 Z" fill="{t["green"]}" opacity="0.9"/>'
                 f'<path d="M110,100 C112,72 116,50 118,16" fill="none" stroke="{t["bg"]}" stroke-width="2.5"/></g>'
                 f'<text x="150" y="86" font-size="14" font-weight="700" fill="{t["muted"]}">CO2</text>')


ARTS = {"sun_path": sun_path, "load_profile": load_profile, "modules": modules, "coins": coins,
        "wind": wind, "weibull": weibull, "turbine_curve": turbine_curve, "battery": battery,
        "electrolyser": electrolyser, "flame": flame, "collector": collector, "tap": tap,
        "target": target, "leaf": leaf}


def step_svg(key: str, phase: float = 0.0) -> str:
    return ARTS[key](phase % 1.0)
