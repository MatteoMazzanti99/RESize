"""RESize logo: a green tile with a sun above three rising bars (sizing), drawn in code."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from resize_energy.gui.theme import COLORS


def draw_logo(painter: QPainter, size: float) -> None:
    """Paint the logo inside a square of ``size`` pixels at the origin."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(Qt.PenStyle.NoPen))
    painter.setBrush(QBrush(QColor(COLORS["accent"])))
    painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.24, size * 0.24)

    ink = QBrush(QColor(COLORS["accent_text"]))
    painter.setBrush(ink)
    bar_w = size * 0.14
    base = size * 0.78
    for i, height in enumerate((0.18, 0.30, 0.42)):
        x = size * (0.20 + 0.23 * i)
        h = size * height
        painter.drawRoundedRect(QRectF(x, base - h, bar_w, h), bar_w * 0.3, bar_w * 0.3)
    radius = size * 0.09
    painter.drawEllipse(QRectF(size * 0.70 - radius, size * 0.25 - radius, 2 * radius, 2 * radius))


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
