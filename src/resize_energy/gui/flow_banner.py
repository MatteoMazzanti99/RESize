"""The energy-flow picture at the top of the results (PySide6 + QtSvg).

The picture comes from :mod:`resize_energy.report.flow_pictures` as SVG text. While the
widget is visible the dots on the arrows drift slowly (one lap per 7 s); the PDF gets a still
image of the same picture.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QElapsedTimer, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QSizePolicy, QWidget

from resize_energy.report.flow_art import Flow, Node, flow_svg, picture_size

LAP_MS = 7000
FRAME_MS = 60
SCALE = 0.52            # height of the banner on screen relative to the picture's own size

Picture = tuple[list[Node], list[Flow]]


def _draw(painter: QPainter, picture: Picture, phase: float, target: QRectF) -> None:
    nodes, flows = picture
    svg = flow_svg(nodes, flows, phase, "light")
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    w, h = picture_size(nodes)
    k = min(target.width() / w, target.height() / h)
    box = QRectF(target.x() + (target.width() - w * k) / 2,
                 target.y() + (target.height() - h * k) / 2, w * k, h * k)
    renderer.render(painter, box)


def picture_image(picture: Picture, width_px: int = 1500) -> QImage:
    """A still image of the picture (white background), for the PDF."""
    w, h = picture_size(picture[0])
    image = QImage(width_px, int(width_px * h / w), QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw(painter, picture, 0.25, QRectF(0, 0, image.width(), image.height()))
    painter.end()
    return image


class FlowBanner(QWidget):
    """Shows one picture; hidden while there is none."""

    def __init__(self) -> None:
        super().__init__()
        self.picture: Picture | None = None
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self.update)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.hide()

    def set_picture(self, picture: Picture | None) -> None:
        self.picture = picture
        if picture is None:
            self.hide()
            self._timer.stop()
            return
        self.setFixedHeight(int(picture_size(picture[0])[1] * SCALE))
        self.show()
        self._clock.start()
        self._timer.start()
        self.update()

    def showEvent(self, event) -> None:
        if self.picture is not None:
            self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def paintEvent(self, _event) -> None:
        if self.picture is None:
            return
        phase = (self._clock.elapsed() % LAP_MS) / LAP_MS if self._clock.isValid() else 0.0
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        card = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(card, 12, 12)
        painter.fillPath(clip, QColor("white"))
        painter.setClipPath(clip)
        painter.setPen(Qt.PenStyle.NoPen)
        _draw(painter, self.picture, phase, QRectF(self.rect()))
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#D5DEE9"), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(card, 12, 12)
        painter.end()
