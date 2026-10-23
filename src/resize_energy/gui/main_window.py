"""Main window: left navigation, page header, the current step and the Back / Next buttons.

It hosts one flow of steps per technology (photovoltaic, wind, biomass, hydrogen, battery, comparison); the home page starts one.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from resize_energy.core import project_file as pf
from resize_energy.gui import country, project_io
from resize_energy.gui.battery_wizard import (
    BATTERY_STEP_NAMES,
    BatteryCostPage,
    BatteryGoalPage,
    BatteryPage,
    BatteryResultsPage,
    BatterySitePage,
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
from resize_energy.gui.plant_cost_page import PlantCostPage
from resize_energy.gui.solar_wizard import (
    SOLAR_STEP_NAMES,
    SolarCollectorPage,
    SolarCostPage,
    SolarLoadPage,
    SolarResultsPage,
    SolarSitePage,
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

TECH_LABELS = {"pv": "PHOTOVOLTAIC", "wind": "WIND", "biomass": "BIOMASS",
               "hydrogen": "GREEN HYDROGEN", "battery": "BATTERY STORAGE",
               "solar": "SOLAR THERMAL", "compare": "COMPARISON"}


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
        self.pv_costs = PlantCostPage("pv", 4)
        self.results = ResultsPage(self.site, self.load, self.comp, self.pv_costs)
        self.wind_site = WindSitePage()
        self.wind_load = WindLoadPage()
        self.wind_turbine = WindTurbinePage()
        self.wind_costs = PlantCostPage("wind", 4)
        self.wind_results = WindResultsPage(self.wind_site, self.wind_load, self.wind_turbine,
                                            self.wind_costs)

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
        self.bat_goal = BatteryGoalPage()
        self.bat_site = BatterySitePage(self.bat_goal)
        self.bat_battery = BatteryPage()
        self.bat_costs = BatteryCostPage()
        self.bat_results = BatteryResultsPage(self.bat_goal, self.bat_site, self.bat_battery,
                                              self.bat_costs)
        self.sol_load = SolarLoadPage()
        self.sol_site = SolarSitePage()
        self.sol_coll = SolarCollectorPage(self.sol_load)
        self.sol_costs = SolarCostPage(self.sol_load)
        self.sol_results = SolarResultsPage(self.sol_load, self.sol_site, self.sol_coll,
                                            self.sol_costs)
        self.cmp_selection = CompareSelection()
        self.cmp_site = CompareSitePage(self.cmp_selection)
        self.cmp_plant = ComparePlantPage(self.cmp_site, self.cmp_selection)
        self.cmp_costs = CompareCostPage(self.cmp_selection)
        self.cmp_results = CompareResultsPage(self.cmp_site, self.cmp_plant, self.cmp_costs,
                                              self.cmp_selection)

        self.flows: dict[str, tuple[list[str], list[StepPage]]] = {
            "pv": (STEP_NAMES, [self.site, self.load, self.comp, self.pv_costs,
                                self.results]),
            "wind": (WIND_STEP_NAMES, [self.wind_site, self.wind_load, self.wind_turbine,
                                       self.wind_costs, self.wind_results]),
            "biomass": (BIOMASS_STEP_NAMES, [self.bio_demand, self.bio_fuel, self.bio_plant,
                                             self.bio_results]),
            "hydrogen": (HYDROGEN_STEP_NAMES, [self.h2_goal, self.h2_site, self.h2_plant,
                                               self.h2_costs, self.h2_results]),
            "battery": (BATTERY_STEP_NAMES, [self.bat_goal, self.bat_site, self.bat_battery,
                                             self.bat_costs, self.bat_results]),
            "solar": (SOLAR_STEP_NAMES, [self.sol_load, self.sol_site, self.sol_coll,
                                         self.sol_costs, self.sol_results]),
            "compare": (COMPARE_STEP_NAMES, [self.cmp_site, self.cmp_plant, self.cmp_costs,
                                             self.cmp_results]),
        }
        self.tech = "pv"
        self.pages: list[StepPage] = [self.home, *self.flows["pv"][1]]
        self.index = 0

        self.sidebar = Sidebar(STEP_NAMES)
        self.header_step = make_label("", "overline", wrap=False)
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
        self.save_button = QPushButton("Save project")
        self.save_button.setProperty("variant", "ghost")
        self.save_button.setToolTip("Save the values of every step to a .resize file (Ctrl+S)")
        self.save_button.clicked.connect(self.save_project)
        self.open_button = QPushButton("Open a saved project…")
        self.open_button.setProperty("variant", "ghost")
        self.open_button.clicked.connect(self.open_project)
        self.project_path: Path | None = None
        self._build_menu()

        footer = QHBoxLayout()
        footer.addWidget(self.back_button)
        footer.addWidget(self.open_button)
        footer.addWidget(self.save_button)
        footer.addStretch(1)
        footer.addWidget(self.restart_button)
        footer.addWidget(self.next_button)

        right = QWidget()
        column = QVBoxLayout(right)
        column.setContentsMargins(36, 28, 36, 20)
        column.setSpacing(0)
        column.addWidget(self.header_step)
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
        """Open the first step of the ``tech`` flow ("pv", "wind", "biomass", "hydrogen", "battery", "solar" or "compare")."""
        if tech not in self.flows:
            tech = "pv"
        self.tech = tech
        names, pages = self.flows[tech]
        for page in pages:
            if hasattr(page, "_version_a"):
                page._version_a = None      # a new project: no kept version
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
        self.header_step.setVisible(page.show_header)
        self.header_title.setVisible(page.show_header)
        self.header_subtitle.setVisible(page.show_header)
        total = len(self.pages) - 1
        self.header_step.setText(f"{TECH_LABELS.get(self.tech, '')}  ·  STEP {index} OF {total}")
        self.header_title.setText(page.title())
        self.header_subtitle.setText(page.subTitle())
        last = index == len(self.pages) - 1
        home = index == 0
        self.back_button.setVisible(not home)
        self.next_button.setVisible(not home and not last)
        self.restart_button.setVisible(last)
        self.open_button.setVisible(home)
        self.save_button.setVisible(not home)
        self.save_action.setEnabled(not home)
        self.save_as_action.setEnabled(not home)
        self._update_title()
        self.next_button.setText("See the results  →" if index == len(self.pages) - 2
                                 else "Next  →")

    # --- projects (save and reopen) -------------------------------------------------
    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("&File")
        open_action = QAction("&Open project…", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_project)
        self.save_action = QAction("&Save project", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save_project)
        self.save_as_action = QAction("Save project &as…", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self.save_project_as)
        home_action = QAction("&Home", self)
        home_action.triggered.connect(self._restart)
        for action in (open_action, self.save_action, self.save_as_action):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(home_action)

    def _update_title(self) -> None:
        name = f" - {self.project_path.name}" if self.project_path else ""
        self.setWindowTitle(f"RESize - renewable energy sizing tutor{name}")

    def project_snapshot(self) -> pf.Project:
        """The values of every step of the open flow."""
        flow = self.pages[1:]
        weather = {}
        for i, page in enumerate(flow):
            w = project_io.weather_of(page)
            if w is not None:
                weather[str(i)] = w
        return pf.Project(
            tech=self.tech, pages=[project_io.capture(p) for p in flow],
            compare_techs=self.cmp_selection.techs if self.tech == "compare" else (),
            weather=weather)

    def save_to(self, path: Path) -> None:
        path = path if path.suffix == pf.EXTENSION else path.with_suffix(pf.EXTENSION)
        path.write_text(pf.dumps(self.project_snapshot()), encoding="utf-8")
        self.project_path = path
        self._update_title()

    def open_from(self, path: Path) -> list[str]:
        """Load a project, fill the steps and show the last one. Returns fields not restored."""
        try:
            project = pf.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise pf.ProjectError(f"the file cannot be read ({exc.strerror or exc})") from exc
        except UnicodeDecodeError as exc:
            raise pf.ProjectError("this is not a RESize project file") from exc
        if project.tech == "compare":
            self.cmp_selection.techs = project.compare_techs or self.cmp_selection.techs
        country.forget_choice()    # the file's own prices win over an earlier pick
        self._start(project.tech)
        flow = self.pages[1:]
        problems: list[str] = []
        for i, (page, state) in enumerate(zip(flow, project.pages, strict=False)):
            problems += project_io.restore(page, state, project.weather.get(str(i)))
        self.project_path = path
        for page in flow:       # as if the steps had been walked through
            page.initializePage()
        try:
            self._go(len(self.pages) - 1)
        except Exception as exc:  # noqa: BLE001 - a bad value must not leave the window stuck
            self._go(1)
            problems.append(f"results ({exc})")
        self._update_title()
        return problems

    def save_project(self) -> None:
        if self.index == 0:
            return
        if self.project_path is None:
            self.save_project_as()
            return
        self._save_checked(self.project_path)

    def save_project_as(self) -> None:
        if self.index == 0:
            return
        start = str(self.project_path or Path.home() / pf.default_name(self.tech))
        name, _ = QFileDialog.getSaveFileName(self, "Save project", start,
                                              "RESize project (*.resize)")
        if name:
            self._save_checked(Path(name))

    def _save_checked(self, path: Path) -> None:
        try:
            self.save_to(path)
        except OSError as exc:
            QMessageBox.warning(self, "Could not save", f"{path}\n{exc.strerror or exc}")

    def open_project(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Open project", str(Path.home()),
                                              "RESize project (*.resize);;All files (*)")
        if not name:
            return
        try:
            problems = self.open_from(Path(name))
        except pf.ProjectError as exc:
            QMessageBox.warning(self, "Could not open the project", str(exc))
            return
        if problems:
            QMessageBox.information(
                self, "Project opened",
                "Some values could not be restored and keep their default: "
                + ", ".join(problems[:8]))
