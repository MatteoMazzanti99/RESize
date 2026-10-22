"""Step-by-step PV sizing wizard (PySide6)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from resize_energy.core.pv_design import (
    InverterSpec,
    ModuleSpec,
    PVDesign,
    PVInputs,
    size_pv_system,
)
from resize_energy.core.pvgis import PVGISError, fetch_pvcalc
from resize_energy.gui.home import HomePage
from resize_energy.gui.numparse import format_number, parse_in_range
from resize_energy.gui.theme import COLORS, SCREEN_DOC_CSS
from resize_energy.gui.tutor_panel import TutorDialog
from resize_energy.gui.why import WhyButton
from resize_energy.gui.widgets import Sidebar, StepPage, make_label
from resize_energy.report.html_report import build_pv_report
from resize_energy.tutor.checker import Finding, check_pv_design
from resize_energy.tutor.context import build_project_context
from resize_energy.tutor.explanations import EXPLANATIONS, TOPIC_ORDER
from resize_energy.tutor.why_html import explanation_html
from resize_energy.tutor.worked import worked_example


class NumberField(QWidget):
    """Free-text numeric input: type the value by hand, with a point or a comma."""

    def __init__(
        self,
        value: float,
        lo: float,
        hi: float,
        decimals: int = 2,
        unit: str = "",
        why_key: str | None = None,
    ):
        super().__init__()
        self.lo, self.hi, self.decimals = lo, hi, decimals
        self.edit = QLineEdit(format_number(value, decimals))
        self.edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.edit.setMaximumWidth(130)
        self.edit.editingFinished.connect(self._mark)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit)
        if unit:
            layout.addWidget(QLabel(unit))
        if why_key:
            layout.addWidget(WhyButton(why_key))
        layout.addStretch(1)

    def value(self) -> float:
        """Current value; raises ValueError (readable message) if invalid or out of range."""
        return parse_in_range(self.edit.text(), self.lo, self.hi)

    def set_value(self, value: float) -> None:
        self.edit.setText(format_number(value, self.decimals))
        self._mark()

    def _mark(self) -> None:
        try:
            self.value()
        except ValueError as exc:
            self.edit.setStyleSheet(f"border: 1px solid {COLORS['error']};")
            self.edit.setToolTip(str(exc))
        else:
            self.edit.setStyleSheet("")
            self.edit.setToolTip("")


def first_error(items: list[tuple[str, NumberField]]) -> str | None:
    """First invalid field as 'Label: message', or None if all values are valid."""
    for label, field in items:
        try:
            field.value()
        except ValueError as exc:
            field.edit.setFocus()
            return f"{label}: {exc}"
    return None


def _hint(text: str) -> QLabel:
    return make_label(text, "hint")


class SitePage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("1. Site and solar resource")
        self.setSubTitle("The yearly in-plane irradiation H sets how much energy each kWp yields.")

        self.lat = NumberField(45.07, -90, 90, 4, "deg N")
        self.lon = NumberField(7.69, -180, 180, 4, "deg E")
        self.tilt = NumberField(30, 0, 90, 0, "deg")
        self.azimuth = NumberField(0, -180, 180, 0, "deg")
        self.loss = NumberField(14, 0, 50, 1, "%")
        self.irr = NumberField(1500, 100, 3500, 0, "kWh/m2 per year", "pv.irradiation")
        self._implied_pr: float | None = None

        self.status = QLabel("")
        self.status.setWordWrap(True)
        fetch = QPushButton("Get irradiation from PVGIS")
        fetch.clicked.connect(self._fetch)

        form = QFormLayout()
        form.addRow("Latitude (north positive)", self.lat)
        form.addRow("Longitude (east positive)", self.lon)
        form.addRow("Tilt of the modules", self.tilt)
        form.addRow("Azimuth (0 = south, 90 = west, -90 = east)", self.azimuth)
        form.addRow("System losses assumed by PVGIS", self.loss)

        manual = QFormLayout()
        manual.addRow("Annual in-plane irradiation H", self.irr)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(fetch)
        layout.addWidget(self.status)
        layout.addWidget(_hint(
            "If you are offline, or already have a value from another source, type the annual "
            "in-plane irradiation by hand below."))
        layout.addLayout(manual)

    def implied_pr(self) -> float | None:
        return self._implied_pr

    def _query_items(self) -> list[tuple[str, NumberField]]:
        return [("Latitude", self.lat), ("Longitude", self.lon), ("Tilt", self.tilt),
                ("Azimuth", self.azimuth), ("System losses", self.loss)]

    def _fetch(self) -> None:
        error = first_error(self._query_items())
        if error:
            self.status.setText(error)
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = fetch_pvcalc(
                self.lat.value(), self.lon.value(), self.tilt.value(),
                self.azimuth.value(), self.loss.value(),
            )
        except (PVGISError, ValueError) as exc:
            self.status.setText(f"Could not get PVGIS data: {exc}\nYou can type H by hand below.")
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.irr.set_value(result.annual_irradiation_kwh_m2)
        self._implied_pr = result.implied_performance_ratio
        self.status.setText(
            f"PVGIS: H = {result.annual_irradiation_kwh_m2:,.0f} kWh/m2 per year, "
            f"yield {result.annual_yield_kwh_per_kwp:,.0f} kWh/kWp "
            f"(implied performance ratio {result.implied_performance_ratio:.2f})."
        )

    def validatePage(self) -> bool:
        error = first_error(self._query_items() + [("Annual irradiation", self.irr)])
        if error:
            QMessageBox.warning(self, "Check the value", error)
            return False
        return True


class LoadPage(StepPage):
    def __init__(self, site: SitePage) -> None:
        super().__init__()
        self.site = site
        self.setTitle("2. Electricity demand")
        self.setSubTitle("How much energy must the plant supply, and how well does it perform?")
        self.demand = NumberField(4500, 1, 1e9, 0, "kWh per year")
        self.coverage = NumberField(100, 1, 100, 0, "%", "pv.required_peak_power")
        self.pr = NumberField(0.80, 0.5, 0.95, 2, "", "pv.performance_ratio")

        form = QFormLayout()
        form.addRow("Annual electricity demand", self.demand)
        form.addRow("Share of the demand to cover with PV", self.coverage)
        form.addRow("Performance ratio (PR)", self.pr)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(_hint(
            "PR groups all losses (temperature, soiling, wiring, inverter, mismatch). "
            "Typical values are 0.75-0.85. A 100% target does not account for the hour-by-hour "
            "match between production and consumption: that needs a storage/self-consumption "
            "analysis."))

    def initializePage(self) -> None:
        implied = self.site.implied_pr()
        if implied and 0.5 <= implied <= 0.95:
            self.pr.set_value(round(implied, 2))

    def validatePage(self) -> bool:
        error = first_error([("Annual demand", self.demand), ("Coverage", self.coverage),
                             ("Performance ratio", self.pr)])
        if error:
            QMessageBox.warning(self, "Check the value", error)
            return False
        return True


class ComponentsPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("3. Module and inverter")
        self.setSubTitle("Enter the datasheet values (defaults are generic placeholders).")
        m, i = ModuleSpec(), InverterSpec()

        def nf(
            value: float, lo: float, hi: float, dec: int, unit: str, why: str | None = None
        ) -> NumberField:
            return NumberField(value, lo, hi, dec, unit, why)

        self.t_min = nf(-10, -60, 25, 0, "degC", "pv.max_modules_per_string")
        self.t_max = nf(70, 25, 120, 0, "degC", "pv.min_modules_per_string")
        self.mod = {
            "p": nf(m.p_stc_w, 50, 1000, 0, "Wp"),
            "voc": nf(m.voc_v, 5, 100, 2, "V", "pv.max_modules_per_string"),
            "vmp": nf(m.vmp_v, 5, 100, 2, "V", "pv.min_modules_per_string"),
            "isc": nf(m.isc_a, 1, 30, 2, "A", "pv.string_layout"),
            "bvoc": nf(m.temp_coeff_voc_pct_per_c, -1, 0, 2, "%/degC", "pv.temperature_extremes"),
            "bvmp": nf(m.temp_coeff_vmp_pct_per_c, -1, 0, 2, "%/degC", "pv.temperature_extremes"),
            "area": nf(m.area_m2, 0.5, 5, 2, "m2"),
        }
        self.inv = {
            "p": nf(i.p_ac_kw, 0.5, 5000, 1, "kW", "pv.dc_ac_ratio"),
            "vmax": nf(i.vdc_max_v, 100, 1500, 0, "V", "pv.max_modules_per_string"),
            "vmin": nf(i.mppt_vmin_v, 20, 1000, 0, "V", "pv.min_modules_per_string"),
            "vmpptmax": nf(i.mppt_vmax_v, 100, 1500, 0, "V", "pv.mppt_window_cold"),
            "imax": nf(i.imax_per_mppt_a, 5, 100, 1, "A", "pv.string_layout"),
            "n": nf(i.n_mppt, 1, 12, 0, ""),
        }
        mod_labels = {
            "p": "Rated power", "voc": "Open-circuit voltage Voc", "vmp": "Voltage at max power Vmp",
            "isc": "Short-circuit current Isc", "bvoc": "Temp. coefficient of Voc",
            "bvmp": "Temp. coefficient of Vmp", "area": "Module area",
        }
        inv_labels = {
            "p": "Rated AC power", "vmax": "Maximum DC voltage", "vmin": "MPPT minimum voltage",
            "vmpptmax": "MPPT maximum voltage", "imax": "Maximum current per MPPT",
            "n": "Number of MPPT inputs",
        }
        self._labels: list[tuple[str, NumberField]] = [
            ("Minimum ambient temperature", self.t_min),
            ("Maximum cell temperature", self.t_max),
        ]

        site = QGroupBox("Climate extremes")
        sf = QFormLayout(site)
        sf.addRow("Minimum ambient temperature", self.t_min)
        sf.addRow("Maximum cell temperature", self.t_max)

        mod_box = QGroupBox("PV module (STC)")
        mf = QFormLayout(mod_box)
        for key, label in mod_labels.items():
            mf.addRow(label, self.mod[key])
            self._labels.append((f"Module: {label}", self.mod[key]))

        inv_box = QGroupBox("Inverter")
        inf = QFormLayout(inv_box)
        for key, label in inv_labels.items():
            inf.addRow(label, self.inv[key])
            self._labels.append((f"Inverter: {label}", self.inv[key]))

        row = QHBoxLayout()
        row.addWidget(mod_box)
        row.addWidget(inv_box)
        layout = QVBoxLayout(self)
        layout.addWidget(site)
        layout.addLayout(row)
        layout.addWidget(_hint(
            "Vmp temperature coefficients are often not listed on the datasheet: use about "
            "-0.30 to -0.40 %/degC if the Vmp one is missing."))

    def specs(self) -> tuple[ModuleSpec, InverterSpec, float, float]:
        mod = {k: f.value() for k, f in self.mod.items()}
        inv = {k: f.value() for k, f in self.inv.items()}
        module = ModuleSpec(
            name="User module", p_stc_w=mod["p"], voc_v=mod["voc"], vmp_v=mod["vmp"],
            isc_a=mod["isc"], imp_a=0.94 * mod["isc"],
            temp_coeff_voc_pct_per_c=mod["bvoc"], temp_coeff_vmp_pct_per_c=mod["bvmp"],
            area_m2=mod["area"],
        )
        inverter = InverterSpec(
            name="User inverter", p_ac_kw=inv["p"], vdc_max_v=inv["vmax"],
            mppt_vmin_v=inv["vmin"], mppt_vmax_v=inv["vmpptmax"],
            imax_per_mppt_a=inv["imax"], n_mppt=max(1, round(inv["n"])),
        )
        return module, inverter, self.t_min.value(), self.t_max.value()

    def validatePage(self) -> bool:
        error = first_error(self._labels)
        if error:
            QMessageBox.warning(self, "Check the value", error)
            return False
        return True


class ResultsPage(StepPage):
    def __init__(self, site: SitePage, load: LoadPage, comp: ComponentsPage) -> None:
        super().__init__()
        self.site, self.load, self.comp = site, load, comp
        self.setMinimumHeight(560)
        self.setTitle("4. Results and design checks")
        self.setSubTitle("Pick a step on the right to see why it is done and the numbers used.")
        self.browser = QTextBrowser()
        self.html = ""  # light version, used for the PDF
        self.html_screen = ""  # dark version, shown in the window
        self._inputs: PVInputs | None = None
        self._design: PVDesign | None = None
        self._findings: list[Finding] = []
        self._tutor: TutorDialog | None = None

        self.topics = QListWidget()
        for key in TOPIC_ORDER:
            self.topics.addItem(EXPLANATIONS[key]["title"])
        self.topics.currentRowChanged.connect(self._show_topic)
        self.detail = QTextBrowser()
        self.detail.document().setDefaultStyleSheet(SCREEN_DOC_CSS)
        self.browser.document().setDefaultStyleSheet(SCREEN_DOC_CSS)
        self.detail.setHtml("<p><i>Why?</i> Select a step above to see its formula, the "
                            "reasoning, and your own numbers substituted in.</p>")
        why_panel = QWidget()
        why_layout = QVBoxLayout(why_panel)
        why_layout.setContentsMargins(0, 0, 0, 0)
        why_layout.addWidget(make_label("Why?", "sectionTitle", wrap=False))
        why_layout.addWidget(self.topics, 1)
        why_layout.addWidget(self.detail, 2)
        ask_step = QPushButton("Ask the tutor about this step...")
        ask_step.clicked.connect(self._ask_about_step)
        why_layout.addWidget(ask_step)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.browser)
        splitter.addWidget(why_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        export = QPushButton("Export PDF report...")
        export.setProperty("variant", "primary")
        export.clicked.connect(self._export_pdf)
        ask = QPushButton("Ask the AI tutor...")
        ask.setToolTip("Chat about your design (optional: needs an API key or a local model)")
        ask.clicked.connect(self._open_tutor)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(ask)
        buttons.addWidget(export)
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)
        layout.addLayout(buttons)

    def _open_tutor(self, question: str | None = None) -> None:
        if self._inputs is None or self._design is None:
            QMessageBox.information(self, "RESize", "There is no design to discuss yet.")
            return
        context = build_project_context(self._inputs, self._design, self._findings)
        if self._tutor is not None:
            self._tutor.close()
        self._tutor = TutorDialog(context, self)
        if isinstance(question, str) and question:
            self._tutor.set_question(question)
        self._tutor.show()

    def _ask_about_step(self) -> None:
        row = self.topics.currentRow()
        if row < 0 or row >= len(TOPIC_ORDER):
            QMessageBox.information(self, "RESize", "Select a step in the list first.")
            return
        title = EXPLANATIONS[TOPIC_ORDER[row]]["title"]
        self._open_tutor(f"Explain this step for my project and check my numbers: {title}")

    def _show_topic(self, row: int) -> None:
        if row < 0 or row >= len(TOPIC_ORDER):
            return
        key = TOPIC_ORDER[row]
        worked = None
        if self._inputs is not None and self._design is not None:
            worked = worked_example(key, self._inputs, self._design)
        self.detail.setHtml(explanation_html(key, worked, heading=False))

    def initializePage(self) -> None:
        try:
            module, inverter, t_min, t_max = self.comp.specs()
            inputs = PVInputs(
                annual_demand_kwh=self.load.demand.value(),
                annual_irradiation_kwh_m2=self.site.irr.value(),
                coverage=self.load.coverage.value() / 100.0,
                performance_ratio=self.load.pr.value(),
                t_min_c=t_min, t_cell_max_c=t_max, module=module, inverter=inverter,
            )
            design = size_pv_system(inputs)
        except ValueError as exc:
            self.html = self.html_screen = ""
            self._inputs = self._design = None
            self._findings = []
            self.browser.setHtml(f"<p><b>Cannot compute the design:</b> {exc}</p>")
            return
        self._inputs, self._design = inputs, design
        findings = check_pv_design(inputs, design)
        self._findings = findings
        note = (
            f"Site: lat {self.site.lat.value():.4f}, lon {self.site.lon.value():.4f}, "
            f"tilt {self.site.tilt.value():.0f} deg, azimuth {self.site.azimuth.value():.0f} deg."
        )
        self.html = build_pv_report(inputs, design, findings, site_note=note, theme="light")
        self.html_screen = build_pv_report(
            inputs, design, findings, site_note=note, theme="dark")
        self.browser.setHtml(self.html_screen)
        row = self.topics.currentRow()
        if row >= 0:
            self._show_topic(row)  # refresh the open topic with the new numbers

    def _export_pdf(self) -> None:
        if not self.html:
            QMessageBox.information(self, "RESize", "There is no report to export yet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save report", "RESize_PV_report.pdf", "PDF files (*.pdf)"
        )
        if not path:
            return
        doc = QTextDocument()
        doc.setHtml(self.html)
        writer = QPdfWriter(path)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        doc.print_(writer)
        QMessageBox.information(self, "RESize", f"Report saved to:\n{path}")


STEP_NAMES = ["Site and solar resource", "Electricity demand", "Module and inverter",
              "Results and checks"]


class MainWindow(QMainWindow):
    """Left navigation, page header, the current step and the Back / Next buttons."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RESize - renewable energy sizing tutor")
        self.setMinimumSize(1040, 700)
        self.resize(1240, 820)

        self.site = SitePage()
        self.load = LoadPage(self.site)
        self.comp = ComponentsPage()
        self.results = ResultsPage(self.site, self.load, self.comp)
        self.home = HomePage(self._start)
        self.pages: list[StepPage] = [self.home, self.site, self.load, self.comp, self.results]
        self.index = 0

        self.sidebar = Sidebar(STEP_NAMES)
        self.header_title = make_label("", "pageTitle", wrap=False)
        self.header_subtitle = make_label("", "pageSubtitle")

        self.stack = QStackedWidget()
        for page in self.pages:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(page)
            self.stack.addWidget(scroll)

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
    def _start(self) -> None:
        self._go(1)

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

    def _show(self, index: int) -> None:
        self.index = index
        page = self.pages[index]
        self.stack.setCurrentIndex(index)
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
