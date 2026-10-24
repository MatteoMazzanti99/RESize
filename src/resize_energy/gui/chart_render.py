"""Draws a :class:`~resize_energy.report.charts.ChartSpec` into an image with QPainter.

The same images are shown in the results window and written into the PDF report.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QImage,
    QPainter,
    QPen,
    QPolygonF,
)

from resize_energy.report.charts import ChartSpec, nice_ticks

INK, MUTED, GRID, AXIS = "#0F1B2D", "#556377", "#E3E8EF", "#9AA7B8"


def _num(value: float, decimals: int) -> str:
    if not math.isfinite(value):
        return "never"
    return f"{value:,.{decimals}f}"


def _tick_decimals(ticks: list[float], decimals: int) -> int:
    step = abs(ticks[1] - ticks[0]) if len(ticks) > 1 else 1.0
    need = 0 if step >= 1 else 1 if step >= 0.1 else 2 if step >= 0.01 else 3
    return max(decimals if step < 1 else 0, need)


class _Canvas:
    def __init__(self, spec: ChartSpec, scale: float) -> None:
        self.spec = spec
        self.image = QImage(int(spec.width * scale), int(spec.height * scale),
                            QImage.Format.Format_ARGB32_Premultiplied)
        self.image.fill(QColor("white"))
        self.p = QPainter(self.image)
        self.p.scale(scale, scale)
        self.p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.base = QFont()
        self.base.setPointSizeF(9)
        self.small = QFont(self.base)
        self.small.setPointSizeF(8)
        self.bold = QFont(self.base)
        self.bold.setPointSizeF(11)
        self.bold.setBold(True)

    def text(self, x: float, y: float, s: str, align: str = "l", font: QFont | None = None,
             color: str = MUTED, w: float = 300.0) -> None:
        """Draw ``s`` with its baseline-centre at (x, y); align l(eft) c(entre) r(ight)."""
        font = font or self.base
        self.p.setFont(font)
        self.p.setPen(QColor(color))
        h = QFontMetricsF(font).height()
        flags = {"l": Qt.AlignmentFlag.AlignLeft, "c": Qt.AlignmentFlag.AlignHCenter,
                 "r": Qt.AlignmentFlag.AlignRight}[align] | Qt.AlignmentFlag.AlignVCenter
        left = x if align == "l" else x - w / 2 if align == "c" else x - w
        self.p.drawText(QRectF(left, y - h / 2, w, h), flags, s)

    def width_of(self, s: str, font: QFont | None = None) -> float:
        return QFontMetricsF(font or self.base).horizontalAdvance(s)

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str, width: float = 1.0,
             dash: bool = False) -> None:
        pen = QPen(QColor(color), width)
        if dash:
            pen.setStyle(Qt.PenStyle.DashLine)
        self.p.setPen(pen)
        self.p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def rect(self, x: float, y: float, w: float, h: float, color: str, alpha: int = 255) -> None:
        c = QColor(color)
        c.setAlpha(alpha)
        self.p.setPen(Qt.PenStyle.NoPen)
        self.p.setBrush(c)
        self.p.drawRoundedRect(QRectF(x, y, max(w, 0.5), max(h, 0.5)), 2.0, 2.0)

    def legend(self, y: float, x0: float) -> None:
        x = x0
        for s in self.spec.series:
            self.rect(x, y - 5, 10, 10, s.color)
            self.text(x + 15, y, s.name, "l")
            x += 15 + self.width_of(s.name) + 18

    def done(self) -> QImage:
        self.p.setPen(QPen(QColor("#D5DEE9"), 1.0))
        self.p.setBrush(Qt.BrushStyle.NoBrush)
        self.p.drawRoundedRect(QRectF(0.5, 0.5, self.spec.width - 1, self.spec.height - 1), 8, 8)
        self.p.end()
        return self.image


def _title(c: _Canvas, spec: ChartSpec) -> float:
    c.text(12, 18, spec.title, "l", c.bold, INK, w=spec.width - 24)
    top = 38.0
    if len(spec.series) > 1:
        c.legend(top + 4, 12)
        top += 20
    return top


def _value_range(values: list[float], extra: list[float], decimals: int):
    finite = [v for v in values + extra if math.isfinite(v)]
    lo = min([0.0, *finite])
    hi = max([0.0, *finite]) if finite else 1.0
    ticks = nice_ticks(lo, hi)
    return ticks, ticks[0], ticks[-1], _tick_decimals(ticks, decimals)


def _refs(c: _Canvas, vlines, to_x, top: float, bottom: float) -> None:
    levels = 0
    for value, label in vlines:
        x = to_x(value)
        c.line(x, top, x, bottom, "#C77700", 1.2, dash=True)
        c.text(x, top - 7 - 11 * (levels % 2), label, "c", c.small, "#8F5600", w=110)
        levels += 1


def _hbars(c: _Canvas, spec: ChartSpec) -> None:
    top = _title(c, spec) + 14
    series = spec.series[0]
    label_w = min(200.0, max(c.width_of(t) for t in spec.categories) + 6)
    left, right, bottom = 16 + label_w, spec.width - 64.0, spec.height - 36.0
    ticks, lo, hi, tdec = _value_range(list(series.values), [v for v, _ in spec.vlines],
                                       spec.decimals)

    def to_x(v: float) -> float:
        return left + (v - lo) / (hi - lo) * (right - left)

    for t in ticks:
        c.line(to_x(t), top, to_x(t), bottom, GRID)
        c.text(to_x(t), bottom + 10, _num(t, tdec), "c", c.small, w=70)
    c.text((left + right) / 2, spec.height - 9, spec.x_label, "c", c.base, MUTED, w=400)
    row = (bottom - top) / len(spec.categories)
    zero = to_x(0.0)
    for i, (name, value) in enumerate(zip(spec.categories, series.values, strict=True)):
        cy = top + row * (i + 0.5)
        color = series.colors[i] if series.colors else series.color
        c.text(left - 8, cy, name, "r", c.base, INK, w=label_w)
        if math.isfinite(value):
            x = to_x(value)
            c.rect(min(zero, x), cy - row * 0.3, abs(x - zero), row * 0.6, color)
            c.text(max(x, zero) + 5, cy, _num(value, spec.decimals), "l", c.base, INK, w=80)
        else:
            c.rect(zero, cy - row * 0.3, right - zero, row * 0.6, "#EEF1F5")
            c.text((zero + right) / 2, cy, "never", "c", c.base, MUTED, w=100)
    c.line(zero, top, zero, bottom, AXIS)
    _refs(c, spec.vlines, to_x, top, bottom)


def _bars(c: _Canvas, spec: ChartSpec, stacked: bool) -> None:
    top = _title(c, spec) + (16 if spec.vlines else 8)
    left, right, bottom = 62.0, spec.width - 14.0, spec.height - 44.0
    n = len(spec.categories)
    if stacked:
        totals = [sum(max(0.0, s.values[i]) for s in spec.series) for i in range(n)]
        values = totals
    else:
        values = [v for s in spec.series for v in s.values]
    ticks, lo, hi, tdec = _value_range(values, [], spec.decimals)

    def to_y(v: float) -> float:
        return bottom - (v - lo) / (hi - lo) * (bottom - top)

    for t in ticks:
        c.line(left, to_y(t), right, to_y(t), GRID)
        c.text(left - 6, to_y(t), _num(t, tdec), "r", c.small, w=56)
    group = (right - left) / n
    k = 1 if stacked else len(spec.series)
    bar_w = group * 0.72 / k
    step = max(1, math.ceil(n / max(1.0, (right - left) / 26.0)))
    for i, name in enumerate(spec.categories):
        x0 = left + group * i + group * 0.14
        base = 0.0
        for j, s in enumerate(spec.series):
            v = max(0.0, s.values[i]) if stacked else s.values[i]
            if stacked:
                y1, y2 = to_y(base + v), to_y(base)
                x = x0
                base += v
            else:
                y1, y2 = to_y(max(v, 0.0)), to_y(min(v, 0.0))
                x = x0 + bar_w * j
            c.rect(x, y1, bar_w, y2 - y1, s.colors[i] if s.colors else s.color)
        if not stacked and n <= 10 and k == 1:
            v = spec.series[0].values[i]
            c.text(x0 + bar_w / 2, to_y(max(v, 0.0)) - 7, _num(v, spec.decimals), "c",
                   c.small, INK, w=70)
        if i % step == 0:
            c.text(left + group * (i + 0.5), bottom + 11, name, "c", c.small, w=group * step)
    c.line(left, to_y(0.0), right, to_y(0.0), AXIS)
    c.text((left + right) / 2, spec.height - 9, spec.x_label, "c", c.base, MUTED, w=420)
    if spec.y_label:
        c.p.save()
        c.p.translate(12, (top + bottom) / 2)
        c.p.rotate(-90)
        c.text(0, 0, spec.y_label, "c", c.small, MUTED, w=220)
        c.p.restore()


def _lines(c: _Canvas, spec: ChartSpec) -> None:
    top = _title(c, spec) + (16 if spec.vlines else 8)
    left, right, bottom = 62.0, spec.width - 18.0, spec.height - 44.0
    xs_all = [x for s in spec.series for x in (s.x or tuple(range(len(s.values))))]
    x_ticks = nice_ticks(min(xs_all), max(xs_all), 6)
    x_lo, x_hi = x_ticks[0], x_ticks[-1]
    ys_all = [v for s in spec.series for v in s.values]
    y_ticks, y_lo, y_hi, ydec = _value_range(ys_all, [v for v, _ in spec.hlines], spec.decimals)
    xdec = _tick_decimals(x_ticks, 0)

    def to_x(v: float) -> float:
        return left + (v - x_lo) / (x_hi - x_lo) * (right - left)

    def to_y(v: float) -> float:
        return bottom - (v - y_lo) / (y_hi - y_lo) * (bottom - top)

    for t in y_ticks:
        c.line(left, to_y(t), right, to_y(t), GRID)
        c.text(left - 6, to_y(t), _num(t, ydec), "r", c.small, w=56)
    for t in x_ticks:
        c.text(to_x(t), bottom + 11, _num(t, xdec), "c", c.small, w=60)
    for s in spec.series:
        xs = s.x or tuple(float(i) for i in range(len(s.values)))
        pts = [QPointF(to_x(x), to_y(v)) for x, v in zip(xs, s.values, strict=True)]
        if s.fill:
            poly = QPolygonF([QPointF(pts[0].x(), to_y(0.0)), *pts, QPointF(pts[-1].x(), to_y(0.0))])
            fill = QColor(s.color)
            fill.setAlpha(55)
            c.p.setPen(Qt.PenStyle.NoPen)
            c.p.setBrush(fill)
            c.p.drawPolygon(poly)
        c.p.setPen(QPen(QColor(s.color), 2.2))
        c.p.setBrush(Qt.BrushStyle.NoBrush)
        c.p.drawPolyline(QPolygonF(pts))
    for value, label in spec.hlines:
        y = to_y(value)
        c.line(left, y, right, y, "#C77700" if value else AXIS, 1.2, dash=bool(value))
        c.text(right - 4, y - 8, label, "r", c.small, "#8F5600" if value else MUTED, w=160)
    c.line(left, bottom, right, bottom, AXIS)
    _refs(c, spec.vlines, to_x, top, bottom)
    c.text((left + right) / 2, spec.height - 9, spec.x_label, "c", c.base, MUTED, w=420)
    if spec.y_label:
        c.p.save()
        c.p.translate(12, (top + bottom) / 2)
        c.p.rotate(-90)
        c.text(0, 0, spec.y_label, "c", c.small, MUTED, w=240)
        c.p.restore()


def render_chart(spec: ChartSpec, scale: float = 2.0) -> QImage:
    """Draw the chart at ``scale`` times its nominal size (sharper in the PDF)."""
    canvas = _Canvas(spec, scale)
    if spec.kind == "hbars":
        _hbars(canvas, spec)
    elif spec.kind == "bars":
        _bars(canvas, spec, stacked=False)
    elif spec.kind == "stack":
        _bars(canvas, spec, stacked=True)
    elif spec.kind == "lines":
        _lines(canvas, spec)
    else:
        raise ValueError(f"unknown chart kind {spec.kind!r}")
    return canvas.done()
