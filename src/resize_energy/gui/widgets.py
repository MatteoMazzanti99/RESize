"""Reusable visual pieces: cards, status pills and the left-hand step navigation."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from resize_energy import __version__
from resize_energy.gui.brand import LogoMark
from resize_energy.gui.theme import COLORS


def make_label(text: str, name: str = "", wrap: bool = True) -> QLabel:
    """QLabel with an object name (used by the style sheet)."""
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setWordWrap(wrap)
    return label


class HoverLift(QObject):
    """A card rises a little under the mouse: its shadow grows and drops lower, smoothly."""

    def __init__(self, frame: QFrame, shadow: QGraphicsDropShadowEffect) -> None:
        super().__init__(frame)
        self._shadow = shadow
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.valueChanged.connect(self._apply)
        self._t = 0.0
        frame.installEventFilter(self)

    def _apply(self, t: float) -> None:
        self._t = float(t)
        self._shadow.setBlurRadius(22 + 16 * self._t)
        self._shadow.setOffset(0, 4 + 5 * self._t)

    def eventFilter(self, obj, event) -> bool:
        kind = event.type()
        if kind in (QEvent.Type.Enter, QEvent.Type.Leave):
            self._anim.stop()
            self._anim.setStartValue(self._t)
            self._anim.setEndValue(1.0 if kind == QEvent.Type.Enter else 0.0)
            self._anim.start()
        return False


def make_card(kind: str = "card", frame: QFrame | None = None) -> tuple[QFrame, QVBoxLayout]:
    """Rounded panel. ``kind``: 'card', 'cardActive' (available) or 'cardDim' (planned).

    Pass ``frame`` to build the card on a QFrame subclass (for instance a clickable card).
    """
    frame = frame if frame is not None else QFrame()
    frame.setObjectName(kind)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(6)
    shadow = QGraphicsDropShadowEffect(frame)  # soft lift; the card keeps a hairline border
    shadow.setBlurRadius(22)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(15, 27, 45, 28))
    frame.setGraphicsEffect(shadow)
    if kind == "cardActive":
        HoverLift(frame, shadow)
    return frame, layout


def make_pill(text: str, on: bool, kind: str = "") -> QLabel:
    """A small tag. ``kind`` "elec", "heat" or "tag" gives it the colour of what it names."""
    label = QLabel(text)
    named = {"elec": "pillElec", "heat": "pillHeat", "tag": "pillTag"}.get(kind)
    label.setObjectName(named or ("pillOn" if on else "pillOff"))
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    return label


class Sidebar(QWidget):
    """Brand block plus the numbered steps of the sizing path, with the current one lit."""

    def __init__(self, steps: list[str]) -> None:
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(250)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 26, 18, 20)
        layout.setSpacing(4)
        layout.addWidget(LogoMark(44))
        layout.addSpacing(8)
        layout.addWidget(make_label("RESize", "brandName", wrap=False))
        layout.addWidget(make_label("Renewable energy sizing tutor", "brandTagline"))
        layout.addSpacing(30)
        layout.addWidget(make_label("SIZING PATH", "sidebarNote", wrap=False))
        layout.addSpacing(6)
        self._list = StepList()
        layout.addWidget(self._list)
        layout.addStretch(1)
        layout.addWidget(make_label(
            "Preliminary and educational sizing. Not a substitute for detailed engineering "
            "design.", "sidebarNote"))
        layout.addSpacing(4)
        layout.addWidget(make_label(f"v{__version__}", "sidebarNote", wrap=False))
        self.set_steps(steps)

    def set_steps(self, steps: list[str]) -> None:
        """Replace the listed steps (each technology has its own path)."""
        self._list.set_steps(steps)

    def set_current(self, index: int) -> None:
        """Highlight step ``index`` (0-based); earlier steps are shown as done, -1 = none."""
        self._list.set_current(index)


class StepList(QWidget):
    """The steps as a vertical stepper: ticked circles for the done ones, a ring for the
    current one, a line joining them."""

    ROW = 40
    R = 11

    def __init__(self) -> None:
        super().__init__()
        self._steps: list[str] = []
        self._current = -1
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def set_steps(self, steps: list[str]) -> None:
        self._steps = list(steps)
        self._current = -1
        self.setFixedHeight(max(1, self.ROW * len(self._steps)))
        self.update()

    def set_current(self, index: int) -> None:
        self._current = index
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        accent, border = QColor(COLORS["accent"]), QColor(COLORS["border"])
        cx = float(self.R + 3)
        for i, name in enumerate(self._steps):
            cy = i * self.ROW + self.ROW / 2.0
            if i > 0:       # the line from the previous circle
                painter.setPen(QPen(accent if i <= self._current else border, 2.0))
                painter.drawLine(QPointF(cx, cy - self.ROW + self.R + 3),
                                 QPointF(cx, cy - self.R - 3))
            if i == self._current:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(COLORS["accent_tint"]))
                painter.drawRoundedRect(QRectF(0, cy - self.ROW / 2.0 + 3, self.width(),
                                               self.ROW - 6), 12, 12)
            circle = QRectF(cx - self.R, cy - self.R, 2 * self.R, 2 * self.R)
            if i < self._current:           # done: filled, with a tick
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(accent)
                painter.drawEllipse(circle)
                tick = QPen(QColor(COLORS["accent_text"]), 2.2)
                tick.setCapStyle(Qt.PenCapStyle.RoundCap)
                tick.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(tick)
                painter.drawPolyline([QPointF(cx - 4.5, cy + 0.5), QPointF(cx - 1.2, cy + 3.6),
                                      QPointF(cx + 4.6, cy - 3.4)])
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(accent if i == self._current else border, 2.0))
                painter.drawEllipse(circle)
                painter.setPen(accent if i == self._current else QColor(COLORS["muted"]))
                painter.drawText(circle, Qt.AlignmentFlag.AlignCenter, str(i + 1))
            font = QFont(painter.font())
            font.setBold(i == self._current)
            painter.setFont(font)
            colour = COLORS["text"] if i <= self._current else COLORS["muted"]
            painter.setPen(QColor(colour))
            room = self.width() - (2 * self.R + 22)
            shown = QFontMetricsF(font).elidedText(name, Qt.TextElideMode.ElideRight, room)
            painter.drawText(QRectF(2 * self.R + 16, cy - 12, room + 4, 24),
                             Qt.AlignmentFlag.AlignVCenter, shown)
        painter.end()


class StepPage(QWidget):
    """One step of the sizing path: a title, a subtitle and two hooks used by the window.

    ``initializePage`` runs when the user arrives from the previous step; ``validatePage``
    runs before leaving forward and returns False to stay (after telling the user why).
    """

    show_header = True
    art_key: str | None = None   # small illustration in the header (see report/step_art.py)

    def __init__(self) -> None:
        super().__init__()
        self._title = ""
        self._subtitle = ""

    def setTitle(self, text: str) -> None:
        self._title = text

    def setSubTitle(self, text: str) -> None:
        self._subtitle = text

    def title(self) -> str:
        return self._title

    def subTitle(self) -> str:
        return self._subtitle

    def initializePage(self) -> None:
        """Called when the page is about to be shown going forward."""

    def validatePage(self) -> bool:
        """Return True to allow moving to the next step."""
        return True
