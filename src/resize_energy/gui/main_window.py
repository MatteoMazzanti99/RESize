"""Main window: left navigation, page header, the current step and the Back / Next buttons.

It hosts one flow of steps per technology (photovoltaic, wind, biomass, hydrogen, comparison); the home page starts one.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from resize_energy.gui.biomass_wizard import (
    BIOMASS_STEP_NAMES,
    BiomassDemandPage,
    BiomassFuelPage,
    BiomassPlantPage,
    BiomassResultsPage,
)
from resize_energy.gui.compare_wizard import (
    COMPARE_STEP_NAMES,
    CompareCostPage,
    ComparePlantPage,
    CompareResultsPage,
    CompareSelection,
    CompareSitePage,
)
from resize_energy.gui.home import HomePage
from resize_energy.gui.hydrogen_wizard import (
    HYDROGEN_STEP_NAMES,
    HydrogenCostPage,
    HydrogenGoalPage,
    HydrogenPlantPage,
    HydrogenResultsPage,
    HydrogenSitePage,
)
from resize_energy.gui.widgets import Sidebar, StepPage, make_label
from resize_energy.gui.wind_wizard import (
    WIND_STEP_NAMES,
    WindLoadPage,
    WindResultsPage,
    WindSitePage,
    WindTurbinePage,
)
from resize_energy.gui.wizard import (
    STEP_NAMES,
    ComponentsPage,
    LoadPage,
    ResultsPage,
    SitePage,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RESize - renewable energy sizing tutor")
        self.setMinimumSize(1040, 700)
        self.resize(1240, 820)

        self.home = HomePage(self._start, self._start_compare)
        self.site = SitePage()
        self.load = LoadPage(self.site)
        self.comp = ComponentsPage()
        self.results = ResultsPage(self.site, self.load, self.comp)
        self.wind_site = WindSitePage()
        self.wind_load = WindLoadPage()
        self.wind_turbine = WindTurbinePage()
        self.wind_results = WindResultsPage(self.wind_site, self.wind_load, self.wind_turbine)

        self.bio_demand = BiomassDemandPage()
        self.bio_fuel = BiomassFuelPage(self.bio_demand)
        self.bio_plant = BiomassPlantPage(self.bio_demand)
        self.bio_results = BiomassResultsPage(self.bio_demand, self.bio_fuel, self.bio_plant)
        self.h2_goal = HydrogenGoalPage()
        self.h2_site = HydrogenSitePage(self.h2_goal)
        self.h2_plant = HydrogenPlantPage(self.h2_goal)
        self.h2_costs = HydrogenCostPage()
        self.h2_results = HydrogenResultsPage(self.h2_goal, self.h2_site, self.h2_plant,
                                              self.h2_costs)
        self.cmp_selection = CompareSelection()
        self.cmp_site = CompareSitePage(self.cmp_selection)
        self.cmp_plant = ComparePlantPage(self.cmp_site, self.cmp_selection)
        self.cmp_costs = CompareCostPage(self.cmp_selection)
        self.cmp_results = CompareResultsPage(self.cmp_site, self.cmp_plant, self.cmp_costs,
                                              self.cmp_selection)

        self.flows: dict[str, tuple[list[str], list[StepPage]]] = {
            "pv": (STEP_NAMES, [self.site, self.load, self.comp, self.results]),
            "wind": (WIND_STEP_NAMES, [self.wind_site, self.wind_load, self.wind_turbine,
                                       self.wind_results]),
            "biomass": (BIOMASS_STEP_NAMES, [self.bio_demand, self.bio_fuel, self.bio_plant,
                                             self.bio_results]),
            "hydrogen": (HYDROGEN_STEP_NAMES, [self.h2_goal, self.h2_site, self.h2_plant,
                                               self.h2_costs, self.h2_results]),
            "compare": (COMPARE_STEP_NAMES, [self.cmp_site, self.cmp_plant, self.cmp_costs,
                                             self.cmp_results]),
        }
        self.tech = "pv"
        self.pages: list[StepPage] = [self.home, *self.flows["pv"][1]]
        self.index = 0

        self.sidebar = Sidebar(STEP_NAMES)
        self.header_title = make_label("", "pageTitle", wrap=False)
        self.header_subtitle = make_label("", "pageSubtitle")

        self.stack = QStackedWidget()
        self._scroll_of: dict[int, QScrollArea] = {}
        for page in [self.home, *(p for _, pages in self.flows.values() for p in pages)]:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(page)
            scroll.setViewportMargins(0, 0, 22, 0)  # air between content and scroll bar
            self.stack.addWidget(scroll)
            self._scroll_of[id(page)] = scroll

        self.back_button = QPushButton("←  Back")
        self.back_button.setProperty("variant", "ghost")
        self.back_button.clicked.connect(self._back)
        self.next_button = QPushButton("Next  →")
        self.next_button.setProperty("variant", "primary")
        self.next_button.clicked.connect(self._next)
        self.restart_button = QPushButton("Start over")
        self.restart_button.setProperty("variant", "ghost")
        self.restart_button.clicked.connect(self._restart)

        footer = QHBoxLayout()
        footer.addWidget(self.back_button)
        footer.addStretch(1)
        footer.addWidget(self.restart_button)
        footer.addWidget(self.next_button)

        right = QWidget()
        column = QVBoxLayout(right)
        column.setContentsMargins(36, 28, 36, 20)
        column.setSpacing(0)
        column.addWidget(self.header_title)
        column.addWidget(self.header_subtitle)
        column.addSpacing(16)
        column.addWidget(self.stack, 1)
        column.addSpacing(12)
        column.addLayout(footer)

        central = QWidget()
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self.sidebar)
        row.addWidget(right, 1)
        self.setCentralWidget(central)
        self._show(0)

    # --- navigation ---------------------------------------------------------------
    def _start(self, tech: str = "pv") -> None:
        """Open the first step of the ``tech`` flow ("pv", "wind", "biomass", "hydrogen" or "compare")."""
        if tech not in self.flows:
            tech = "pv"
        self.tech = tech
        names, pages = self.flows[tech]
        self.pages = [self.home, *pages]
        self.sidebar.set_steps(names)
        self._go(1)

    def _start_compare(self, techs: list[str]) -> None:
        """Open the comparison of the technologies dropped in the Compare zone."""
        self.cmp_selection.techs = tuple(techs)
        self._start("compare")

    def _back(self) -> None:
        self._go(self.index - 1)

    def _restart(self) -> None:
        self._go(0)

    def _next(self) -> None:
        if self.pages[self.index].validatePage():
            self._go(self.index + 1)

    def _go(self, index: int) -> None:
        if not 0 <= index < len(self.pages):
            return
        forward = index > self.index
        if forward:
            self.pages[index].initializePage()
        self._show(index)

    def _fade_in(self, widget: QWidget) -> None:
        """Short fade when a step appears. The effect is removed at the end (it costs speed)."""
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda w=widget: w.setGraphicsEffect(None))
        self._fade = anim  # keep a reference while it runs
        anim.start()

    def _show(self, index: int) -> None:
        self.index = index
        page = self.pages[index]
        self.stack.setCurrentWidget(self._scroll_of[id(page)])
        self._fade_in(self._scroll_of[id(page)])
        self.sidebar.set_current(index - 1)
        self.header_title.setVisible(page.show_header)
        self.header_subtitle.setVisible(page.show_header)
        self.header_title.setText(page.title())
        self.header_subtitle.setText(page.subTitle())
        last = index == len(self.pages) - 1
        home = index == 0
        self.back_button.setVisible(not home)
        self.next_button.setVisible(not home and not last)
        self.restart_button.setVisible(last)
