"""Drag-and-drop pieces of the home page: clickable technology cards and the Compare zone.

A technology card starts its project when clicked and can be dragged into the Compare zone.
In the zone the technologies stand as small icons facing each other with a "VS" between them
(no text with their names); with two or more the Compare button is enabled, and pressing it
plays a short clash before the comparison opens.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtCore import QMimeData, QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QDrag, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from resize_energy.core.comparison import possible_carriers
from resize_energy.gui.icons import paint_icon_tile
from resize_energy.gui.theme import COLORS
from resize_energy.gui.zone_layout import (
    CLASH_SECONDS,
    ICON_SIZE,
    autoscroll_step,
    bob,
    clash_x,
    flash_alpha,
    pop_scale,
    slot_centres,
    vs_centres,
)

MIME_PREFIX = "resize/tech:"
SEGMENT_LABELS = {"electricity": "Electricity", "heat": "Heat", "both": "Both"}
CARRIER_WORDS = {"electricity": "electricity", "heat": "heat", "both": "electricity and heat"}
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
        timer = self._start_autoscroll()
        try:
            drag.exec(Qt.DropAction.CopyAction)
        finally:
            if timer is not None:
                timer.stop()

    def _scroll_area(self) -> QAbstractScrollArea | None:
        widget = self.parentWidget()
        while widget is not None and not isinstance(widget, QAbstractScrollArea):
            widget = widget.parentWidget()
        return widget

    def _start_autoscroll(self) -> QTimer | None:
        """While the card is dragged near the top or bottom edge, the page scrolls with it."""
        area = self._scroll_area()
        if area is None:
            return None
        bar = area.verticalScrollBar()

        def tick() -> None:
            view = area.viewport()
            top = view.mapToGlobal(QPoint(0, 0)).y()
            step = autoscroll_step(QCursor.pos().y(), top, top + view.height())
            if step:
                bar.setValue(bar.value() + step)

        timer = QTimer(self)
        timer.timeout.connect(tick)
        timer.start(16)
        return timer

    def mouseReleaseEvent(self, event) -> None:
        if self._press is not None and event.button() == Qt.MouseButton.LeftButton:
            self._press = None
            self._on_click(self.key)


class _Arena(QWidget):
    """The area where the dropped icons face each other. Click an icon to take it out."""

    def __init__(self, zone: CompareZone) -> None:
        super().__init__()
        self.zone = zone
        self.keys: list[str] = []
        self._born: dict[str, float] = {}
        self._clash_start: float | None = None
        self._after_clash: Callable[[], None] | None = None
        self.setMinimumHeight(110)
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

    # --- content ---------------------------------------------------------------------
    def add(self, key: str) -> None:
        if key in self.keys:
            return
        self.keys.append(key)
        self._born[key] = time.monotonic()
        self._timer.start()
        self.update()

    def remove(self, key: str) -> None:
        if key in self.keys:
            self.keys.remove(key)
            self._born.pop(key, None)
        if not self.keys:
            self._timer.stop()
        self.update()

    def clear(self) -> None:
        self.keys.clear()
        self._born.clear()
        self._timer.stop()
        self.update()

    def busy(self) -> bool:
        return self._clash_start is not None

    def clash(self, then: Callable[[], None]) -> None:
        """Play the face-off, then call ``then``."""
        self._clash_start = time.monotonic()
        self._after_clash = then
        self._timer.start()

    # --- animation -------------------------------------------------------------------
    def _tick(self) -> None:
        if self._clash_start is not None and (
                time.monotonic() - self._clash_start >= CLASH_SECONDS):
            done, self._after_clash = self._after_clash, None
            self._clash_start = None
            if done is not None:
                done()
        if self.isVisible():
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w, h = float(self.width()), float(self.height())
        now = time.monotonic()
        if not self.keys:
            painter.setPen(QColor(COLORS["muted"]))
            painter.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter,
                             "Drag technologies here to compare them")
            painter.end()
            return
        centres = slot_centres(len(self.keys), w, h)
        progress = (None if self._clash_start is None
                    else (now - self._clash_start) / CLASH_SECONDS)
        mid_x = w / 2.0
        for i, (key, (cx, cy)) in enumerate(zip(self.keys, centres, strict=True)):
            x = cx if progress is None else clash_x(cx, mid_x, progress)
            y = cy + (bob(now, i) if progress is None else 0.0)
            scale = pop_scale(now - self._born.get(key, 0.0))
            painter.save()
            painter.translate(x, y)
            painter.scale(scale, scale)
            painter.translate(-ICON_SIZE / 2.0, -ICON_SIZE / 2.0)
            paint_icon_tile(painter, key, float(ICON_SIZE))
            painter.restore()
        font = QFont(painter.font())
        font.setBold(True)
        font.setPointSizeF(11.0)
        painter.setFont(font)
        for vx, vy in vs_centres(centres):
            if progress is not None and progress > 0.5:
                continue
            painter.setPen(QColor("#C77700"))
            painter.drawText(QRectF(vx - 20, vy - 12, 40, 24), Qt.AlignmentFlag.AlignCenter, "VS")
        if progress is not None:
            alpha = flash_alpha(progress)
            if alpha > 0:
                colour = QColor("#F5B941")
                colour.setAlpha(alpha)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(colour)
                painter.drawEllipse(QPointF(mid_x, centres[0][1]), 34.0, 34.0)
        elif len(self.keys) == 1:
            painter.setPen(QColor(COLORS["muted"]))
            small = QFont(painter.font())
            small.setBold(False)
            small.setPointSizeF(8.5)
            painter.setFont(small)
            painter.drawText(QRectF(0, h - 26, w, 20), Qt.AlignmentFlag.AlignCenter,
                             "Needs an opponent: drag another one in")
        painter.end()

    def mousePressEvent(self, event) -> None:
        if self.busy():
            return
        pos = event.position()
        centres = slot_centres(len(self.keys), float(self.width()), float(self.height()))
        for key, (cx, cy) in zip(list(self.keys), centres, strict=True):
            if abs(pos.x() - cx) <= ICON_SIZE / 2 and abs(pos.y() - cy) <= ICON_SIZE / 2:
                self.zone.remove(key)
                return


class CompareZone(QFrame):
    """Empty area called Compare: drop technologies in it, then press Compare."""

    def __init__(self, allowed: tuple[str, ...],
                 on_compare: Callable[[list[str], str], None]) -> None:
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
        # what to compare: only the kinds of energy that the dropped technologies allow
        self.mode = QWidget()
        self.mode.setObjectName("segmented")
        self.mode.setToolTip("Compare the electricity, the heat, or both (the plants that make "
                             "each are compared on the same demand)")
        seg = QHBoxLayout(self.mode)
        seg.setContentsMargins(3, 3, 3, 3)
        seg.setSpacing(2)
        self._group = QButtonGroup(self.mode)
        self._group.setExclusive(True)
        self._segments: dict[str, QPushButton] = {}
        for key, label in SEGMENT_LABELS.items():
            segment = QPushButton(label)
            segment.setProperty("variant", "segment")
            segment.setCheckable(True)
            segment.setCursor(Qt.CursorShape.PointingHandCursor)
            self._group.addButton(segment)
            self._segments[key] = segment
            seg.addWidget(segment)
        self._segments["both"].setChecked(True)
        self.mode.setVisible(False)
        self.hint = QLabel("")
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)
        self.hint.setVisible(False)
        self.clear_button = QPushButton("Clear")
        self.clear_button.setProperty("variant", "ghost")
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(lambda *_: self.clear())

        header = QHBoxLayout()
        header.addWidget(self.title)
        header.addStretch(1)
        header.addWidget(self.mode)
        header.addWidget(self.clear_button)
        header.addWidget(self.button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)
        layout.addLayout(header)
        layout.addWidget(self.hint)
        layout.addWidget(self.arena, 1)
        self.setMinimumHeight(190)

    # --- state ---------------------------------------------------------------------
    def keys(self) -> list[str]:
        return [k for k in self.allowed if k in self.arena.keys]

    def add(self, key: str) -> bool:
        if key not in self.allowed:
            return False
        self.arena.add(key)
        self._refresh()
        return True

    def remove(self, key: str) -> None:
        self.arena.remove(key)
        self._refresh()

    def clear(self) -> None:
        self.arena.clear()
        self._refresh()

    def carrier(self) -> str:
        """The kind of comparison chosen on the switch ("electricity", "heat" or "both")."""
        for key, segment in self._segments.items():
            if segment.isChecked():
                return key
        return "electricity"

    def _refresh(self) -> None:
        n = len(self.arena.keys)
        busy = self.arena.busy()
        options = possible_carriers(tuple(self.keys()))
        previous = self.carrier()
        for key, segment in self._segments.items():
            segment.setEnabled(key in options)
        if previous not in options and options:
            self._segments["both" if "both" in options else options[0]].setChecked(True)
        self.mode.setVisible(len(options) > 1)
        if n >= 2 and not options:
            self.hint.setText(
                "These cannot be compared: pick at least two that make electricity, or at least "
                "two that make heat (biomass and geothermal make both).")
        elif len(options) == 1:
            self.hint.setText(f"They are compared on {CARRIER_WORDS[options[0]]}.")
        else:
            self.hint.setText("")
        self.hint.setVisible(bool(self.hint.text()))
        self.button.setEnabled(bool(options) and not busy)
        self.clear_button.setEnabled(n >= 1 and not busy)

    def _compare(self) -> None:
        keys = self.keys()
        if len(keys) < 2 or self.arena.busy():
            return
        carrier = self.carrier()
        if carrier not in possible_carriers(tuple(keys)):
            return

        def go() -> None:
            self._refresh()
            self._on_compare(keys, carrier)

        self.arena.clash(go)
        self._refresh()

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
            self.add(key)
            event.acceptProposedAction()
