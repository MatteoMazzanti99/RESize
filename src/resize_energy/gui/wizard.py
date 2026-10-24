"""Step-by-step PV sizing wizard (PySide6)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPageSize, QPdfWriter, QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from resize_energy.core.pv_design import (
    InverterSpec,
    ModuleSpec,
    PVInputs,
    size_pv_system,
)
from resize_energy.core.pv_extra import shading_loss
from resize_energy.core.pvgis import PVGISError, fetch_pvcalc
from resize_energy.gui.chart_render import render_chart
from resize_energy.gui.flow_banner import FlowBanner, picture_image
from resize_energy.gui.formula_image import FormulaBrowser, formula_image
from resize_energy.gui.numparse import format_number, parse_in_range
from resize_energy.gui.provenance import insert_before_formulas, provenance_section
from resize_energy.gui.theme import COLORS, SCREEN_DOC_CSS
from resize_energy.gui.tutor_panel import TutorDialog
from resize_energy.gui.why import WhyButton
from resize_energy.gui.widgets import StepPage, make_label
from resize_energy.report.charts import ChartSpec, pv_charts
from resize_energy.report.flow_art import picture_size
from resize_energy.report.html_report import build_pv_report
from resize_energy.tutor.checker import Finding, check_pv_design
from resize_energy.tutor.context import build_project_context
from resize_energy.tutor.explanations import EXPLANATIONS, TOPIC_ORDER
from resize_energy.tutor.why_html import explanation_html
from resize_energy.tutor.worked import worked_example


class ReportBrowser(FormulaBrowser):
    """Shows the report; ``<img src="chart:NAME">`` is answered with the drawn chart."""

    def __init__(self) -> None:
        super().__init__()
        self.images: dict[str, QImage] = {}

    def loadResource(self, rtype, url):
        image = self.images.get(url.toString())
        return image if image is not None else super().loadResource(rtype, url)


class ReportDocument(QTextDocument):
    """Same for the document that is printed to PDF."""

    def __init__(self, images: dict[str, QImage]) -> None:
        super().__init__()
        self.images = images

    def loadResource(self, rtype, url):
        image = self.images.get(url.toString()) or formula_image(url.toString())
        return image if image is not None else super().loadResource(rtype, url)


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
        self.default = value          # what the program proposes
        self.source: str | None = None  # "PVGIS", "NASA POWER"... when fetched, None otherwise
        self.edit = QLineEdit(format_number(value, decimals))
        self.edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.edit.setMaximumWidth(130)
        self.edit.editingFinished.connect(self._mark)
        self.edit.textEdited.connect(self._typed)
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

    def set_value(self, value: float, source: str | None = None) -> None:
        self.edit.setText(format_number(value, self.decimals))
        self.source = source
        self._mark()

    def _typed(self, _text: str) -> None:
        self.source = None            # the user has taken over

    def provenance(self) -> str:
        """"source" name if fetched, "default" if untouched, else "changed"."""
        if self.source:
            return self.source
        try:
            same = abs(self.value() - self.default) <= 10 ** -(self.decimals + 1)
        except ValueError:
            return "changed"
        return "default" if same else "changed"

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
        self.setSubTitle("Where is it? Press the button to get the solar energy of this place from PVGIS, or type your own value: it sets how much each kWp produces.")

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

        fetch_row = QHBoxLayout()
        fetch_row.addWidget(fetch)
        fetch_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addLayout(form)
        layout.addLayout(fetch_row)
        layout.addWidget(self.status)
        layout.addSpacing(8)
        layout.addWidget(_hint(
            "If you are offline, or already have a value from another source, type the annual "
            "in-plane irradiation by hand below."))
        layout.addLayout(manual)
        layout.addStretch(1)

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
        self.irr.set_value(result.annual_irradiation_kwh_m2, "PVGIS")
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
        self.setSubTitle("How much electricity do you use, and what share should the PV cover? The performance ratio says how much of the ideal energy you really get.")
        self.demand = NumberField(4500, 1, 1e9, 0, "kWh per year")
        self.coverage = NumberField(100, 1, 100, 0, "%", "pv.required_peak_power")
        self.pr = NumberField(0.80, 0.5, 0.95, 2, "", "pv.performance_ratio")
        self.obstacle = NumberField(0, 0, 80, 0, "deg above the horizon", "pv.shading")
        self.az_from = NumberField(-60, -180, 180, 0, "deg (0 = south)", "pv.shading")
        self.az_to = NumberField(60, -180, 180, 0, "deg (0 = south)", "pv.shading")

        form = QFormLayout()
        form.addRow("Annual electricity demand", self.demand)
        form.addRow("Share of the demand to cover with PV", self.coverage)
        form.addRow("Performance ratio (PR)", self.pr)
        shade = QGroupBox("Shading by a nearby obstacle (0 degrees = no obstacle)")
        sf = QFormLayout(shade)
        sf.addRow("Height of the obstacle", self.obstacle)
        sf.addRow("From azimuth", self.az_from)
        sf.addRow("To azimuth", self.az_to)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(shade)
        layout.addWidget(_hint(
            "PR groups all losses (temperature, soiling, wiring, inverter, mismatch). "
            "Typical values are 0.75-0.85. A 100% target does not account for the hour-by-hour "
            "match between production and consumption: that needs a storage/self-consumption "
            "analysis."))

    def shading(self) -> float:
        """Share of the yearly energy lost to the obstacle (0 when none is entered)."""
        if self.obstacle.value() <= 0:
            return 0.0
        return shading_loss(self.site.lat.value(), self.obstacle.value(),
                            self.az_from.value(), self.az_to.value())

    def initializePage(self) -> None:
        implied = self.site.implied_pr()
        if implied and 0.5 <= implied <= 0.95:
            self.pr.set_value(round(implied, 2))

    def validatePage(self) -> bool:
        error = first_error([("Annual demand", self.demand), ("Coverage", self.coverage),
                             ("Performance ratio", self.pr), ("Obstacle height", self.obstacle),
                             ("Azimuth from", self.az_from), ("Azimuth to", self.az_to)])
        if error:
            QMessageBox.warning(self, "Check the value", error)
            return False
        if self.az_to.value() < self.az_from.value():
            QMessageBox.warning(self, "Check the value",
                                "The end azimuth must not be before the start azimuth.")
            return False
        return True


class ComponentsPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("3. Module and inverter")
        self.setSubTitle("Choose the module and the inverter. The defaults are generic: use your datasheet values for a real design.")
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


class BaseResultsPage(StepPage):
    """Report on the left, 'Why?' topics on the right, export and tutor buttons.

    A technology fills in :meth:`_compute`, :meth:`_worked` and :meth:`_context`.
    """

    topic_order: tuple[str, ...] = ()
    pdf_name = "RESize_report.pdf"
    has_excel = False          # technologies that can export a workbook set this and _workbook

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(640)
        self.setTitle("4. Results and design checks")
        self.setSubTitle("Your results first, then charts and checks. Use the list on the right to see why each number is what it is.")
        self.browser = ReportBrowser()
        self.banner = FlowBanner()   # energy-flow picture above the report
        self.chart_images: dict[str, QImage] = {}
        self.html = ""  # light version, used for the PDF
        self.html_screen = ""  # dark version, shown in the window
        self._inputs: object | None = None
        self._design: object | None = None
        self._findings: list[Finding] = []
        self._tutor: TutorDialog | None = None
        self._base: tuple[str, str] = ("", "")   # report without the extra sections
        self._version_a: dict | None = None        # kept version: states and key results
        self._explained = ("", "")                 # 'Why did it change?' for this version

        self.topics = QListWidget()
        for key in self.topic_order:
            self.topics.addItem(EXPLANATIONS[key]["title"])
        self.topics.currentRowChanged.connect(self._show_topic)
        self.detail = FormulaBrowser()
        self.detail.document().setDefaultStyleSheet(SCREEN_DOC_CSS)
        self.browser.document().setDefaultStyleSheet(SCREEN_DOC_CSS)
        self.detail.setHtml("<p><i>Why?</i> Select a step above to see its formula, the "
                            "reasoning, and your own numbers substituted in.</p>")
        why_panel = QWidget()
        why_layout = QVBoxLayout(why_panel)
        why_layout.setContentsMargins(14, 0, 0, 0)  # air between report and Why? panel
        why_layout.addWidget(make_label("Why? Understand each step", "sectionTitle", wrap=False))
        why_layout.addWidget(self.topics, 1)
        why_layout.addWidget(self.detail, 2)
        ask_step = QPushButton("Ask the tutor about this step...")
        ask_step.clicked.connect(self._ask_about_step)
        why_layout.addWidget(ask_step)

        self.splitter = splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.browser)
        splitter.addWidget(why_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        export = QPushButton("Save the report as PDF (with charts)...")
        export.setProperty("variant", "primary")
        export.clicked.connect(self._export_pdf)
        ask = QPushButton("Ask the AI tutor...")
        ask.setToolTip("Chat about your design (optional: needs an API key or a local model)")
        ask.clicked.connect(self._open_tutor)
        keep = QPushButton("Keep this version as A")
        keep.setToolTip("Remember these results. Change something in an earlier step, come "
                        "back, and the report compares the two versions.")
        keep.clicked.connect(self._keep_version)
        self.explain_button = QPushButton("Why did it change?")
        self.explain_button.setToolTip("Apply each difference to version A, one at a time, to "
                                       "see what each input did to the results.")
        self.explain_button.clicked.connect(self._explain_version)
        self.explain_button.setEnabled(False)
        buttons = QHBoxLayout()
        buttons.addWidget(keep)
        buttons.addWidget(self.explain_button)
        self.excel_button = QPushButton("Export to Excel (live formulas)...")
        self.excel_button.setToolTip("A workbook where every step is a formula: change an "
                                     "input and watch the results move.")
        self.excel_button.clicked.connect(self._export_excel)
        self.excel_button.setVisible(self.has_excel)
        buttons.addWidget(self.excel_button)
        buttons.addStretch(1)
        buttons.addWidget(ask)
        buttons.addWidget(export)
        layout = QVBoxLayout(self)
        layout.addWidget(make_label(
            "Left: your results, the charts and the design checks (start from 'In short'). "
            "Right: pick a step to see its formula with your own numbers.", "hint"), 0)
        layout.addWidget(self.banner)
        layout.addWidget(splitter, 1)  # the report takes all the spare height
        layout.addLayout(buttons)

    # --- hooks for each technology ----------------------------------------------------
    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        """Return (inputs, design, findings, light report html, dark report html).

        Raises ValueError (readable message) when the numbers cannot be sized.
        """
        raise NotImplementedError

    def _worked(self, key: str) -> str | None:
        raise NotImplementedError

    def _context(self) -> str:
        raise NotImplementedError

    def _charts(self) -> dict[str, ChartSpec]:
        """The charts named in the report (``chart:NAME``)."""
        return {}

    def _flow(self):
        """The energy-flow picture (nodes, flows) of the design, or None. Technologies fill it in."""
        return None

    def _draw_charts(self) -> None:
        self.chart_images = {f"chart:{name}": render_chart(spec)
                             for name, spec in self._charts().items()}
        try:
            picture = self._flow()
        except Exception:  # noqa: BLE001 - a picture must never stop the report
            picture = None
        self.banner.set_picture(picture)
        self._banner_ratio = 0.0
        if picture is not None:
            self.chart_images["chart:flow_banner"] = picture_image(picture)
            w, h = picture_size(picture[0])
            self._banner_ratio = h / w
        self.browser.images = self.chart_images

    # --- shared behaviour ----------------------------------------------------------------
    def _open_tutor(self, question: str | None = None) -> None:
        if self._inputs is None or self._design is None:
            QMessageBox.information(self, "RESize", "There is no design to discuss yet.")
            return
        if self._tutor is not None:
            self._tutor.close()
        self._tutor = TutorDialog(self._context(), self)
        if isinstance(question, str) and question:
            self._tutor.set_question(question)
        self._tutor.show()

    def _ask_about_step(self) -> None:
        row = self.topics.currentRow()
        if row < 0 or row >= len(self.topic_order):
            QMessageBox.information(self, "RESize", "Select a step in the list first.")
            return
        title = EXPLANATIONS[self.topic_order[row]]["title"]
        self._open_tutor(f"Explain this step for my project and check my numbers: {title}")

    def _show_topic(self, row: int) -> None:
        if row < 0 or row >= len(self.topic_order):
            return
        key = self.topic_order[row]
        worked = None
        if self._inputs is not None and self._design is not None:
            worked = self._worked(key)
        self.detail.setHtml(explanation_html(key, worked, heading=False, math=True))

    def initializePage(self) -> None:
        try:
            inputs, design, findings, light, dark = self._compute()
        except ValueError as exc:
            self.html = self.html_screen = ""
            self._inputs = self._design = None
            self._findings = []
            self.browser.setHtml(f"<p><b>Cannot compute the design:</b> {exc}</p>")
            return
        self._inputs, self._design, self._findings = inputs, design, findings
        self._base = (light, dark)
        self._explained = ("", "")
        self._draw_charts()
        self._compose()
        row = self.topics.currentRow()
        if row >= 0:
            self._show_topic(row)  # refresh the open topic with the new numbers

    # --- extra sections: values to check, comparison with version A -----------------------
    def _compose(self) -> None:
        """Report = the technology's report + provenance + comparison with version A."""
        from resize_energy.gui import versions_ui  # here: it imports this module's fields

        extra = provenance_section(self)
        compare = versions_ui.compare_sections(self)
        light, dark = self._base
        light = self._with_banner(light)
        self.html = insert_before_formulas(light, extra + compare[0] + self._explained[0])
        self.html_screen = insert_before_formulas(dark, extra + compare[1] + self._explained[1])
        self.explain_button.setEnabled(self._version_a is not None and bool(compare[0]))
        self.browser.setHtml(self.html_screen)

    def _with_banner(self, html: str) -> str:
        """The still picture under the title of the report (PDF only; the screen has the
        animated banner above the report)."""
        ratio = getattr(self, "_banner_ratio", 0.0)
        if not ratio or "chart:flow_banner" not in self.chart_images or "</h1>" not in html:
            return html
        tag = (f'<p align="center"><img src="chart:flow_banner" width="600" '
               f'height="{int(600 * ratio)}"></p>')
        return html.replace("</h1>", "</h1>" + tag, 1)

    def _keep_version(self) -> None:
        from resize_energy.gui import versions_ui

        if self._design is None:
            QMessageBox.information(self, "RESize", "There are no results to keep yet.")
            return
        if not versions_ui.keep(self):
            QMessageBox.information(self, "RESize",
                                    "Comparing versions is not available for this technology.")
            return
        QMessageBox.information(
            self, "RESize", "Version A kept. Go back, change something, and return here: the "
            "report will compare the two versions.")
        self._compose()

    def _explain_version(self) -> None:
        from resize_energy.gui import versions_ui

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._explained = versions_ui.explain(self)
        finally:
            QApplication.restoreOverrideCursor()
        self._compose()

    def _workbook(self):
        """The Excel workbook of the current design (technologies with ``has_excel``)."""
        raise NotImplementedError

    def _export_excel(self) -> None:
        if self._design is None:
            QMessageBox.information(self, "RESize", "There are no results to export yet.")
            return
        try:
            wb = self._workbook()
        except ImportError:
            QMessageBox.information(self, "RESize", "Excel export needs the openpyxl package.\n\n"
                                    "Close RESize and run, in the same Python environment:\n"
                                    "pip install openpyxl")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save workbook", self.pdf_name.replace(".pdf", ".xlsx"),
            "Excel workbooks (*.xlsx)")
        if not path:
            return
        from resize_energy.report.excel import save_workbook

        save_workbook(wb, path)
        QMessageBox.information(self, "RESize", f"Workbook saved to:\n{path}")

    def _export_pdf(self) -> None:
        if not self.html:
            QMessageBox.information(self, "RESize", "There is no report to export yet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save report", self.pdf_name, "PDF files (*.pdf)"
        )
        if not path:
            return
        doc = ReportDocument(self.chart_images)
        doc.setHtml(self.html)
        writer = QPdfWriter(path)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        doc.print_(writer)
        QMessageBox.information(self, "RESize", f"Report saved to:\n{path}")


