"""SVG pictures of a wind farm: the layout map and the wind rose (Qt-free, easy to test).

Both are drawn to scale as SVG text; the app renders them with QtSvg like the energy-flow
picture, so the results page and the PDF show the same image.
"""

from __future__ import annotations

import base64
import math
from collections.abc import Sequence
from xml.sax.saxutils import escape

INK, MUTED, GRID = "#0F1B2D", "#556377", "#E3E8EF"
BLUE, GREEN, RED, AMBER = "#1F5FBF", "#0A7452", "#B3261E", "#C77700"
FONT = 'font-family="Poppins, Segoe UI, Arial, sans-serif"'


def _text(x: float, y: float, s: str, size: float = 11, color: str = MUTED, anchor: str = "start",
          weight: str = "400") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}" {FONT}>{escape(s)}</text>')


def _halo(x: float, y: float, s: str, size: float, anchor: str = "start") -> str:
    """White text with a dark outline, readable on a satellite picture (two layers: the
    outline first, then the fill, because QtSvg ignores paint-order)."""
    back = _text(x, y, s, size, "#000000", anchor, "700").replace(
        "<text ", '<text stroke="#000000" stroke-width="2.6" stroke-linejoin="round" ', 1)
    return back + _text(x, y, s, size, "#FFFFFF", anchor, "700")


def _svg(width: int, height: int, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}"><rect width="{width}" height="{height}" fill="white"/>'
            f'{body}</svg>')


def efficiency_color(eff: float) -> str:
    """Green for a turbine that keeps its energy, through amber to red for a shaded one."""
    u = min(1.0, max(0.0, (eff - 0.85) / 0.13))          # 0.85 -> red, 0.98 -> green
    lo, hi = (0xB3, 0x26, 0x1E), (0x0A, 0x74, 0x52)
    mid = (0xC7, 0x77, 0x00)
    a, b, t = (lo, mid, u * 2) if u < 0.5 else (mid, hi, u * 2 - 1)
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b, strict=True))


def _scale_bar_m(span_m: float) -> float:
    """A round length of about a fifth of the map width."""
    raw = span_m / 5.0
    mag = 10 ** math.floor(math.log10(raw))
    return next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)


def _frame(positions: Sequence[tuple[float, float]], rotor_d: float,
           outline: Sequence[tuple[float, float]] | None, wind_from_deg: float,
           width: int, height: int):
    """Scale and offsets that fit the farm in the picture, and the window it then shows."""
    pts = list(positions)
    area = list(outline) if outline else []
    wake_len = 10.0 * rotor_d
    th = math.radians(wind_from_deg)
    dx, dy = -math.sin(th), -math.cos(th)
    tail = [(x + dx * wake_len * 0.6, y + dy * wake_len * 0.6) for x, y in pts]
    xs = [p[0] for p in [*area, *pts, *tail]]
    ys = [p[1] for p in [*area, *pts, *tail]]
    pad = 2.0 * rotor_d
    x_lo, x_hi, y_lo, y_hi = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    top, bottom, left, right = 34.0, height - 52.0, 14.0, width - 14.0
    k = min((right - left) / (x_hi - x_lo), (bottom - top) / (y_hi - y_lo))
    ox = left + ((right - left) - (x_hi - x_lo) * k) / 2.0 - x_lo * k
    oy = bottom - ((bottom - top) - (y_hi - y_lo) * k) / 2.0 + y_lo * k
    window = ((left - ox) / k, (right - ox) / k, (oy - bottom) / k, (oy - top) / k)
    return k, ox, oy, (top, bottom, left, right), window


def layout_window(positions: Sequence[tuple[float, float]], rotor_d: float,
                  outline: Sequence[tuple[float, float]] | None, wind_from_deg: float,
                  width: int = 460, height: int = 390) -> tuple[float, float, float, float]:
    """The part of the ground (east_lo, east_hi, north_lo, north_hi, metres from the site
    centre) that the map shows: the area a satellite picture has to cover."""
    if not positions and not outline:
        return (-100.0, 100.0, -100.0, 100.0)
    return _frame(positions, rotor_d, outline, wind_from_deg, width, height)[4]


