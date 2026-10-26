"""Home screen: what RESize is for, what it can size today and what is coming."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout

from resize_energy.gui.compare_zone import CompareZone, TechCard
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
    ("battery", "Battery storage", "Store the surplus of your PV or wind plant: self-sufficiency, cycles, payback and the best size.", True),
    ("solar", "Solar thermal", "Collectors and tank for hot water, with optional adsorption cooling: solar fraction, area, payback.", True),
    ("hydro", "Hydropower", "Run-of-river plant: flow-duration curve, penstock, turbine type, yearly energy and cost.", True),
    ("geothermal", "Geothermal", "Hot water from the ground for a heat network or a power plant: wells, pumping, net power.", True),
]
# technologies that make energy and can be dragged into the Compare zone
COMPARABLE: tuple[str, ...] = ("pv", "wind", "biomass", "hydrogen")


class HomePage(StepPage):
    """Landing page. Click a technology card to start its project (``on_start(key)``) or drag
    cards into the Compare zone and press Compare (``on_compare([keys])``)."""

    show_header = False

    def _fit_hero(self) -> None:
        """The illustration may open down to the bottom edge of the Compare box, no further."""
        if not hasattr(self, "hero") or not hasattr(self, "zone"):
            return
        top = self.hero.mapTo(self, self.hero.rect().topLeft()).y()
        bottom = self.zone.mapTo(self, self.zone.rect().bottomLeft()).y()
        self.hero.set_limit(bottom - top)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._fit_hero)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._fit_hero)

    def __init__(self, on_start: Callable[[str], None],
                 on_compare: Callable[[list[str]], None]) -> None:
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

        self.zone = CompareZone(COMPARABLE, on_compare)
        text.addWidget(self.zone)

        top = QHBoxLayout()
        top.setSpacing(28)
        top.addLayout(text, 1)
        self.hero = HeroArt()
        top.addWidget(self.hero, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(top)
        root.addSpacing(26)

        root.addWidget(make_label("What you can size  ·  click to start, drag the generating ones to compare",
                                  "sectionTitle", wrap=False))
        root.addSpacing(10)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        for i, (key, title, text, available) in enumerate(TECHNOLOGIES):
            frame, layout = make_card(
                "cardActive" if available else "cardDim",
                TechCard(key, on_start, draggable=available and key in COMPARABLE))
            frame.setToolTip("Click to start a project, or drag into Compare"
                         if key in COMPARABLE else "Click to start a project")
            top = QHBoxLayout()
            top.addWidget(IconTile(key))
            top.addStretch(1)
            top.addWidget(make_pill("Available" if available else "Planned", available))
            layout.addLayout(top)
            layout.addWidget(make_label(title, "cardTitle"))
            layout.addWidget(make_label(text, "cardText"))
            layout.addStretch(1)
            grid.addWidget(frame, i // 2, i % 2)
        root.addLayout(grid)
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
