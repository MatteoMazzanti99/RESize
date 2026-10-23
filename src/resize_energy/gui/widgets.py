"""Reusable visual pieces: cards, status pills and the left-hand step navigation."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

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


def make_card(kind: str = "card") -> tuple[QFrame, QVBoxLayout]:
    """Rounded panel. ``kind``: 'card', 'cardActive' (available) or 'cardDim' (planned)."""
    frame = QFrame()
    frame.setObjectName(kind)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(6)
    return frame, layout


def make_pill(text: str, on: bool) -> QLabel:
    label = QLabel(text)
    label.setObjectName("pillOn" if on else "pillOff")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    return label


class Sidebar(QWidget):
    """Brand block plus the numbered steps of the sizing path, with the current one lit."""

    def __init__(self, steps: list[str]) -> None:
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(250)
        self._labels: list[QLabel] = []
        self._steps = steps

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
        self._steps_layout = QVBoxLayout()
        self._steps_layout.setSpacing(4)
        layout.addLayout(self._steps_layout)
        layout.addStretch(1)
        layout.addWidget(make_label(
            "Preliminary and educational sizing. Not a substitute for detailed engineering "
            "design.", "sidebarNote"))
        layout.addSpacing(4)
        layout.addWidget(make_label(f"v{__version__}", "sidebarNote", wrap=False))
        self.set_steps(steps)

    def set_steps(self, steps: list[str]) -> None:
        """Replace the listed steps (each technology has its own path)."""
        for label in self._labels:
            self._steps_layout.removeWidget(label)
            label.deleteLater()
        self._labels = []
        self._steps = steps
        for _ in steps:
            label = QLabel()
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setContentsMargins(0, 7, 0, 7)
            self._labels.append(label)
            self._steps_layout.addWidget(label)
        self.set_current(-1)

    def set_current(self, index: int) -> None:
        """Highlight step ``index`` (0-based); earlier steps are shown as done, -1 = none."""
        for i, (label, name) in enumerate(zip(self._labels, self._steps, strict=True)):
            if i < index:
                mark, color, weight = "&#10003;", COLORS["accent"], 400
            elif i == index:
                mark, color, weight = "&#9679;", COLORS["accent"], 700
            else:
                mark, color, weight = "&#9675;", COLORS["muted"], 400
            text_color = COLORS["text"] if i == index else color if i < index else COLORS["muted"]
            label.setText(
                f'<span style="color:{color}">{mark}</span>&nbsp;&nbsp;'
                f'<span style="color:{text_color}; font-weight:{weight}">'
                f"{i + 1}. {name}</span>"
            )


class StepPage(QWidget):
    """One step of the sizing path: a title, a subtitle and two hooks used by the window.

    ``initializePage`` runs when the user arrives from the previous step; ``validatePage``
    runs before leaving forward and returns False to stay (after telling the user why).
    """

    show_header = True

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
