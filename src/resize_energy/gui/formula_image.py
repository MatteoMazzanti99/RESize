"""Pictures of the formulas for the 'Why?' texts (PySide6 + QtSvg).

:mod:`resize_energy.report.formula_art` draws a formula as SVG and remembers it under a name;
the HTML refers to it as ``<img src="chart:fx_...">``. These helpers turn the SVG into an image
the first time a text browser or the PDF document asks for it.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QTextBrowser

from resize_energy.report.formula_art import REGISTRY

SCALE = 3.0        # pixels per logical pixel in the PDF; on screen the device ratio is used
_cache: dict[tuple[str, float], QImage] = {}


def formula_image(url: str, scale: float = SCALE) -> QImage | None:
    """The image for ``chart:fx_...`` drawn at ``scale`` pixels per logical pixel.

    On screen ``scale`` is the widget's device pixel ratio, so the picture is shown 1:1 on the
    physical pixels (a bigger picture shrunk by the text engine looks soft)."""
    name = url.removeprefix("chart:")
    if not name.startswith("fx_"):
        return None
    key = (name, round(scale, 3))
    if key in _cache:
        return _cache[key]
    formula = REGISTRY.get(name)
    if formula is None:
        return None
    image = QImage(round(formula.w * scale), round(formula.h * scale), QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    QSvgRenderer(QByteArray(formula.svg.encode("utf-8"))).render(painter)
    painter.end()
    image.setDevicePixelRatio(scale)
    _cache[key] = image
    return image


class FormulaBrowser(QTextBrowser):
    """A text browser that can show the formula pictures."""

    def loadResource(self, rtype, url):
        image = formula_image(url.toString(), max(1.0, self.devicePixelRatioF()))
        return image if image is not None else super().loadResource(rtype, url)