def layout_svg(title: str, positions: Sequence[tuple[float, float]], rotor_d: float,
               efficiencies: Sequence[float], outline: Sequence[tuple[float, float]] | None,
               wind_from_deg: float, decay: float, width: int = 460, height: int = 390,
               satellite=None, exclusions: Sequence[Sequence[tuple[float, float]]] = ()) -> str:
    """Top view of the farm: site outline, rotors to scale, wake cones of the prevailing wind,
    each turbine coloured by the share of a free turbine's energy it keeps. North is up.
    ``satellite`` (a core.satellite.Satellite) puts the aerial picture under everything."""
    pts = list(positions)
    area = list(outline) if outline else []
    r0 = rotor_d / 2.0
    wake_len = 10.0 * rotor_d
    if not pts and not area:
        return _svg(width, height, _text(width / 2, height / 2, "No layout", anchor="middle"))
    th = math.radians(wind_from_deg)
    dx, dy = -math.sin(th), -math.cos(th)
    k, ox, oy, (top, bottom, left, right), _window = _frame(
        pts, rotor_d, area, wind_from_deg, width, height)

    def px(e: float, n: float) -> tuple[float, float]:
        return ox + e * k, oy - n * k

    aerial = satellite is not None and satellite.ok
    line = "#FFFFFF" if aerial else MUTED
    body = []
    body.append(f'<defs><clipPath id="mapclip"><rect x="{left}" y="{top}" '
                f'width="{right - left}" height="{bottom - top}"/></clipPath></defs>')
    if aerial:
        body.append('<g clip-path="url(#mapclip)">')
        for tile in satellite.tiles:
            x, y = px(tile.west_m, tile.north_m)
            b64 = base64.b64encode(tile.data).decode("ascii")
            mime = "image/png" if tile.data[:4] == b"\x89PNG" else "image/jpeg"
            size = tile.size_m * k + 0.6                      # a hair of overlap: no seams
            body.append(f'<image x="{x:.2f}" y="{y:.2f}" width="{size:.2f}" height="{size:.2f}" '
                        f'xlink:href="data:{mime};base64,{b64}"/>')
        body.append('</g>'
                    f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" '
                    f'fill="none" stroke="{GRID}"/>')
    if area:
        poly = " ".join(f"{px(e, n)[0]:.1f},{px(e, n)[1]:.1f}" for e, n in area)
        fill = "none" if aerial else "#F3F8F5"
        body.append(f'<polygon points="{poly}" fill="{fill}" stroke="{line}" stroke-width="1.6" '
                    f'stroke-dasharray="6 4"/>')
    if exclusions:
        for ring in exclusions:
            poly = " ".join(f"{px(e, n)[0]:.1f},{px(e, n)[1]:.1f}" for e, n in ring)
            body.append(f'<polygon points="{poly}" fill="{RED}" fill-opacity="0.30" '
                        f'stroke="{RED}" stroke-width="1.4"/>')
    # wake cones of the prevailing wind, behind the rotors
    cross = (math.cos(th), -math.sin(th))
    body.append('<g clip-path="url(#mapclip)">')
    for e, n in pts:
        half_far = r0 + decay * wake_len
        a = px(e + cross[0] * r0, n + cross[1] * r0)
        b = px(e - cross[0] * r0, n - cross[1] * r0)
        c = px(e + dx * wake_len - cross[0] * half_far, n + dy * wake_len - cross[1] * half_far)
        d = px(e + dx * wake_len + cross[0] * half_far, n + dy * wake_len + cross[1] * half_far)
        body.append(f'<polygon points="{a[0]:.1f},{a[1]:.1f} {d[0]:.1f},{d[1]:.1f} '
                    f'{c[0]:.1f},{c[1]:.1f} {b[0]:.1f},{b[1]:.1f}" fill="{BLUE}" opacity="{0.35 if aerial else 0.10}"/>')
    body.append('</g>')
    # QtSvg does not always honour clip-path: mask whatever the picture or the cones draw
    # outside the map with opaque white, then write the title and the legend on it
    for x, y, w, h in ((0, 0, width, top), (0, bottom, width, height - bottom),
                       (0, top, left, bottom - top), (right, top, width - right, bottom - top)):
        body.append(f'<rect x="{x}" y="{y:.1f}" width="{w}" height="{h:.1f}" fill="white"/>')
    body.append(_text(12, 20, title, 14, INK, weight="700"))
    if aerial:
        body.append(f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" '
                    f'fill="none" stroke="{GRID}"/>')
    show_numbers = len(pts) <= 14
    for i, ((e, n), eff) in enumerate(zip(pts, efficiencies, strict=True)):
        x, y = px(e, n)
        col = efficiency_color(eff)
        rr = max(4.0, r0 * k)
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="{col}" fill-opacity="{0.55 if aerial else 0.25}" '
                    f'stroke="{col}" stroke-width="1.8"/>'
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="{col}"/>')
        if show_numbers:
            label = f"{i + 1}  {eff:.0%}"
            if aerial:      # white halo so the figures can be read on any picture
                body.append(_halo(x, y + rr + 11, label, 9.5, "middle"))
            else:
                body.append(_text(x, y + rr + 11, label, 9.5, INK, "middle"))
    if aerial:
        body.append(_halo(right - 3, bottom - 4, satellite.attribution, 7.5, "end"))
        body.append(f'<circle cx="{width - 30}" cy="{top + 22}" r="21" fill="#FFFFFF" '
                    'fill-opacity="0.8"/>')
    # north arrow, scale bar, wind arrow, colour key
    body.append(f'<path d="M{width - 30},{top + 26} V{top + 4} M{width - 30},{top + 2} l-4,8 h8 z" '
                f'stroke="{INK}" stroke-width="1.6" fill="{INK}"/>'
                + _text(width - 30, top + 40, "N", 10, INK, "middle", "700"))
    span = (right - left) / k
    bar_m = _scale_bar_m(span)
    bx, by = left + 4, bottom + 14
    body.append(f'<path d="M{bx:.1f},{by - 4} v8 M{bx:.1f},{by} h{bar_m * k:.1f} '
                f'm0,-4 v8" stroke="{INK}" stroke-width="1.6" fill="none"/>'
                + _text(bx + bar_m * k + 8, by + 4, f"{bar_m:,.0f} m", 10, MUTED))
    if exclusions:
        body.append(f'<rect x="200" y="{by - 6}" width="12" height="12" fill="{RED}" '
                    f'fill-opacity="0.35" stroke="{RED}"/>' + _text(217, by + 4, "excluded", 10, MUTED))
    wx, wy = width - 135, by
    ax, ay = dx * 22, -dy * 22                                  # screen: y points down
    body.append(f'<path d="M{wx - ax / 2:.1f},{wy - ay / 2:.1f} L{wx + ax / 2:.1f},{wy + ay / 2:.1f}" '
                f'stroke="{BLUE}" stroke-width="2.4" marker-end="none"/>'
                f'<circle cx="{wx + ax / 2:.1f}" cy="{wy + ay / 2:.1f}" r="3.4" fill="{BLUE}"/>'
                + _text(wx + 30, wy + 4, f"wind from {wind_from_deg:.0f} deg", 10, MUTED))
    ky = height - 14
    for j, (eff, label) in enumerate(((0.98, "keeps its energy"), (0.92, "some shading"),
                                      (0.85, "shaded"))):
        kx = left + 4 + j * 135
        body.append(f'<circle cx="{kx}" cy="{ky - 3}" r="5" fill="{efficiency_color(eff)}"/>'
                    + _text(kx + 10, ky, label, 10, MUTED))
    return _svg(width, height, "".join(body))


