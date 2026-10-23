"""Home screen: what RESize is for, what it can size today and what is coming."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from resize_energy.gui.hero import HeroArt
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
    ("biomass", "Biomass", "Boiler, ORC cogeneration or biogas: plant size, fuel supply, digester.", True),
    ("hydrogen", "Green hydrogen", "PEM electrolyser fed by PV, wind and/or grid: hours, cost and carbon of hydrogen.", True),
]


class HomePage(StepPage):
    """Landing page. ``on_start("pv" | "wind" | "biomass" | "hydrogen" | "compare")`` is called when the user starts a project."""

    show_header = False

    def __init__(self, on_start: Callable[[str], None]) -> None:
        super().__init__()
        self.setTitle("Home")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        text = QVBoxLayout()
        text.setSpacing(0)
        text.addWidget(make_label("RENEWABLE ENERGY SIZING TUTOR", "overline", wrap=False))
        text.addSpacing(6)
        text.addWidget(make_label("Size renewable energy systems.\nStep by step, with the why.",
                                  "headline"))
        text.addSpacing(10)
        text.addWidget(make_label(
            "RESize takes you from site data to a sized plant. It is built for MSc students in "
            "renewable energy and for engineers doing a first-pass design: at each step you see "
            "the formula, the assumptions and your own numbers.", "lead"))
        text.addSpacing(16)

        start = QPushButton("Start a photovoltaic project  →")
        start.setProperty("variant", "primary")
        start.setCursor(Qt.CursorShape.PointingHandCursor)
        start.clicked.connect(lambda *_: on_start("pv"))
        start_wind = QPushButton("Start a wind project  →")
        start_wind.setCursor(Qt.CursorShape.PointingHandCursor)
        start_wind.clicked.connect(lambda *_: on_start("wind"))
        start_h2 = QPushButton("Start a green hydrogen project  →")
        start_h2.setCursor(Qt.CursorShape.PointingHandCursor)
        start_h2.clicked.connect(lambda *_: on_start("hydrogen"))
        start_bio = QPushButton("Start a biomass project  →")
        start_bio.setCursor(Qt.CursorShape.PointingHandCursor)
        start_bio.clicked.connect(lambda *_: on_start("biomass"))
        compare = QPushButton("Compare technologies  →")
        compare.setToolTip("Photovoltaic and wind side by side: cost of energy, payback, CO2")
        compare.setCursor(Qt.CursorShape.PointingHandCursor)
        compare.clicked.connect(lambda *_: on_start("compare"))
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(start)
        row.addWidget(start_wind)
        row.addStretch(1)
        text.addLayout(row)
        text.addSpacing(10)
        row2 = QHBoxLayout()
        row2.setSpacing(12)
        row2.addWidget(start_bio)
        row2.addWidget(start_h2)
        row2.addStretch(1)
        text.addLayout(row2)
        text.addSpacing(10)
        row3 = QHBoxLayout()
        row3.addWidget(compare)
        row3.addStretch(1)
        text.addLayout(row3)

        top = QHBoxLayout()
        top.setSpacing(28)
        top.addLayout(text, 1)
        top.addWidget(HeroArt(), 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(top)
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