class ResultsPage(BaseResultsPage):
    """Results of the photovoltaic design."""

    topic_order = TOPIC_ORDER
    pdf_name = "RESize_PV_report.pdf"
    has_excel = True

    def __init__(self, site: SitePage, load: LoadPage, comp: ComponentsPage, costs) -> None:
        self.site, self.load, self.comp, self.costs = site, load, comp, costs
        super().__init__()
        self.setTitle("5. Results and design checks")

    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        module, inverter, t_min, t_max = self.comp.specs()
        inputs = PVInputs(
            annual_demand_kwh=self.load.demand.value(),
            annual_irradiation_kwh_m2=self.site.irr.value(),
            coverage=self.load.coverage.value() / 100.0,
            performance_ratio=self.load.pr.value(),
            t_min_c=t_min, t_cell_max_c=t_max, module=module, inverter=inverter,
            latitude_deg=self.site.lat.value(), shading_loss=self.load.shading(),
            economics=self.costs.inputs(),
        )
        design = size_pv_system(inputs)
        findings = check_pv_design(inputs, design)
        note = (
            f"Site: lat {self.site.lat.value():.4f}, lon {self.site.lon.value():.4f}, "
            f"tilt {self.site.tilt.value():.0f} deg, azimuth {self.site.azimuth.value():.0f} deg."
        )
        light = build_pv_report(inputs, design, findings, site_note=note, theme="light")
        dark = build_pv_report(inputs, design, findings, site_note=note, theme="screen")
        return inputs, design, findings, light, dark

    def _flow(self):
        from resize_energy.report.flow_pictures import pv_picture

        return pv_picture(self._inputs, self._design)

    def _workbook(self):
        from resize_energy.report.excel import build_pv_workbook

        return build_pv_workbook(self._inputs, self._design)

    def _worked(self, key: str) -> str | None:
        return worked_example(key, self._inputs, self._design)

    def _context(self) -> str:
        return build_project_context(self._inputs, self._design, self._findings)

    def _charts(self) -> dict[str, ChartSpec]:
        return pv_charts(self._inputs, self._design)


STEP_NAMES = ["Site and solar resource", "Electricity demand", "Module and inverter",
              "Costs and savings", "Results and checks"]


