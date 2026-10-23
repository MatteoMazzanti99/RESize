"""Home screen: what RESize is for, what it can size today and what is coming."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from resize_energy.gui.icons import IconTile
from resize_energy.gui.widgets import StepPage, make_card, make_label, make_pill

BENEFITS: list[tuple[str, str, str]] = [
    ("?", "Learn the why",
     ("Every number comes with its formula, the assumptions behind it and your own values "
      "plugged in, so you understand the choice and not only the result.")),
    ("✓", "Check your design",
     ("Automatic checks flag string voltages, MPPT window, current limits and the DC/AC ratio "
      "before they become a problem in your report or your plant.")),
    ("↓", "Get the report",
     ("Export a PDF with inputs, results, checks and the method used, ready for a project "
      "or a first-pass design review.")),
]

# (icon text, title, description, available now)
TECHNOLOGIES: list[tuple[str, str, str, bool]] = [
    ("pv", "Photovoltaic", "Array, strings, inverter and yearly yield from PVGIS data.", True),
    ("wind", "Wind", "Wind resource at hub height, turbine yield, number of turbines and layout.", True),
    ("biomass", "Biomass", "Plant sizing and fuel supply for heat and power.", False),
    ("hydrogen", "Green hydrogen", "PEM electrolyser coupled to photovoltaic or wind.", False),
]


class HomePage(StepPage):
    """Landing page. ``on_start("pv" | "wind")`` is called when the user starts a project."""

    show_header = False

    def __init__(self, on_start: Callable[[str], None]) -> None:
        super().__init__()
        self.setTitle("Home")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(make_label("RENEWABLE ENERGY SIZING TUTOR", "overline", wrap=False))
        root.addSpacing(6)
        root.addWidget(make_label("Size renewable energy systems.\nStep by step, with the why.",
                                  "headline"))
        root.addSpacing(10)
        root.addWidget(make_label(
            "RESize takes you from site data to a sized plant. It is built for MSc students in "
            "renewable energy and for engineers doing a first-pass design: at each step you see "
            "the formula, the assumptions and your own numbers.", "lead"))
        root.addSpacing(16)

        start = QPushButton("Start a photovoltaic project  →")
        start.setProperty("variant", "primary")
        start.setCursor(Qt.CursorShape.PointingHandCursor)
        start.clicked.connect(lambda *_: on_start("pv"))
        start_wind = QPushButton("Start a wind project  →")
        start_wind.setCursor(Qt.CursorShape.PointingHandCursor)
        start_wind.clicked.connect(lambda *_: on_start("wind"))
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(start)
        row.addWidget(start_wind)
        row.addStretch(1)
        root.addLayout(row)
        root.addSpacing(26)

        benefits = QHBoxLayout()
        benefits.setSpacing(14)
        for icon, title, text in BENEFITS:
            frame, layout = make_card("card")
            layout.addWidget(self._icon(icon))
            layout.addWidget(make_label(title, "cardTitle"))
            layout.addWidget(make_label(text, "cardText"))
            layout.addStretch(1)
            benefits.addWidget(frame, 1)
        root.addLayout(benefits)
        root.addSpacing(26)

        root.addWidget(make_label("What you can size", "sectionTitle", wrap=False))
        root.addSpacing(10)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        for i, (icon, title, text, available) in enumerate(TECHNOLOGIES):
            frame, layout = make_card("cardActive" if available else "cardDim")
            top = QHBoxLayout()
            top.addWidget(IconTile(icon))
            top.addStretch(1)
            top.addWidget(make_pill("Available" if available else "Planned", available))
            layout.addLayout(top)
            layout.addWidget(make_label(title, "cardTitle"))
            layout.addWidget(make_label(text, "cardText"))
            layout.addStretch(1)
            grid.addWidget(frame, i // 2, i % 2)
        root.addLayout(grid)
        root.addSpacing(18)
        root.addWidget(make_label(
            "For preliminary and educational use. Results are not a substitute for detailed "
            "engineering design.", "hint"))
        root.addStretch(1)

    @staticmethod
    def _icon(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("cardIcon")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedSize(40, 40)
        return label
