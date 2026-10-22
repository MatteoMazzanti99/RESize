"""'Why?' widgets: a small '?' button and the dialog it opens (PySide6)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QPushButton, QTextBrowser, QVBoxLayout

from resize_energy.gui.theme import SCREEN_DOC_CSS
from resize_energy.tutor.why_html import explanation_html


class WhyDialog(QDialog):
    """Shows formula, reasoning, assumptions (and the user's numbers, if available)."""

    def __init__(self, key: str, worked: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Why?")
        self.resize(580, 480)
        browser = QTextBrowser()
        browser.document().setDefaultStyleSheet(SCREEN_DOC_CSS)
        browser.setHtml(explanation_html(key, worked))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(browser)
        layout.addWidget(buttons)


class WhyButton(QPushButton):
    """Round-ish '?' button placed next to a field; opens the explanation of ``key``."""

    def __init__(self, key: str, worked_provider: Callable[[], str | None] | None = None) -> None:
        super().__init__("?")
        self.key = key
        self._provider = worked_provider
        self.setObjectName("whyButton")
        self.setFixedSize(24, 24)
        self.setToolTip("Why? Explain this step")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._open)

    def _open(self) -> None:
        worked = self._provider() if self._provider else None
        WhyDialog(self.key, worked, self).exec()
