"""A small illustration in the header of an input step (PySide6 + QtSvg).

It moves slowly while the step is on screen (the sun walks, the rotor turns...) and rests
when the window is hidden.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QElapsedTimer, QRectF, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

from resize_energy.report.step_art import ARTS, H, W, step_svg

LAP_MS = 8000
FRAME_MS = 33


class StepArt(QWidget):
    """Shows the illustration ``key`` (one of ``ARTS``); hidden when the key is empty."""

    def __init__(self) -> None:
        super().__init__()
        self.key: str | None = None
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self.update)
        self.setFixedSize(W, H)
        self.hide()

    def set_key(self, key: str | None) -> None:
        self.key = key if key in ARTS else None
        if self.key is None:
            self._timer.stop()
            self.hide()
            return
        self.show()
        self._clock.start()
        self._timer.start()
        self.update()

    def showEvent(self, event) -> None:
        if self.key is not None:
            self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def paintEvent(self, _event) -> None:
        if self.key is None:
            return
        phase = (self._clock.elapsed() % LAP_MS) / LAP_MS if self._clock.isValid() else 0.0
        renderer = QSvgRenderer(QByteArray(step_svg(self.key, phase).encode("utf-8")))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(0, 0, W, H))
        painter.end()
