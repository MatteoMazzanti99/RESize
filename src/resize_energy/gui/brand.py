"""RESize logo: the letter R inside a three-colour ring (all renewables), drawn in code."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPen, QPixmap, QTextOption
from PySide6.QtWidgets import QWidget

from resize_energy.gui.theme import COLORS


def draw_logo(painter: QPainter, size: float) -> None:
    """Paint the logo in a square of ``size`` pixels at the origin.

    A letter R inside a ring of three arcs: sun (yellow), wind (blue) and the green of
    the brand, one per family of renewable sources.
    """
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(Qt.PenStyle.NoPen))
    painter.setBrush(QBrush(QColor(COLORS["sidebar"])))
    painter.drawEllipse(QRectF(0, 0, size, size))

    width = size * 0.07
    radius = size * 0.41
    ring = QRectF(size / 2 - radius, size / 2 - radius, 2 * radius, 2 * radius)
    painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
    # Qt angles: counter-clockwise from 3 o'clock, in 1/16 degree
    for start_deg, color in ((-24, COLORS["warning"]), (-144, COLORS["info"]),
                             (-264, COLORS["accent"])):
        pen = QPen(QColor(color), width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(ring, int(start_deg * 16), int(108 * 16))

    font = QFont()
    font.setBold(True)
    font.setPixelSize(max(6, int(size * 0.50)))
    painter.setFont(font)
    painter.setPen(QPen(QColor(COLORS["text"])))
    painter.drawText(QRectF(0, size * 0.015, size, size), "R", QTextOption(Qt.AlignmentFlag.AlignCenter))


class LogoMark(QWidget):
    """Square widget showing the logo."""

    def __init__(self, size: int = 40) -> None:
        super().__init__()
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        draw_logo(painter, self._size)
        painter.end()


def logo_icon(size: int = 128) -> QIcon:
    """Window / taskbar icon (needs a running QApplication)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    draw_logo(painter, size)
    painter.end()
    return QIcon(pixmap)
