"""Home-page illustration: a sun, a slowly turning wind turbine and a soft landscape line.

Drawn in code (no image files). The rotation runs only while the widget is visible.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from resize_energy.gui.theme import COLORS

SUN = "#F5B941"
BLADE_STEP_DEG = 120.0  # three blades: one third of a turn looks identical, so the loop is seamless


def blade_angle(progress: float) -> float:
    """Rotor angle in degrees for an animation progress in [0, 1]."""
    return BLADE_STEP_DEG * progress


class HeroArt(QWidget):
    """Fixed-size illustration for the home page."""

    def __init__(self, width: int = 300, height: int = 210) -> None:
        super().__init__()
        self.setFixedSize(width, height)
        self._angle = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(5000)  # one third of a turn per 5 s: calm, not distracting
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._on_value)

    def _on_value(self, value) -> None:
        self._angle = blade_angle(float(value))
        self.update()

    def showEvent(self, event) -> None:
        self._anim.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._anim.stop()
        super().hideEvent(event)

    def paintEvent(self, event) -> None:
        w, h = float(self.width()), float(self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # soft backdrop
        back = QLinearGradient(0, 0, w, h)
        back.setColorAt(0.0, QColor(COLORS["accent_tint"]))
        back.setColorAt(1.0, QColor("#E7EEFB"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(back))
        p.drawRoundedRect(QRectF(0, 0, w, h), 26, 26)
        # sun
        p.setBrush(QBrush(QColor(SUN)))
        p.drawEllipse(QPointF(w * 0.74, h * 0.28), h * 0.13, h * 0.13)
        # hills
        hills = QPainterPath()
        hills.moveTo(0, h * 0.82)
        hills.cubicTo(w * 0.25, h * 0.68, w * 0.55, h * 0.95, w, h * 0.78)
        hills.lineTo(w, h)
        hills.lineTo(0, h)
        hills.closeSubpath()
        p.setClipPath(self._rounded(w, h))
        p.setBrush(QBrush(QColor(COLORS["accent"]).lighter(165)))
        p.drawPath(hills)
        p.setClipping(False)
        # tower and rotor
        hub = QPointF(w * 0.36, h * 0.38)
        base = QPointF(w * 0.36, h * 0.88)
        p.setPen(QPen(QColor(COLORS["text"]), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(hub, base)
        blade = h * 0.30
        pen = QPen(QColor(COLORS["accent"]), 4.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        for k in range(3):
            a = math.radians(self._angle + 120.0 * k - 90.0)
            p.drawLine(hub, QPointF(hub.x() + blade * math.cos(a), hub.y() + blade * math.sin(a)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(COLORS["text"])))
        p.drawEllipse(hub, 5.5, 5.5)
        p.end()

    @staticmethod
    def _rounded(w: float, h: float) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), 26, 26)
        return path
