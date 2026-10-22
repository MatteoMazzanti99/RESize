"""Icon tile widget: draws the technology icons from :mod:`icon_shapes` (PySide6)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from resize_energy.gui.icon_shapes import GRID, ICONS, STROKE
from resize_energy.gui.theme import COLORS


class IconTile(QWidget):
    """A rounded tile with a technology icon in the accent colour."""

    def __init__(self, kind: str, size: int = 44) -> None:
        super().__init__()
        self.kind = kind
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(QColor(COLORS["surface2"])))
        s = float(self._size)
        painter.drawRoundedRect(QRectF(0, 0, s, s), s * 0.25, s * 0.25)

        accent = QColor(COLORS["accent"])
        pen = QPen(accent, STROKE * (s * 0.62) / GRID)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        scale = s * 0.62 / GRID
        offset = s * 0.19
        for points, closed, filled in ICONS.get(self.kind, []):
            path = QPainterPath()
            first = points[0]
            path.moveTo(QPointF(offset + first[0] * scale, offset + first[1] * scale))
            for x, y in points[1:]:
                path.lineTo(QPointF(offset + x * scale, offset + y * scale))
            if closed:
                path.closeSubpath()
            painter.setPen(pen)
            painter.setBrush(QBrush(accent) if filled else QBrush(Qt.BrushStyle.NoBrush))
            painter.drawPath(path)
        painter.end()
