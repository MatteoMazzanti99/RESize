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

SCALE = 2          # pixels per logical pixel, so that the formulas stay sharp on screen and in print
_cache: dict[str, QImage] = {}


def formula_image(url: str) -> QImage | None:
    """The image for ``chart:fx_...`` (None for anything else)."""
    name = url.removeprefix("chart:")
    if not name.startswith("fx_"):
        return None
    if name in _cache:
        return _cache[name]
    formula = REGISTRY.get(name)
    if formula is None:
        return None
    image = QImage(formula.w * SCALE, formula.h * SCALE, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    QSvgRenderer(QByteArray(formula.svg.encode("utf-8"))).render(painter)
    painter.end()
    _cache[name] = image
    return image


class FormulaBrowser(QTextBrowser):
    """A text browser that can show the formula pictures."""

    def loadResource(self, rtype, url):
        image = formula_image(url.toString())
        return image if image is not None else super().loadResource(rtype, url)
