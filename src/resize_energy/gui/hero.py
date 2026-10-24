"""Home-page illustration: a sun over a landscape that grows when you pull it down.

Closed it shows the sun and a green ridge. Pulling the grip at the bottom reveals, in turn, a
wind turbine that rises from the ridge and a solar farm on the plain below. Drawn in code (no
image files). The rotation runs only while the widget is visible.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from resize_energy.gui.theme import COLORS

SUN = "#F5B941"
BLADE_STEP_DEG = 120.0  # three blades: one third of a turn looks identical, so the loop is seamless
MIN_H, MAX_H = 210, 440   # MAX_H: the height the landscape is drawn for
LIMIT_H = 520               # the tallest the picture may ever be
GRIP = 26               # height of the strip at the bottom that can be dragged
RADIUS = 26
PANEL = "#2F5FA8"


def blade_angle(progress: float) -> float:
    """Rotor angle in degrees for an animation progress in [0, 1]."""
    return BLADE_STEP_DEG * progress


def reveal(height: float, start: float, span: float) -> float:
    """0 until ``height`` reaches ``start``, then rising to 1 over ``span`` pixels."""
    return max(0.0, min(1.0, (height - start) / span))


class HeroArt(QWidget):
    """The home-page illustration; its height can be dragged between MIN_H and MAX_H."""

    def __init__(self, width: int = 300, height: int = MIN_H) -> None:
        super().__init__()
        self.setFixedSize(width, height)
        self.setMouseTracking(True)
        self.setToolTip("Drag the bottom edge down to see more of the landscape")
        self._drag: tuple[float, int] | None = None
        self._angle = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(5000)  # one third of a turn per 5 s: calm, not distracting
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._on_value)
        # the first time the home page is shown the landscape unrolls by itself
        self._opening = QVariantAnimation(self)
        self._opening.setStartValue(float(MIN_H))
        self._opening.setEndValue(float(MAX_H))
        self._opening.setDuration(3200)
        self._opening.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._opening.valueChanged.connect(lambda v: self.set_height(float(v)))
        self._opened = False
        self._max = MAX_H                      # how far it can open (set by the page)

    def set_limit(self, pixels: float) -> None:
        """Do not open further than ``pixels`` (the page lines it up with the Compare box)."""
        self._max = round(max(MIN_H + 60, min(LIMIT_H, pixels)))
        if self.height() > self._max or (self._opening.state() == QVariantAnimation.State.Stopped
                                         and self.height() == self._max):
            self.setFixedHeight(self._max)
        self._opening.setEndValue(float(self._max))

    def _open_by_itself(self) -> None:
        if not self._opened and self._drag is None and self.height() == MIN_H:
            self._opening.start()
        self._opened = True

    def stop_opening(self) -> None:
        """Stop the automatic opening (the user took over, or a test wants a fixed size)."""
        self._opening.stop()
        self._opened = True

    # --- size ----------------------------------------------------------------------------
    def set_height(self, height: float) -> None:
        self.setFixedHeight(round(max(MIN_H, min(self._max, height))))

    def _in_grip(self, y: float) -> bool:
        return y >= self.height() - GRIP

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._in_grip(event.position().y()):
            self.stop_opening()
            self._drag = (event.globalPosition().y(), self.height())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag is not None:
            start_y, start_h = self._drag
            self.set_height(start_h + event.globalPosition().y() - start_y)
            event.accept()
            return
        self.setCursor(Qt.CursorShape.SizeVerCursor if self._in_grip(event.position().y())
                       else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self._in_grip(event.position().y()):    # open fully, or close again
            self.stop_opening()
            self.set_height(MIN_H if self.height() > MIN_H else self._max)
            return
        super().mouseDoubleClickEvent(event)

    # --- animation -----------------------------------------------------------------------
    def _on_value(self, value) -> None:
        self._angle = blade_angle(float(value))
        self.update()

    def showEvent(self, event) -> None:
        self._anim.start()
        if not self._opened:
            QTimer.singleShot(700, self._open_by_itself)
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._anim.stop()
        super().hideEvent(event)

    # --- drawing -------------------------------------------------------------------------
    def paintEvent(self, event) -> None:
        w, h = float(self.width()), float(self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        card = QPainterPath()
        card.addRoundedRect(QRectF(0, 0, w, h), RADIUS, RADIUS)
        p.setClipPath(card)
        # sky
        back = QLinearGradient(0, 0, w, h)
        back.setColorAt(0.0, QColor(COLORS["accent_tint"]))
        back.setColorAt(1.0, QColor("#E7EEFB"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(back))
        p.drawRect(QRectF(0, 0, w, h))
        # sun
        p.setBrush(QBrush(QColor(SUN)))
        p.drawEllipse(QPointF(w * 0.74, 59), 27, 27)
        accent = QColor(COLORS["accent"])
        k = self._max / MAX_H                       # the landscape is squeezed to fit the room
        grow = h / k
        p.save()
        p.scale(1.0, k)
        peak = QPointF(w * 0.36, 150)
        # the mountain with the turbine on its ridge
        mountain = QPainterPath()
        mountain.moveTo(0, 190)
        mountain.cubicTo(w * 0.12, 168, w * 0.24, peak.y(), peak.x(), peak.y())
        mountain.cubicTo(w * 0.52, peak.y(), w * 0.68, 205, w, 262)
        mountain.lineTo(w, MAX_H)
        mountain.lineTo(0, MAX_H)
        mountain.closeSubpath()
        p.setBrush(QBrush(accent.lighter(165)))
        p.drawPath(mountain)
        shade = QPainterPath()                       # the side away from the sun
        shade.moveTo(peak)
        shade.cubicTo(w * 0.52, peak.y(), w * 0.68, 205, w, 262)
        shade.lineTo(w, MAX_H)
        shade.lineTo(w * 0.55, MAX_H)
        shade.cubicTo(w * 0.5, 280, w * 0.42, 200, peak.x(), peak.y())
        shade.closeSubpath()
        shade_colour = QColor(accent.lighter(140))
        shade_colour.setAlpha(150)
        p.setBrush(QBrush(shade_colour))
        p.drawPath(shade)
        # foothills and the plain
        foot = QPainterPath()
        foot.moveTo(0, 318)
        foot.cubicTo(w * 0.3, 292, w * 0.6, 336, w, 306)
        foot.lineTo(w, MAX_H)
        foot.lineTo(0, MAX_H)
        foot.closeSubpath()
        p.setBrush(QBrush(accent.lighter(185)))
        p.drawPath(foot)
        self._solar_farm(p, w, reveal(grow, 300, 110))
        p.restore()
        self._turbine(p, QPointF(peak.x(), peak.y() * k), reveal(h, MIN_H, 70))
        self._grip(p, w, h)
        p.end()

    def _turbine(self, p: QPainter, base: QPointF, grow: float) -> None:
        if grow <= 0.0:
            return
        hub = QPointF(base.x(), base.y() - 88 * grow)
        p.setPen(QPen(QColor(COLORS["text"]), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(hub, base)
        blade = 50 * grow
        p.setPen(QPen(QColor(COLORS["accent"]), 4.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for k in range(3):
            a = math.radians(self._angle + 120.0 * k - 90.0)
            p.drawLine(hub, QPointF(hub.x() + blade * math.cos(a), hub.y() + blade * math.sin(a)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(COLORS["text"])))
        p.drawEllipse(hub, 5.5 * grow, 5.5 * grow)

    @staticmethod
    def _solar_farm(p: QPainter, w: float, alpha: float) -> None:
        """Rows of tilted panels on the plain, bigger towards the viewer."""
        if alpha <= 0.0:
            return
        p.save()
        p.setOpacity(alpha)
        for row, (y, scale) in enumerate(((352, 0.8), (385, 1.0), (418, 1.2))):
            pw, ph = 46 * scale, 20 * scale
            count = 4
            gap = 10 * scale
            x = (w - (count * pw + (count - 1) * gap)) / 2 + (row % 2) * 4
            for _ in range(count):
                top = QPolygonF([QPointF(x + 0.12 * pw, y - ph), QPointF(x + pw + 0.12 * pw, y - ph),
                                 QPointF(x + pw, y), QPointF(x, y)])
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(PANEL)))
                p.drawPolygon(top)
                p.setPen(QPen(QColor("#9DB8E6"), 0.8))
                for c in (1, 2, 3):                  # cell lines
                    f = c / 4
                    p.drawLine(QPointF(x + 0.12 * pw + f * pw, y - ph), QPointF(x + f * pw, y))
                p.drawLine(QPointF(x + 0.06 * pw, y - ph / 2), QPointF(x + 1.06 * pw, y - ph / 2))
                p.setPen(QPen(QColor(COLORS["text"]), 1.4))
                p.drawLine(QPointF(x + pw / 2, y), QPointF(x + pw / 2, y + 4 * scale))
                x += pw + gap
        p.restore()

    @staticmethod
    def _grip(p: QPainter, w: float, h: float) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        colour = QColor(COLORS["text"])
        colour.setAlpha(70)
        p.setBrush(QBrush(colour))
        p.drawRoundedRect(QRectF(w / 2 - 17, h - 11, 34, 4.5), 2.2, 2.2)
