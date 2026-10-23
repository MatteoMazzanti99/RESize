"""Drag-and-drop pieces of the home page: clickable technology cards and the Compare zone.

A technology card starts its project when clicked and can be dragged into the Compare zone.
In the zone the technologies appear as small icons drifting around, without any text; once two
or more are inside, the Compare button is enabled.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable

from PySide6.QtCore import QMimeData, QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QDrag, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from resize_energy.gui.icons import paint_icon_tile
from resize_energy.gui.theme import COLORS
from resize_energy.gui.zone_physics import ICON_SIZE, advance

MIME_PREFIX = "resize/tech:"
TICK_MS = 33


def icon_pixmap(kind: str, size: int = ICON_SIZE) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    paint_icon_tile(painter, kind, float(size))
    painter.end()
    return pixmap


class TechCard(QFrame):
    """A card that starts the project on a click and starts a drag when moved."""

    def __init__(self, key: str, on_click: Callable[[str], None], draggable: bool = True) -> None:
        super().__init__()
        self.key = key
        self._on_click = on_click
        self._draggable = draggable
        self._press: QPoint | None = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.position().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if self._press is None or not self._draggable:
            return
        moved = (event.position().toPoint() - self._press).manhattanLength()
        if moved < QApplication.startDragDistance():
            return
        self._press = None
        mime = QMimeData()
        mime.setText(MIME_PREFIX + self.key)
        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = icon_pixmap(self.key)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        drag.exec(Qt.DropAction.CopyAction)

    def mouseReleaseEvent(self, event) -> None:
        if self._press is not None and event.button() == Qt.MouseButton.LeftButton:
            self._press = None
            self._on_click(self.key)


class _Arena(QWidget):
    """The area where the dropped icons move. Click an icon to take it out."""

    def __init__(self, zone: CompareZone) -> None:
        super().__init__()
        self.zone = zone
        self.items: dict[str, list[float]] = {}
        self.setMinimumHeight(110)
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

    def add(self, key: str, at: QPointF | None = None) -> None:
        if key in self.items:
            return
        width, height = max(self.width(), 2 * ICON_SIZE), max(self.height(), 2 * ICON_SIZE)
        x = min(max(0.0, (at.x() if at else random.uniform(0, width)) - ICON_SIZE / 2),
                width - ICON_SIZE)
        y = min(max(0.0, (at.y() if at else random.uniform(0, height)) - ICON_SIZE / 2),
                height - ICON_SIZE)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.1, 1.9)
        self.items[key] = [x, y, speed * math.cos(angle), speed * math.sin(angle)]
        self._timer.start()
        self.update()

    def remove(self, key: str) -> None:
        self.items.pop(key, None)
        if not self.items:
            self._timer.stop()
        self.update()

    def clear(self) -> None:
        self.items.clear()
        self._timer.stop()
        self.update()

    def _tick(self) -> None:
        if not self.isVisible():
            return
        advance(self.items, self.width(), self.height())
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.items:
            painter.setPen(QColor(COLORS["muted"]))
            painter.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter,
                             "Drag technologies here to compare them")
        for key, (x, y, _vx, _vy) in self.items.items():
            painter.save()
            painter.translate(x, y)
            paint_icon_tile(painter, key, float(ICON_SIZE))
            painter.restore()
        painter.end()

    def mousePressEvent(self, event) -> None:
        pos = event.position()
        for key, (x, y, _vx, _vy) in list(self.items.items()):
            if x <= pos.x() <= x + ICON_SIZE and y <= pos.y() <= y + ICON_SIZE:
                self.zone.remove(key)
                return


class CompareZone(QFrame):
    """Empty area called Compare: drop technologies in it, then press Compare."""

    def __init__(self, allowed: tuple[str, ...], on_compare: Callable[[list[str]], None]) -> None:
        super().__init__()
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.allowed = allowed
        self._on_compare = on_compare
        self.setProperty("dragOver", False)

        self.arena = _Arena(self)
        self.title = QLabel("Compare")
        self.title.setObjectName("sectionTitle")
        self.button = QPushButton("Compare  →")
        self.button.setProperty("variant", "primary")
        self.button.setEnabled(False)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.clicked.connect(lambda *_: self._compare())
        self.clear_button = QPushButton("Clear")
        self.clear_button.setProperty("variant", "ghost")
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(lambda *_: self.clear())

        header = QHBoxLayout()
        header.addWidget(self.title)
        header.addStretch(1)
        header.addWidget(self.clear_button)
        header.addWidget(self.button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)
        layout.addLayout(header)
        layout.addWidget(self.arena, 1)
        self.setMinimumHeight(190)

    # --- state ---------------------------------------------------------------------
    def keys(self) -> list[str]:
        return [k for k in self.allowed if k in self.arena.items]

    def add(self, key: str, at: QPointF | None = None) -> bool:
        if key not in self.allowed:
            return False
        self.arena.add(key, at)
        self._refresh()
        return True

    def remove(self, key: str) -> None:
        self.arena.remove(key)
        self._refresh()

    def clear(self) -> None:
        self.arena.clear()
        self._refresh()

    def _refresh(self) -> None:
        n = len(self.arena.items)
        self.button.setEnabled(n >= 2)
        self.clear_button.setEnabled(n >= 1)

    def _compare(self) -> None:
        keys = self.keys()
        if len(keys) >= 2:
            self._on_compare(keys)

    # --- drag and drop -------------------------------------------------------------
    @staticmethod
    def _key_of(event) -> str | None:
        mime = event.mimeData()
        if mime is not None and mime.hasText() and mime.text().startswith(MIME_PREFIX):
            return mime.text()[len(MIME_PREFIX):]
        return None

    def _highlight(self, on: bool) -> None:
        self.setProperty("dragOver", on)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event) -> None:
        if self._key_of(event) in self.allowed:
            event.acceptProposedAction()
            self._highlight(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._highlight(False)

    def dropEvent(self, event) -> None:
        self._highlight(False)
        key = self._key_of(event)
        if key in self.allowed:
            at = self.arena.mapFrom(self, event.position().toPoint())
            self.add(key, QPointF(at))
            event.acceptProposedAction()
