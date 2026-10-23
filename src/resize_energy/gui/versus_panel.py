"""Versus screen: round by round bars that fill up, like the life bars of a fighting game."""

from __future__ import annotations

import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter
from PySide6.QtWidgets import QWidget

from resize_energy.gui.icons import paint_icon_tile
from resize_energy.gui.theme import COLORS
from resize_energy.report.charts import TECH_COLORS
from resize_energy.report.versus import Round, rounds_won

ROUND_DELAY = 0.45     # seconds between the start of two rounds
FILL_SECONDS = 0.75
ICON = 20
ROW = 26
HEAD = 30
GAP = 16
TOP = 62


def ease_out(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1.0 - (1.0 - x) ** 3


def panel_height(n_rounds: int, n_entries: int) -> int:
    return TOP + n_rounds * (HEAD + n_entries * ROW + GAP) + 10


class VersusPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.rounds: list[Round] = []
        self._t0 = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def set_rounds(self, rounds: list[Round]) -> None:
        self.rounds = rounds
        if rounds:
            self.setMinimumHeight(panel_height(len(rounds), len(rounds[0].entries)))
        self._t0 = time.monotonic()
        self._timer.start()
        self.update()

    def _tick(self) -> None:
        total = ROUND_DELAY * len(self.rounds) + FILL_SECONDS + 0.1
        if time.monotonic() - self._t0 > total:
            self._timer.stop()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if not self.rounds:
            painter.end()
            return
        elapsed = time.monotonic() - self._t0
        w = float(self.width())
        base = QFont(painter.font())
        bold = QFont(base)
        bold.setBold(True)
        title = QFont(bold)
        title.setPointSizeF(base.pointSizeF() + 1.5)
        name_w = max(QFontMetricsF(base).horizontalAdvance(e.name)
                     for e in self.rounds[0].entries) + 8
        left = 14 + ICON + 8 + name_w
        value_w = 120.0
        track_right = max(left + 80.0, w - value_w - 24.0)

        wins = rounds_won(self.rounds)
        best = max(wins.values()) if wins else 0
        painter.setFont(title)
        painter.setPen(QColor(COLORS["text"]))
        painter.drawText(QRectF(14, 8, w - 28, 22), Qt.AlignmentFlag.AlignVCenter,
                         "Round by round")
        painter.setFont(base)
        painter.setPen(QColor(COLORS["muted"]))
        score = "   ".join(f"{name} {n}" for name, n in wins.items())
        painter.drawText(QRectF(14, 30, w - 28, 20), Qt.AlignmentFlag.AlignVCenter,
                         f"Rounds won:  {score}" if best else "No round has a clear winner")

        y = float(TOP)
        for r_index, rd in enumerate(self.rounds):
            progress = ease_out((elapsed - r_index * ROUND_DELAY) / FILL_SECONDS)
            painter.setFont(bold)
            painter.setPen(QColor(COLORS["text"]))
            painter.drawText(QRectF(14, y, w - 28, HEAD - 6), Qt.AlignmentFlag.AlignVCenter,
                             f"Round {r_index + 1}: {rd.title}")
            painter.setFont(base)
            painter.setPen(QColor(COLORS["muted"]))
            painter.drawText(QRectF(14, y, w - 28, HEAD - 6),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                             rd.hint)
            y += HEAD
            for e in rd.entries:
                is_win = rd.winner == e.name
                painter.save()
                painter.translate(14, y + (ROW - ICON) / 2)
                paint_icon_tile(painter, e.key, float(ICON))
                painter.restore()
                painter.setFont(bold if is_win else base)
                painter.setPen(QColor(COLORS["text"]))
                painter.drawText(QRectF(14 + ICON + 8, y, name_w, ROW),
                                 Qt.AlignmentFlag.AlignVCenter, e.name)
                track = QRectF(left, y + 6, track_right - left, ROW - 12)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(COLORS["surface2"]))
                painter.drawRoundedRect(track, 5, 5)
                fill = QColor(TECH_COLORS.get(e.key, COLORS["accent"]))
                if not is_win:
                    fill.setAlpha(150)
                width = max(0.0, track.width() * e.score * progress)
                if width > 0.5:
                    painter.setBrush(fill)
                    painter.drawRoundedRect(QRectF(track.left(), track.top(), width,
                                                   track.height()), 5, 5)
                painter.setFont(bold if is_win else base)
                painter.setPen(QColor(COLORS["text"]))
                mark = "  ★" if is_win and progress >= 1.0 else ""
                painter.drawText(QRectF(track_right + 10, y, value_w + 14, ROW),
                                 Qt.AlignmentFlag.AlignVCenter, e.text + mark)
                y += ROW
            y += GAP
        painter.end()
