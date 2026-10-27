"""A row of tiles with the key results of a design; the numbers count up when they appear."""

from __future__ import annotations

import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from resize_energy.core.versions import Kpi, read_kpis
from resize_energy.gui.kpi_format import ease_out, format_value

COUNT_SECONDS = 0.7


class KpiStrip(QWidget):
    """Tiles for the entries of ``KPI_SPECS`` of the design (nothing for other designs)."""

    def __init__(self) -> None:
        super().__init__()
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(10)
        self._tiles: list[tuple[QLabel, Kpi]] = []
        self._t0 = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self.setVisible(False)

    def clear(self) -> None:
        self._timer.stop()
        while self._row.count():
            item = self._row.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._tiles = []
        self.setVisible(False)

    def show_design(self, design: object) -> None:
        """Rebuild the tiles for ``design`` and start the count-up."""
        self.clear()
        kpis = read_kpis(design)[:6]
        for kpi in kpis:
            tile = QFrame()
            tile.setObjectName("kpiTile")
            box = QVBoxLayout(tile)
            box.setContentsMargins(14, 6, 14, 6)
            box.setSpacing(0)
            caption = QLabel(kpi.label)
            caption.setObjectName("kpiLabel")
            value = QLabel(format_value(0.0, kpi.decimals))
            value.setObjectName("kpiValue")
            unit = QLabel(kpi.unit or " ")
            unit.setObjectName("kpiUnit")
            for widget in (caption, value, unit):
                box.addWidget(widget)
            self._row.addWidget(tile, 1)
            self._tiles.append((value, kpi))
        if not kpis:
            return
        self.setVisible(True)
        self._t0 = time.monotonic()
        self._timer.start()

    def _tick(self) -> None:
        progress = ease_out((time.monotonic() - self._t0) / COUNT_SECONDS)
        for label, kpi in self._tiles:
            label.setText(format_value(kpi.value * progress, kpi.decimals))
        if progress >= 1.0:
            self._timer.stop()

    def finish(self) -> None:
        """Jump to the final numbers (used by tests and when the page is rebuilt)."""
        self._timer.stop()
        for label, kpi in self._tiles:
            label.setText(format_value(kpi.value, kpi.decimals))


__all__ = ["KpiStrip"]
