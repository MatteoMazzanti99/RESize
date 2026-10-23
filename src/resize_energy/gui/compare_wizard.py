"""Technology comparison pages (PySide6): site and demand, plants, costs, results."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from resize_energy.core.comparison import (
    ComparisonInputs,
    CostAssumptions,
    compare_technologies,
)
from resize_energy.core.nasa_power import NasaPowerError, fetch_wind_climate
from resize_energy.core.pvgis import PVGISError, fetch_pvcalc
from resize_energy.core.turbine_library import load_library
from resize_energy.core.wind_design import TurbineSpec, WindInputs
from resize_energy.gui.widgets import StepPage
from resize_energy.gui.wizard import BaseResultsPage, NumberField, _hint, first_error
from resize_energy.report.html_report import build_comparison_report
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.checker_compare import check_comparison
from resize_energy.tutor.context_compare import build_compare_context
from resize_energy.tutor.explanations_compare import COMPARE_TOPIC_ORDER
from resize_energy.tutor.worked_compare import compare_worked_example

COMPARE_STEP_NAMES = ["Site and demand", "Plant assumptions", "Costs and prices",
                      "Comparison"]


def _warn(page: StepPage, items: list[tuple[str, NumberField]]) -> bool:
    error = first_error(items)
    if error:
        QMessageBox.warning(page, "Check the value", error)
        return False
    return True


class CompareSitePage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("1. Site and demand")
        self.setSubTitle("One site and one demand: both technologies are sized for the same job.")
        self._implied_pr: float | None = None

        self.lat = NumberField(45.07, -90, 90, 4, "deg N")
        self.lon = NumberField(7.69, -180, 180, 4, "deg E")
        self.tilt = NumberField(30, 0, 90, 0, "deg")
        self.azimuth = NumberField(0, -180, 180, 0, "deg")
        self.demand = NumberField(10_000_000, 1, 1e12, 0, "kWh per year", "econ.same_demand")
        self.coverage = NumberField(100, 1, 100, 0, "%", "econ.same_demand")
        self.irr = NumberField(1500, 100, 3500, 0, "kWh/m2 per year", "pv.irradiation")
        self.speed = NumberField(6.0, 0.5, 20, 2, "m/s", "wind.resource")
        self.ref_height = NumberField(50, 5, 300, 0, "m")
        self.k = NumberField(2.0, 1.0, 5.0, 2, "", "wind.weibull")
        self.alpha = NumberField(0.14, 0.0, 0.5, 2, "", "wind.shear")
        self.elevation = NumberField(100, -400, 5000, 0, "m a.s.l.", "wind.air_density")
        self.temperature = NumberField(12, -30, 40, 0, "degC", "wind.air_density")

        self.status = QLabel("")
        self.status.setWordWrap(True)
        fetch = QPushButton("Get solar and wind data (PVGIS + NASA POWER)")
        fetch.clicked.connect(self._fetch)
        fetch_row = QHBoxLayout()
        fetch_row.addWidget(fetch)
        fetch_row.addStretch(1)

        place = QGroupBox("Site and demand")
        pf = QFormLayout(place)
        pf.addRow("Latitude (north positive)", self.lat)
        pf.addRow("Longitude (east positive)", self.lon)
        pf.addRow("Tilt of the PV modules", self.tilt)
        pf.addRow("Azimuth (0 = south)", self.azimuth)
        pf.addRow("Annual electricity demand", self.demand)
        pf.addRow("Share of the demand to cover", self.coverage)

        sun = QGroupBox("Solar resource")
        sf = QFormLayout(sun)
        sf.addRow("Annual in-plane irradiation H", self.irr)
        wind = QGroupBox("Wind resource")
        wf = QFormLayout(wind)
        wf.addRow("Mean wind speed", self.speed)
        wf.addRow("... measured at height", self.ref_height)
        wf.addRow("Weibull shape k", self.k)
        wf.addRow("Shear exponent alpha", self.alpha)
        wf.addRow("Elevation", self.elevation)
        wf.addRow("Mean temperature", self.temperature)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(place)
        layout.addLayout(fetch_row)
        layout.addWidget(self.status)
        layout.addWidget(_hint(
            "The button fills the irradiation (PVGIS) and the wind speed, temperature and "
            "elevation (NASA POWER, smooth long-term values at 50 m). Offline, or with "
            "better data, type the values by hand."))
        row = QHBoxLayout()
        row.addWidget(sun)
        row.addWidget(wind)
        layout.addLayout(row)
        layout.addStretch(1)

    def implied_pr(self) -> float | None:
        return self._implied_pr

    def _items(self) -> list[tuple[str, NumberField]]:
        return [("Latitude", self.lat), ("Longitude", self.lon), ("Tilt", self.tilt),
                ("Azimuth", self.azimuth), ("Annual demand", self.demand),
                ("Coverage", self.coverage), ("Irradiation", self.irr),
                ("Mean wind speed", self.speed), ("Reference height", self.ref_height),
                ("Weibull k", self.k), ("Shear exponent", self.alpha),
                ("Elevation", self.elevation), ("Temperature", self.temperature)]

    def _fetch(self) -> None:
        error = first_error([("Latitude", self.lat), ("Longitude", self.lon),
                             ("Tilt", self.tilt), ("Azimuth", self.azimuth)])
        if error:
            self.status.setText(error)
            return
        lines = []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            try:
                sun = fetch_pvcalc(self.lat.value(), self.lon.value(), self.tilt.value(),
                                   self.azimuth.value(), 14)
                self.irr.set_value(sun.annual_irradiation_kwh_m2)
                self._implied_pr = sun.implied_performance_ratio
                lines.append(f"PVGIS: H = {sun.annual_irradiation_kwh_m2:,.0f} kWh/m2 per year.")
            except (PVGISError, ValueError) as exc:
                lines.append(f"PVGIS not available ({exc}): type H by hand.")
            try:
                climate = fetch_wind_climate(self.lat.value(), self.lon.value())
                self.speed.set_value(round(climate.mean_speed_50m_ms, 2))
                self.ref_height.set_value(50)
                text = f"NASA POWER: {climate.mean_speed_50m_ms:.2f} m/s at 50 m"
                if climate.mean_temperature_c is not None:
                    self.temperature.set_value(round(climate.mean_temperature_c))
                if climate.elevation_m is not None:
                    self.elevation.set_value(round(climate.elevation_m))
                lines.append(text + ".")
            except (NasaPowerError, ValueError) as exc:
                lines.append(f"NASA POWER not available ({exc}): type the wind values by hand.")
        finally:
            QApplication.restoreOverrideCursor()
        self.status.setText("\n".join(lines))

    def validatePage(self) -> bool:
        return _warn(self, self._items())


class ComparePlantPage(StepPage):
    GENERIC = "Generic 2 MW turbine"

    def __init__(self, site: CompareSitePage) -> None:
        super().__init__()
        self.site = site
        self.setTitle("2. Plant assumptions")
        self.setSubTitle("Performance of the PV plant and the turbine used for the comparison.")
        self.library = load_library()

        self.pr = NumberField(0.80, 0.5, 0.95, 2, "", "pv.performance_ratio")
        self.availability = NumberField(97, 50, 100, 1, "%", "wind.losses")
        self.losses = NumberField(10, 0, 50, 1, "%", "wind.losses")
        self.hub = NumberField(TurbineSpec().hub_height_m, 5, 300, 0, "m", "wind.shear")
        self.picker = QComboBox()
        self.picker.setMaxVisibleItems(20)
        self.picker.addItem(self.GENERIC)
        for turbine in self.library:
            self.picker.addItem(turbine.label)

        pv_box = QGroupBox("Photovoltaic")
        pf = QFormLayout(pv_box)
        pf.addRow("Performance ratio (PR)", self.pr)
        wind_box = QGroupBox("Wind")
        wf = QFormLayout(wind_box)
        wf.addRow("Turbine model", self.picker)
        wf.addRow("Hub height", self.hub)
        wf.addRow("Turbine availability", self.availability)
        wf.addRow("Other losses (wake, electrical, ...)", self.losses)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(pv_box)
        layout.addWidget(wind_box)
        layout.addWidget(_hint(
            "The PV array is sized exactly on the target. The wind plant uses a whole number "
            "of the chosen turbines, so a large turbine on a small demand overshoots: pick a "
            "turbine of a size comparable with the demand. Full module, inverter and layout "
            "details are in the photovoltaic and wind flows."))
        layout.addStretch(1)

    def initializePage(self) -> None:
        implied = self.site.implied_pr()
        if implied and 0.5 <= implied <= 0.95:
            self.pr.set_value(round(implied, 2))

    def turbine(self) -> TurbineSpec:
        hub = self.hub.value()
        index = self.picker.currentIndex()
        if index <= 0:
            return replace(TurbineSpec(), hub_height_m=hub)
        return replace(self.library[index - 1].to_spec(), hub_height_m=hub)

    def validatePage(self) -> bool:
        return _warn(self, [("Performance ratio", self.pr), ("Hub height", self.hub),
                            ("Availability", self.availability), ("Other losses", self.losses)])


class CompareCostPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        c = CostAssumptions()
        self.setTitle("3. Costs and prices")
        self.setSubTitle("Round placeholder values: replace them with local quotes and tariffs.")

        self.pv_capex = NumberField(c.pv_capex_eur_per_kwp, 1, 20000, 0, "euro/kWp", "econ.lcoe")
        self.pv_om = NumberField(c.pv_om_eur_per_kwp_year, 0, 1000, 1, "euro/kWp per year",
                                 "econ.lcoe")
        self.pv_life = NumberField(c.pv_lifetime_years, 1, 60, 0, "years", "econ.crf")
        self.pv_co2 = NumberField(c.pv_lifecycle_g_per_kwh, 0, 500, 0, "g CO2/kWh", "econ.co2")
        self.w_capex = NumberField(c.wind_capex_eur_per_kw, 1, 20000, 0, "euro/kW", "econ.lcoe")
        self.w_om = NumberField(c.wind_om_eur_per_kw_year, 0, 1000, 1, "euro/kW per year",
                                "econ.lcoe")
        self.w_life = NumberField(c.wind_lifetime_years, 1, 60, 0, "years", "econ.crf")
        self.w_co2 = NumberField(c.wind_lifecycle_g_per_kwh, 0, 500, 0, "g CO2/kWh", "econ.co2")
        self.rate = NumberField(c.discount_rate * 100, 0, 30, 1, "%", "econ.crf")
        self.retail = NumberField(c.retail_price_eur_per_kwh, 0.001, 5, 3, "euro/kWh",
                                  "econ.savings")
        self.export = NumberField(c.export_price_eur_per_kwh, 0, 5, 3, "euro/kWh", "econ.savings")
        self.grid = NumberField(c.grid_kg_co2_per_kwh, 0, 2, 3, "kg CO2/kWh", "econ.co2")

        pv_box = QGroupBox("Photovoltaic")
        pf = QFormLayout(pv_box)
        pf.addRow("Investment (CAPEX)", self.pv_capex)
        pf.addRow("Operation and maintenance", self.pv_om)
        pf.addRow("Lifetime", self.pv_life)
        pf.addRow("Life-cycle emissions", self.pv_co2)
        wind_box = QGroupBox("Wind")
        wf = QFormLayout(wind_box)
        wf.addRow("Investment (CAPEX)", self.w_capex)
        wf.addRow("Operation and maintenance", self.w_om)
        wf.addRow("Lifetime", self.w_life)
        wf.addRow("Life-cycle emissions", self.w_co2)
        common = QGroupBox("Prices and rates")
        cf = QFormLayout(common)
        cf.addRow("Discount rate", self.rate)
        cf.addRow("Electricity price you pay (retail)", self.retail)
        cf.addRow("Price for exported energy", self.export)
        cf.addRow("Grid emission factor", self.grid)

        self._items = [
            ("PV CAPEX", self.pv_capex), ("PV O&M", self.pv_om), ("PV lifetime", self.pv_life),
            ("PV life-cycle emissions", self.pv_co2), ("Wind CAPEX", self.w_capex),
            ("Wind O&M", self.w_om), ("Wind lifetime", self.w_life),
            ("Wind life-cycle emissions", self.w_co2), ("Discount rate", self.rate),
            ("Retail price", self.retail), ("Export price", self.export),
            ("Grid emission factor", self.grid)]

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        row = QHBoxLayout()
        row.addWidget(pv_box)
        row.addWidget(wind_box)
        layout.addLayout(row)
        layout.addWidget(common)
        layout.addWidget(_hint(
            "Defaults are round, typical orders of magnitude for utility and commercial plants "
            "in Europe, not quotes. Life-cycle emissions are typical literature values (tens "
            "of g/kWh for PV, about 10 for onshore wind). Include grid connection and permits "
            "in the CAPEX if they matter. No incentives or taxes are modelled."))
        layout.addStretch(1)

    def costs(self) -> CostAssumptions:
        return CostAssumptions(
            pv_capex_eur_per_kwp=self.pv_capex.value(),
            pv_om_eur_per_kwp_year=self.pv_om.value(),
            pv_lifetime_years=self.pv_life.value(),
            pv_lifecycle_g_per_kwh=self.pv_co2.value(),
            wind_capex_eur_per_kw=self.w_capex.value(),
            wind_om_eur_per_kw_year=self.w_om.value(),
            wind_lifetime_years=self.w_life.value(),
            wind_lifecycle_g_per_kwh=self.w_co2.value(),
            discount_rate=self.rate.value() / 100.0,
            retail_price_eur_per_kwh=self.retail.value(),
            export_price_eur_per_kwh=self.export.value(),
            grid_kg_co2_per_kwh=self.grid.value(),
        )

    def validatePage(self) -> bool:
        return _warn(self, self._items)


class CompareResultsPage(BaseResultsPage):
    """Side-by-side figures, checks and the Why? panel for the economics."""

    topic_order = COMPARE_TOPIC_ORDER
    pdf_name = "RESize_comparison_report.pdf"

    def __init__(self, site: CompareSitePage, plant: ComparePlantPage,
                 costs: CompareCostPage) -> None:
        self.site, self.plant, self.costs_page = site, plant, costs
        super().__init__()
        self.setTitle("4. Comparison")
        self.setSubTitle("Photovoltaic and wind side by side. Pick a step on the right for the why.")

    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        s, p = self.site, self.plant
        wind = WindInputs(
            annual_demand_kwh=s.demand.value(),
            mean_speed_ref_ms=s.speed.value(),
            ref_height_m=s.ref_height.value(),
            weibull_k=s.k.value(),
            shear_alpha=s.alpha.value(),
            elevation_m=s.elevation.value(),
            temperature_c=s.temperature.value(),
            coverage=s.coverage.value() / 100.0,
            availability=p.availability.value() / 100.0,
            other_losses=p.losses.value() / 100.0,
            turbine=p.turbine(),
        )
        inputs = ComparisonInputs(
            annual_irradiation_kwh_m2=s.irr.value(),
            performance_ratio=p.pr.value(),
            wind=wind,
            costs=self.costs_page.costs(),
        )
        result = compare_technologies(inputs)
        findings = check_comparison(inputs, result)
        note = f"Site: lat {s.lat.value():.4f}, lon {s.lon.value():.4f}."
        light = build_comparison_report(inputs, result, findings, site_note=note, theme="light")
        dark = build_comparison_report(inputs, result, findings, site_note=note, theme="screen")
        return inputs, result, findings, light, dark

    def _worked(self, key: str) -> str | None:
        return compare_worked_example(key, self._inputs, self._design)

    def _context(self) -> str:
        return build_compare_context(self._inputs, self._design, self._findings)