def rose_svg(title: str, frequency: Sequence[float], energy_share: Sequence[float],
             loss: Sequence[float] | None = None, width: int = 460, height: int = 360) -> str:
    """A wind rose: petal length = share of the hours (blue), amber outline = share of the
    wind energy, red figure = wake loss when the wind comes from that sector."""
    n = len(frequency)
    cx, cy = width / 2, 188.0
    big = 112.0
    top = max(max(frequency), max(energy_share), 1e-9)
    ring_max = math.ceil(top * 100 / 5.0) * 5.0 / 100.0          # to the next 5 %
    body = [_text(12, 20, title, 14, INK, weight="700")]
    for r in (0.25, 0.5, 0.75, 1.0):
        body.append(f'<circle cx="{cx}" cy="{cy}" r="{big * r:.1f}" fill="none" stroke="{GRID}"/>')
        if r in (0.5, 1.0):
            body.append(_text(cx + 4, cy - big * r + 11, f"{ring_max * r:.0%}", 9, MUTED))

    def petal(i: int, value: float, **style: str) -> str:
        half = math.radians(360.0 / n / 2 * 0.86)
        mid = math.radians(i * 360.0 / n)
        r = big * min(value / ring_max, 1.0)
        pts = [(cx, cy)]
        for a in (mid - half, mid - half / 2, mid, mid + half / 2, mid + half):
            pts.append((cx + r * math.sin(a), cy - r * math.cos(a)))
        text = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        extra = " ".join(f'{k}="{v}"' for k, v in style.items())
        return f'<polygon points="{text}" {extra}/>'

    for i, f in enumerate(frequency):
        body.append(petal(i, f, fill=BLUE, **{"fill-opacity": "0.55"}, stroke=BLUE))
    for i, e in enumerate(energy_share):
        body.append(petal(i, e, fill="none", stroke=AMBER, **{"stroke-width": "1.8"}))
    for label, ang in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
        a = math.radians(ang)
        body.append(_text(cx + (big + 14) * math.sin(a), cy - (big + 14) * math.cos(a) + 4,
                          label, 12, INK, "middle", "700"))
    if loss is not None:
        for i, ls in enumerate(loss):
            if ls >= 0.005:
                a = math.radians(i * 360.0 / n)
                r = big + 30
                body.append(_text(cx + r * math.sin(a), cy - r * math.cos(a) + 3,
                                  f"-{ls:.0%}", 9.5, RED, "middle", "700"))
    ly = height - 16
    body.append(f'<rect x="14" y="{ly - 9}" width="12" height="10" fill="{BLUE}" fill-opacity="0.55" '
                f'stroke="{BLUE}"/>' + _text(31, ly, "share of the hours", 10, MUTED)
                + f'<rect x="150" y="{ly - 9}" width="12" height="10" fill="none" stroke="{AMBER}" '
                f'stroke-width="1.8"/>' + _text(167, ly, "share of the energy", 10, MUTED)
                + (_text(290, ly, "-x%: wake loss from there", 10, RED) if loss is not None else ""))
    return _svg(width, height, "".join(body))
