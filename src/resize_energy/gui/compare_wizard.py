"""Technology comparison pages (PySide6): site and demand, plants, costs, results."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
)

from resize_energy.core import profiles as prof
from resize_energy.core.biomass_design import BiomassInputs
from resize_energy.core.comparison import (
    TECH_NAMES,
    TECHS,
    ComparisonInputs,
    CostAssumptions,
    compare_technologies,
    comparison_sensitivity,
)
from resize_energy.core.fuel_library import SUBSTRATES
from resize_energy.core.nasa_power import NasaPowerError, fetch_wind_climate
from resize_energy.core.pvgis import PVGISError, fetch_pvcalc
from resize_energy.core.turbine_library import load_library
from resize_energy.core.wind_design import TurbineSpec, WindInputs
from resize_energy.gui.country import CountryBar
from resize_energy.gui.versus_panel import VersusPanel
from resize_energy.gui.widgets import StepPage
from resize_energy.gui.wizard import BaseResultsPage, NumberField, _hint, first_error
from resize_energy.report.charts import ChartSpec, comparison_charts
from resize_energy.report.html_report import build_comparison_report
from resize_energy.report.versus import versus_rounds
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.checker_compare import check_comparison
from resize_energy.tutor.context_compare import build_compare_context
from resize_energy.tutor.explanations_compare import COMPARE_TOPIC_ORDER
from resize_energy.tutor.worked_compare import compare_worked_example

COMPARE_STEP_NAMES = ["Site and demand", "Plant assumptions", "Costs and prices",
                      "Comparison"]


class CompareSelection:
    """The technologies chosen on the home page (always in the canonical order)."""

    def __init__(self, techs: tuple[str, ...] = ("pv", "wind")) -> None:
        self.techs = techs

    def has(self, key: str) -> bool:
        return key in self.techs

    @property
    def techs(self) -> tuple[str, ...]:
        return self._techs

    @techs.setter
    def techs(self, value: tuple[str, ...]) -> None:
        self._techs = tuple(t for t in TECHS if t in value)

    def names(self) -> str:
        names = [TECH_NAMES[t] for t in self._techs]
        return ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else "".join(names)

    # the resource groups are needed by a technology or by the hydrogen plant
    def needs_sun(self) -> bool:
        return self.has("pv") or self.has("hydrogen")

    def needs_wind(self) -> bool:
        return self.has("wind") or self.has("hydrogen")


def _warn(page: StepPage, items: list[tuple[str, NumberField]]) -> bool:
    error = first_error(items)
    if error:
        QMessageBox.warning(page, "Check the value", error)
        return False
    return True


class CompareSitePage(StepPage):
    def __init__(self, selection: CompareSelection | None = None) -> None:
        super().__init__()
        self.selection = selection or CompareSelection()
        self.setTitle("1. Site and demand")
        self.setSubTitle("Where is it, and how much energy do you need? Every technology is sized for this same demand.")
        self._implied_pr: float | None = None
        self._weather: prof.HourlyWeather | None = None

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
        pf.addRow("Annual energy demand (kWh of electricity)", self.demand)
        pf.addRow("Share of the demand to cover", self.coverage)

        self.sun_box = sun = QGroupBox("Solar resource")
        sf = QFormLayout(sun)
        sf.addRow("Annual in-plane irradiation H", self.irr)
        self.wind_box = wind = QGroupBox("Wind resource")
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

    def initializePage(self) -> None:
        sel = self.selection
        self.sun_box.setVisible(sel.needs_sun())
        self.wind_box.setVisible(sel.needs_wind())
        self.setSubTitle(f"One site and one demand: {sel.names()} are sized for the same job.")

    def implied_pr(self) -> float | None:
        return self._implied_pr

    def weather(self) -> prof.HourlyWeather | None:
        """Real hourly year, when it was downloaded (used by the hydrogen plant)."""
        return self._weather

    def _items(self) -> list[tuple[str, NumberField]]:
        items = [("Latitude", self.lat), ("Longitude", self.lon), ("Tilt", self.tilt),
                 ("Azimuth", self.azimuth), ("Annual demand", self.demand),
                 ("Coverage", self.coverage)]
        if self.selection.needs_sun():
            items.append(("Irradiation", self.irr))
        if self.selection.needs_wind():
            items += [("Mean wind speed", self.speed), ("Reference height", self.ref_height),
                      ("Weibull k", self.k), ("Shear exponent", self.alpha),
                      ("Elevation", self.elevation), ("Temperature", self.temperature)]
        return items

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
                self.irr.set_value(sun.annual_irradiation_kwh_m2, "PVGIS")
                self._implied_pr = sun.implied_performance_ratio
                lines.append(f"PVGIS: H = {sun.annual_irradiation_kwh_m2:,.0f} kWh/m2 per year.")
            except (PVGISError, ValueError) as exc:
                lines.append(f"PVGIS not available ({exc}): type H by hand.")
            try:
                climate = fetch_wind_climate(self.lat.value(), self.lon.value())
                self.speed.set_value(round(climate.mean_speed_50m_ms, 2), "NASA POWER")
                self.ref_height.set_value(50, "NASA POWER")
                text = f"NASA POWER: {climate.mean_speed_50m_ms:.2f} m/s at 50 m"
                if climate.mean_temperature_c is not None:
                    self.temperature.set_value(round(climate.mean_temperature_c), "NASA POWER")
                if climate.elevation_m is not None:
                    self.elevation.set_value(round(climate.elevation_m), "NASA POWER")
                lines.append(text + ".")
            except (NasaPowerError, ValueError) as exc:
                lines.append(f"NASA POWER not available ({exc}): type the wind values by hand.")
            self._weather = None
            if "hydrogen" in self.selection.techs:
                try:
                    self._weather = prof.fetch_hourly(self.lat.value(), self.lon.value())
                    lines.append(f"NASA POWER hourly {self._weather.year}: the hydrogen plant "
                                 "will be simulated on this real year.")
                except (NasaPowerError, ValueError) as exc:
                    lines.append(f"Hourly data not available ({exc}): the hydrogen plant uses "
                                 "an invented year.")
        finally:
            QApplication.restoreOverrideCursor()
        self.status.setText("\n".join(lines))

    def validatePage(self) -> bool:
        return _warn(self, self._items())


class ComparePlantPage(StepPage):
    GENERIC = "Generic 2 MW turbine"

    def __init__(self, site: CompareSitePage, selection: CompareSelection | None = None) -> None:
        super().__init__()
        self.site = site
        self.selection = selection or CompareSelection()
        self.setTitle("2. Plant assumptions")
        self.setSubTitle("Only the technologies you chose are asked here: the PV performance, the turbine, "
                         "the biogas feed and the electricity source of the hydrogen.")
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

        names = [s.name for s in SUBSTRATES]
        self.sub_a = QComboBox()
        self.sub_b = QComboBox()
        for name in names:
            self.sub_a.addItem(name)
            self.sub_b.addItem(name)
        self.sub_a.setCurrentIndex(2 if len(names) > 2 else 0)
        self.share_b = NumberField(50, 0, 100, 0, "% of the feed (mass)", "biomass.biogas_yield")
        self.hrt = NumberField(BiomassInputs().hrt_days, 10, 120, 0, "days", "biomass.digester")
        self.h2_pv = QCheckBox("Photovoltaic")
        self.h2_pv.setChecked(True)
        self.h2_wind = QCheckBox("Wind")

        self.pv_box = QGroupBox("Photovoltaic")
        pf = QFormLayout(self.pv_box)
        pf.addRow("Performance ratio (PR)", self.pr)
        self.wind_box = QGroupBox("Wind")
        wf = QFormLayout(self.wind_box)
        wf.addRow("Turbine model", self.picker)
        wf.addRow("Hub height", self.hub)
        wf.addRow("Turbine availability", self.availability)
        wf.addRow("Other losses (wake, electrical, ...)", self.losses)
        self.bio_box = QGroupBox("Biomass: biogas CHP (electricity-led)")
        bf = QFormLayout(self.bio_box)
        bf.addRow("Substrate A", self.sub_a)
        bf.addRow("Substrate B", self.sub_b)
        bf.addRow("Share of substrate B", self.share_b)
        bf.addRow("Retention time in the digester", self.hrt)
        self.h2_box = QGroupBox("Green hydrogen: where the electricity comes from")
        hl = QHBoxLayout(self.h2_box)
        hl.addWidget(self.h2_pv)
        hl.addWidget(self.h2_wind)
        hl.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(self.pv_box)
        layout.addWidget(self.wind_box)
        layout.addWidget(self.bio_box)
        layout.addWidget(self.h2_box)
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
        sel = self.selection
        self.pv_box.setVisible(sel.needs_sun())
        self.wind_box.setVisible(sel.needs_wind())
        self.bio_box.setVisible(sel.has("biomass"))
        self.h2_box.setVisible(sel.has("hydrogen"))

    def biomass(self) -> BiomassInputs:
        return BiomassInputs(
            pathway="biogas", substrate_a=SUBSTRATES[self.sub_a.currentIndex()],
            substrate_b=SUBSTRATES[self.sub_b.currentIndex()],
            share_b=self.share_b.value() / 100.0, hrt_days=self.hrt.value())

    def turbine(self) -> TurbineSpec:
        hub = self.hub.value()
        index = self.picker.currentIndex()
        if index <= 0:
            return replace(TurbineSpec(), hub_height_m=hub)
        return replace(self.library[index - 1].to_spec(), hub_height_m=hub)

    def validatePage(self) -> bool:
        sel = self.selection
        items: list[tuple[str, NumberField]] = []
        if sel.needs_sun():
            items.append(("Performance ratio", self.pr))
        if sel.needs_wind():
            items += [("Hub height", self.hub), ("Availability", self.availability),
                      ("Other losses", self.losses)]
        if sel.has("biomass"):
            items += [("Share of substrate B", self.share_b), ("Retention time", self.hrt)]
        if not _warn(self, items):
            return False
        if sel.has("hydrogen") and not (self.h2_pv.isChecked() or self.h2_wind.isChecked()):
            QMessageBox.warning(self, "Check the value",
                                "Choose PV, wind or both as the electricity of the hydrogen.")
            return False
        return True


class CompareCostPage(StepPage):
    def __init__(self, selection: CompareSelection | None = None) -> None:
        super().__init__()
        self.selection = selection or CompareSelection()
        c = CostAssumptions()
        self.setTitle("3. Costs and prices")
        self.setSubTitle("Costs and prices. The defaults are round placeholders that give an order of magnitude: replace them with local quotes and tariffs.")

        def nf(value, lo, hi, dec, unit, why="econ.lcoe") -> NumberField:
            return NumberField(value, lo, hi, dec, unit, why)

        self.pv_capex = nf(c.pv_capex_eur_per_kwp, 1, 20000, 0, "euro/kWp")
        self.pv_om = nf(c.pv_om_eur_per_kwp_year, 0, 1000, 1, "euro/kWp per year")
        self.pv_life = nf(c.pv_lifetime_years, 1, 60, 0, "years", "econ.crf")
        self.pv_co2 = nf(c.pv_lifecycle_g_per_kwh, 0, 500, 0, "g CO2/kWh", "econ.co2")
        self.w_capex = nf(c.wind_capex_eur_per_kw, 1, 20000, 0, "euro/kW")
        self.w_om = nf(c.wind_om_eur_per_kw_year, 0, 1000, 1, "euro/kW per year")
        self.w_life = nf(c.wind_lifetime_years, 1, 60, 0, "years", "econ.crf")
        self.w_co2 = nf(c.wind_lifecycle_g_per_kwh, 0, 500, 0, "g CO2/kWh", "econ.co2")
        self.b_capex = nf(c.bio_capex_eur_per_kwe, 1, 30000, 0, "euro/kWe")
        self.b_om = nf(c.bio_om_eur_per_kwe_year, 0, 3000, 0, "euro/kWe per year")
        self.b_feed = nf(c.bio_feedstock_eur_per_t, 0, 500, 0, "euro per tonne of substrate")
        self.b_life = nf(c.bio_lifetime_years, 1, 60, 0, "years", "econ.crf")
        self.b_co2 = nf(c.bio_lifecycle_g_per_kwh, 0, 1000, 0, "g CO2/kWh", "econ.co2")
        self.h_capex = nf(c.h2_electrolyser_capex_eur_per_kw, 100, 10000, 0, "euro/kW")
        self.h_price = nf(c.h2_reference_price_eur_per_kg, 0.1, 30, 2, "euro/kg", "econ.savings")
        self.h_ref_co2 = nf(c.h2_reference_kg_co2_per_kg, 0.5, 30, 1, "kg CO2/kg", "econ.co2")
        self.rate = nf(c.discount_rate * 100, 0, 30, 1, "%", "econ.crf")
        self.retail = nf(c.retail_price_eur_per_kwh, 0.001, 5, 3, "euro/kWh", "econ.savings")
        self.export = nf(c.export_price_eur_per_kwh, 0, 5, 3, "euro/kWh", "econ.savings")
        self.grid = nf(c.grid_kg_co2_per_kwh, 0, 2, 3, "kg CO2/kWh", "econ.co2")

        self.pv_box = QGroupBox("Photovoltaic (also feeds the hydrogen)")
        pf = QFormLayout(self.pv_box)
        pf.addRow("Investment (CAPEX)", self.pv_capex)
        pf.addRow("Operation and maintenance", self.pv_om)
        pf.addRow("Lifetime", self.pv_life)
        pf.addRow("Life-cycle emissions", self.pv_co2)
        self.wind_box = QGroupBox("Wind (also feeds the hydrogen)")
        wf = QFormLayout(self.wind_box)
        wf.addRow("Investment (CAPEX)", self.w_capex)
        wf.addRow("Operation and maintenance", self.w_om)
        wf.addRow("Lifetime", self.w_life)
        wf.addRow("Life-cycle emissions", self.w_co2)
        self.bio_box = QGroupBox("Biomass: biogas CHP with digester")
        bf = QFormLayout(self.bio_box)
        bf.addRow("Investment (CAPEX)", self.b_capex)
        bf.addRow("Operation and maintenance", self.b_om)
        bf.addRow("Substrate cost", self.b_feed)
        bf.addRow("Lifetime", self.b_life)
        bf.addRow("Life-cycle emissions", self.b_co2)
        self.h2_box = QGroupBox("Green hydrogen")
        hf = QFormLayout(self.h2_box)
        hf.addRow("Electrolyser CAPEX", self.h_capex)
        hf.addRow("Hydrogen from natural gas: price", self.h_price)
        hf.addRow("Hydrogen from natural gas: emissions", self.h_ref_co2)
        common = QGroupBox("Prices and rates")
        cf = QFormLayout(common)
        cf.addRow("Discount rate", self.rate)
        cf.addRow("Electricity price you pay (retail)", self.retail)
        cf.addRow("Price for exported energy", self.export)
        cf.addRow("Grid emission factor", self.grid)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        row1 = QHBoxLayout()
        row1.addWidget(self.pv_box)
        row1.addWidget(self.wind_box)
        row2 = QHBoxLayout()
        row2.addWidget(self.bio_box)
        row2.addWidget(self.h2_box)
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addWidget(common)
        self.country_bar = CountryBar({"electricity": self.retail, "export": self.export, "grid_ef": self.grid})
        self.country = self.country_bar.combo
        layout.insertWidget(0, self.country_bar)
        layout.addWidget(_hint(
            "Defaults are round, typical orders of magnitude for utility and commercial plants "
            "in Europe, not quotes. Include grid connection and permits in the CAPEX if they "
            "matter. The hydrogen plant also uses the PV and wind costs and the other electrolyser "
            "values of the hydrogen flow (stack, storage, water). No incentives or taxes."))
        layout.addStretch(1)

    def initializePage(self) -> None:
        self.country_bar.sync()
        sel = self.selection
        self.pv_box.setVisible(sel.needs_sun())
        self.wind_box.setVisible(sel.needs_wind())
        self.bio_box.setVisible(sel.has("biomass"))
        self.h2_box.setVisible(sel.has("hydrogen"))

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
            bio_capex_eur_per_kwe=self.b_capex.value(),
            bio_om_eur_per_kwe_year=self.b_om.value(),
            bio_feedstock_eur_per_t=self.b_feed.value(),
            bio_lifetime_years=self.b_life.value(),
            bio_lifecycle_g_per_kwh=self.b_co2.value(),
            h2_electrolyser_capex_eur_per_kw=self.h_capex.value(),
            h2_reference_price_eur_per_kg=self.h_price.value(),
            h2_reference_kg_co2_per_kg=self.h_ref_co2.value(),
        )

    def validatePage(self) -> bool:
        sel = self.selection
        items = [("Discount rate", self.rate), ("Retail price", self.retail),
                 ("Export price", self.export), ("Grid emission factor", self.grid)]
        if sel.needs_sun():
            items += [("PV CAPEX", self.pv_capex), ("PV O&M", self.pv_om),
                      ("PV lifetime", self.pv_life), ("PV life-cycle emissions", self.pv_co2)]
        if sel.needs_wind():
            items += [("Wind CAPEX", self.w_capex), ("Wind O&M", self.w_om),
                      ("Wind lifetime", self.w_life), ("Wind life-cycle emissions", self.w_co2)]
        if sel.has("biomass"):
            items += [("Biogas CAPEX", self.b_capex), ("Biogas O&M", self.b_om),
                      ("Substrate cost", self.b_feed), ("Biogas lifetime", self.b_life),
                      ("Biogas life-cycle emissions", self.b_co2)]
        if sel.has("hydrogen"):
            items += [("Electrolyser CAPEX", self.h_capex), ("Reference hydrogen price", self.h_price),
                      ("Reference hydrogen emissions", self.h_ref_co2)]
        return _warn(self, items)


class CompareResultsPage(BaseResultsPage):
    """Side-by-side figures, checks and the Why? panel for the economics."""

    topic_order = COMPARE_TOPIC_ORDER
    pdf_name = "RESize_comparison_report.pdf"

    def __init__(self, site: CompareSitePage, plant: ComparePlantPage,
                 costs: CompareCostPage, selection: CompareSelection | None = None) -> None:
        self.site, self.plant, self.costs_page = site, plant, costs
        self.selection = selection or CompareSelection()
        super().__init__()
        self.setTitle("4. Comparison")
        self.setSubTitle("Side by side. Pick a step on the right to see why.")
        # the Versus screen first, the full report in the second tab
        self.versus = VersusPanel()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.versus)
        self.tabs = QTabWidget()
        self.tabs.addTab(scroll, "Versus")
        self.tabs.addTab(self.browser, "Full report")
        self.splitter.replaceWidget(0, self.tabs)

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
            techs=self.selection.techs,
            latitude_deg=s.lat.value(),
            biomass=p.biomass(),
            h2_use_pv=p.h2_pv.isChecked(),
            h2_use_wind=p.h2_wind.isChecked(),
            hourly_weather=s.weather(),
        )
        result = replace(compare_technologies(inputs),
                         sensitivity=comparison_sensitivity(inputs))
        findings = check_comparison(inputs, result)
        note = f"Site: lat {s.lat.value():.4f}, lon {s.lon.value():.4f}."
        light = build_comparison_report(inputs, result, findings, site_note=note, theme="light")
        dark = build_comparison_report(inputs, result, findings, site_note=note, theme="screen")
        return inputs, result, findings, light, dark

    def initializePage(self) -> None:
        self.setSubTitle(f"{self.selection.names()} side by side. Pick a step on the right "
                         "for the why.")
        super().initializePage()
        if self._design is not None:
            self.versus.set_rounds(versus_rounds(self._design))
            self.tabs.setCurrentIndex(0)

    def _worked(self, key: str) -> str | None:
        return compare_worked_example(key, self._inputs, self._design)

    def _context(self) -> str:
        return build_compare_context(self._inputs, self._design, self._findings)

    def _charts(self) -> dict[str, ChartSpec]:
        return comparison_charts(self._inputs, self._design)
