"""Side panel of the wizard: the result so far, updated while the user types."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from resize_energy.gui import theme
from resize_energy.gui.kpi_format import format_value
from resize_energy.gui.preview_data import Preview
from resize_energy.gui.widgets import make_label


class BarsView(QWidget):
    """Small bar chart whose bars glide to their new height."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(96)
        self._now: list[float] = []
        self._to: list[float] = []
        self._from: list[float] = []
        self._labels: tuple[str, ...] = ()
        self.color = QColor("#0A7452")
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(260)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._step)

    def set_bars(self, bars: tuple[float, ...], labels: tuple[str, ...], color: str) -> None:
        self.color = QColor(color)
        self._labels = labels
        top = max(bars) if bars else 0.0
        target = [b / top if top > 0 else 0.0 for b in bars]
        self._from = (self._now + [0.0] * len(target))[:len(target)]
        self._to = target
        self._anim.stop()
        self._anim.start()

    def _step(self, t: float) -> None:
        self._now = [a + (b - a) * float(t) for a, b in zip(self._from, self._to, strict=False)]
        self.update()

    def paintEvent(self, _event) -> None:
        if not self._now:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        n = len(self._now)
        label_h = 16 if self._labels else 0
        h = self.height() - label_h
        gap = 4.0
        w = (self.width() - gap * (n - 1)) / n
        for i, v in enumerate(self._now):
            bar_h = max(2.0, v * (h - 4))
            colour = QColor(self.color)
            colour.setAlphaF(0.45 + 0.55 * v)
            p.setBrush(colour)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(i * (w + gap), h - bar_h, w, bar_h), 3, 3)
        if self._labels:
            p.setPen(QColor(theme.COLORS["muted"]))
            p.drawText(0, h + 2, self.width(), label_h,
                       Qt.AlignmentFlag.AlignLeft, self._labels[0])
            if len(self._labels) > 2:
                p.drawText(0, h + 2, self.width(), label_h,
                           Qt.AlignmentFlag.AlignHCenter, self._labels[1])
            p.drawText(0, h + 2, self.width(), label_h,
                       Qt.AlignmentFlag.AlignRight, self._labels[-1])


class LivePreview(QFrame):
    """Headline number + bars + checks. ``show_preview`` or ``show_waiting``."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("livePanel")
        self.setFixedWidth(290)
        box = QVBoxLayout(self)
        box.setContentsMargins(16, 16, 16, 16)
        box.setSpacing(8)
        box.addWidget(make_label("LIVE PREVIEW", "overline", wrap=False))
        self.label = QLabel("")
        self.label.setObjectName("kpiLabel")
        self.value = QLabel("")
        self.value.setObjectName("kpiValue")
        self.unit = QLabel("")
        self.unit.setObjectName("kpiUnit")
        self._value_anim = QVariantAnimation(self)
        self._value_anim.setDuration(240)
        self._value_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._value_anim.valueChanged.connect(self._tween)
        self._shown: tuple[float, int] | None = None   # (number, decimals) on screen now
        self.bars = BarsView()
        self.extra = QLabel("")
        self.extra.setWordWrap(True)
        self.notes = QLabel("")
        self.notes.setWordWrap(True)
        self.notes.setTextFormat(Qt.TextFormat.RichText)
        for widget in (self.label, self.value, self.unit, self.bars, self.extra, self.notes):
            box.addWidget(widget)
        box.addStretch(1)

    def _set_value(self, text: str) -> None:
        """Glide from the number on screen to the new one (plain text when it is not a number)."""
        try:
            target = float(text.replace(",", ""))
        except ValueError:
            self._shown = None
            self.value.setText(text)
            return
        decimals = len(text.split(".")[1]) if "." in text else 0
        start = self._shown[0] if self._shown else target
        self._shown = (target, decimals)
        self._value_anim.stop()
        self._value_anim.setStartValue(start)
        self._value_anim.setEndValue(target)
        self._value_anim.start()

    def _tween(self, number: float) -> None:
        if self._shown is not None:
            self.value.setText(format_value(float(number), self._shown[1]))

    def show_waiting(self, message: str) -> None:
        self.label.setText(message)
        for widget in (self.value, self.unit, self.extra, self.notes):
            widget.setText("")
        self.bars.setVisible(False)

    def show_preview(self, preview: Preview, color: str) -> None:
        c = theme.COLORS
        self.label.setText(preview.label)
        self._set_value(preview.value)
        self.unit.setText(preview.unit)
        self.bars.setVisible(bool(preview.bars))
        if preview.bars:
            self.bars.set_bars(preview.bars, preview.bar_labels, color)
        self.extra.setText("<br>".join(
            f"<span style='color:{c['muted']}'>{a}</span>  <b>{b}</b>" for a, b in preview.extra))
        tone = {"ok": c["accent"], "warning": c["warning"], "error": c["error"]}
        mark = {"ok": "✓", "warning": "!", "error": "✕"}
        self.notes.setText("<br>".join(
            f"<span style='color:{tone.get(k, c['muted'])}'><b>{mark.get(k, '•')}</b></span> {t}"
            for k, t in preview.notes))
