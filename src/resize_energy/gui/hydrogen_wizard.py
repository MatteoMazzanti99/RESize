"""Green hydrogen pages (PySide6): goal and sources, site and profiles, electrolyser, costs, results."""

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
    QVBoxLayout,
)

from resize_energy.core import hydrogen as h2
from resize_energy.core import profiles as prof
from resize_energy.core import wind
from resize_energy.core.hydrogen_design import (
    MODES,
    HydrogenInputs,
    HydrogenProfiles,
    hydrogen_sensitivity,
    size_hydrogen_plant,
)
from resize_energy.core.nasa_power import NasaPowerError
from resize_energy.core.pvgis import PVGISError, fetch_pvcalc
from resize_energy.core.turbine_library import load_library
from resize_energy.core.wind_design import TurbineSpec
from resize_energy.gui.biomass_wizard import _show_row
from resize_energy.gui.country import CountryBar
from resize_energy.gui.widgets import StepPage
from resize_energy.gui.wizard import BaseResultsPage, NumberField, _hint, first_error
from resize_energy.report.charts import ChartSpec, hydrogen_charts
from resize_energy.report.html_report import build_hydrogen_report
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.checker_hydrogen import check_hydrogen_design
from resize_energy.tutor.context_hydrogen import build_hydrogen_context
from resize_energy.tutor.explanations_hydrogen import HYDROGEN_TOPIC_ORDER
from resize_energy.tutor.worked_hydrogen import hydrogen_worked_example

HYDROGEN_STEP_NAMES = ["Goal and sources", "Site and profiles", "Electrolyser and storage",
                       "Costs and emissions", "Results and checks"]
MODE_KEYS = list(MODES)


def _warn(page: StepPage, items: list[tuple[str, NumberField]]) -> bool:
    error = first_error(items)
    if error:
        QMessageBox.warning(page, "Check the value", error)
        return False
    return True


class HydrogenGoalPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("1. Goal and sources")
        self.setSubTitle("What do you already know, and which electricity feeds the electrolyser? Tick every source you want to use.")
        self.mode_picker = QComboBox()
        for key in MODE_KEYS:
            self.mode_picker.addItem(MODES[key])
        self.pv = QCheckBox("Photovoltaic")
        self.pv.setChecked(True)
        self.wind = QCheckBox("Wind")
        self.grid = QCheckBox("Grid")
        for box in (self.mode_picker,):
            box.currentIndexChanged.connect(self._changed)
        for box in (self.pv, self.wind, self.grid):
            box.stateChanged.connect(self._changed)

        self.demand = NumberField(100_000, 1, 1e10, 0, "kg per year", "hydrogen.sizing")
        self.pv_ratio = NumberField(1.5, 0.1, 10, 2, "kWp per kW of electrolyser",
                                    "hydrogen.sizing")
        self.wind_ratio = NumberField(1.2, 0.1, 10, 2, "kW per kW of electrolyser",
                                      "hydrogen.sizing")
        self.pv_kwp = NumberField(1500, 0, 1e7, 0, "kWp", "hydrogen.sizing")
        self.wind_kw = NumberField(1000, 0, 1e7, 0, "kW", "hydrogen.sizing")
        self.el_kw = NumberField(1000, 0, 1e7, 0, "kW", "hydrogen.sizing")

        top = QGroupBox("Starting point")
        tl = QVBoxLayout(top)
        tl.addWidget(self.mode_picker)
        src = QGroupBox("Electricity sources (any combination)")
        sl = QHBoxLayout(src)
        for box in (self.pv, self.wind, self.grid):
            sl.addWidget(box)
        sl.addStretch(1)
        self.form = QFormLayout()
        self.form.addRow("Hydrogen needed", self.demand)
        self.form.addRow("PV power per kW of electrolyser", self.pv_ratio)
        self.form.addRow("Wind power per kW of electrolyser", self.wind_ratio)
        self.form.addRow("Photovoltaic plant", self.pv_kwp)
        self.form.addRow("Wind plant", self.wind_kw)
        self.form.addRow("Electrolyser power", self.el_kw)
        sizes = QGroupBox("Size")
        sizes.setLayout(self.form)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(top)
        layout.addWidget(src)
        layout.addWidget(sizes)
        layout.addWidget(_hint(
            "From a demand, the electrolyser and the renewable plants are sized for it: the "
            "ratio of renewable to electrolyser power (oversizing, 1.2-2) is your choice. From an "
            "existing plant you give the sizes and get the hydrogen. With the grid the "
            "electrolyser runs more hours, but the hydrogen is no longer green: the carbon "
            "intensity is shown in the results."))
        layout.addStretch(1)
        self._changed()

    def mode(self) -> str:
        return MODE_KEYS[max(0, self.mode_picker.currentIndex())]

    def _changed(self, *_args) -> None:
        demand = self.mode() == "demand"
        pv, wind_on = self.pv.isChecked(), self.wind.isChecked()
        _show_row(self.form, self.demand, demand)
        _show_row(self.form, self.pv_ratio, demand and pv)
        _show_row(self.form, self.wind_ratio, demand and wind_on)
        _show_row(self.form, self.pv_kwp, not demand and pv)
        _show_row(self.form, self.wind_kw, not demand and wind_on)
        _show_row(self.form, self.el_kw, not demand)

    def _items(self) -> list[tuple[str, NumberField]]:
        if self.mode() == "demand":
            items = [("Hydrogen needed", self.demand)]
            if self.pv.isChecked():
                items.append(("PV per kW of electrolyser", self.pv_ratio))
            if self.wind.isChecked():
                items.append(("Wind per kW of electrolyser", self.wind_ratio))
            return items
        items = [("Electrolyser power", self.el_kw)]
        if self.pv.isChecked():
            items.append(("PV plant", self.pv_kwp))
        if self.wind.isChecked():
            items.append(("Wind plant", self.wind_kw))
        return items

    def validatePage(self) -> bool:
        if not (self.pv.isChecked() or self.wind.isChecked() or self.grid.isChecked()):
            QMessageBox.warning(self, "Check the value", "Choose at least one electricity source.")
            return False
        return _warn(self, self._items())


class HydrogenSitePage(StepPage):
    GENERIC = "Generic 2 MW turbine"

    def __init__(self, goal: HydrogenGoalPage) -> None:
        super().__init__()
        self.goal = goal
        self._weather: prof.HourlyWeather | None = None
        self.library = load_library()
        self.setTitle("2. Site and profiles")
        self.setSubTitle("Where is it? Press the button for real hourly sun and wind data, or keep the defaults to explore: hour by hour, sun and wind decide how long the electrolyser runs.")

        self.lat = NumberField(45.07, -90, 90, 4, "deg N")
        self.lon = NumberField(7.69, -180, 180, 4, "deg E")
        self.tilt = NumberField(30, 0, 90, 0, "deg")
        self.azimuth = NumberField(0, -180, 180, 0, "deg")
        self.pv_yield = NumberField(1300, 300, 2600, 0, "kWh per kWp per year", "hydrogen.dispatch")
        self.speed = NumberField(6.5, 0.5, 20, 2, "m/s at 50 m", "hydrogen.dispatch")
        self.k = NumberField(2.0, 1.0, 5.0, 2, "")
        self.alpha = NumberField(0.14, 0.0, 0.5, 2, "")
        self.hub = NumberField(TurbineSpec().hub_height_m, 5, 300, 0, "m")
        self.elevation = NumberField(100, -400, 5000, 0, "m a.s.l.")
        self.temperature = NumberField(12, -30, 40, 0, "degC")
        self.availability = NumberField(97, 50, 100, 1, "%")
        self.losses = NumberField(10, 0, 50, 1, "%")
        self.picker = QComboBox()
        self.picker.setMaxVisibleItems(20)
        self.picker.addItem(self.GENERIC)
        for turbine in self.library:
            self.picker.addItem(turbine.label)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        fetch = QPushButton("Get real hourly data (NASA POWER) and PV yield (PVGIS)")
        fetch.clicked.connect(self._fetch)
        row = QHBoxLayout()
        row.addWidget(fetch)
        row.addStretch(1)

        place = QGroupBox("Site")
        pf = QFormLayout(place)
        pf.addRow("Latitude (north positive)", self.lat)
        pf.addRow("Longitude (east positive)", self.lon)
        self.pv_box = QGroupBox("Photovoltaic")
        vf = QFormLayout(self.pv_box)
        vf.addRow("Tilt", self.tilt)
        vf.addRow("Azimuth (0 = south)", self.azimuth)
        vf.addRow("Yearly yield", self.pv_yield)
        self.wind_box = QGroupBox("Wind")
        wf = QFormLayout(self.wind_box)
        wf.addRow("Turbine", self.picker)
        wf.addRow("Mean wind speed", self.speed)
        wf.addRow("Hub height", self.hub)
        wf.addRow("Weibull k (invented year only)", self.k)
        wf.addRow("Shear exponent alpha", self.alpha)
        wf.addRow("Elevation", self.elevation)
        wf.addRow("Mean temperature", self.temperature)
        wf.addRow("Availability", self.availability)
        wf.addRow("Other losses", self.losses)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(place)
        layout.addLayout(row)
        layout.addWidget(self.status)
        layout.addWidget(_hint(
            "The button downloads one real year of hourly wind and radiation (same place, same "
            "year) and the yearly PV yield. Without it, or offline, an invented year with the "
            "same yearly totals is used: the hours of operation are then only indicative."))
        columns = QHBoxLayout()
        columns.addWidget(self.pv_box)
        columns.addWidget(self.wind_box)
        layout.addLayout(columns)
        layout.addStretch(1)

    def initializePage(self) -> None:
        self.pv_box.setVisible(self.goal.pv.isChecked())
        self.wind_box.setVisible(self.goal.wind.isChecked())

    def _query_items(self) -> list[tuple[str, NumberField]]:
        return [("Latitude", self.lat), ("Longitude", self.lon), ("Tilt", self.tilt),
                ("Azimuth", self.azimuth)]

    def _fetch(self) -> None:
        error = first_error(self._query_items())
        if error:
            self.status.setText(error)
            return
        lines = []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            try:
                sun = fetch_pvcalc(self.lat.value(), self.lon.value(), self.tilt.value(),
                                   self.azimuth.value(), 14)
                self.pv_yield.set_value(round(sun.annual_yield_kwh_per_kwp))
                lines.append(f"PVGIS: {sun.annual_yield_kwh_per_kwp:,.0f} kWh/kWp per year.")
            except (PVGISError, ValueError) as exc:
                lines.append(f"PVGIS not available ({exc}): type the yield by hand.")
            try:
                self._weather = prof.fetch_hourly(self.lat.value(), self.lon.value())
                mean50 = sum(self._weather.wind50_ms) / prof.HOURS
                self.speed.set_value(round(mean50, 2))
                lines.append(f"NASA POWER hourly {self._weather.year}: mean wind {mean50:.2f} "
                             "m/s at 50 m. Real hourly profiles will be used.")
            except (NasaPowerError, ValueError) as exc:
                self._weather = None
                lines.append(f"NASA POWER hourly data not available ({exc}): an invented year "
                             "will be used.")
        finally:
            QApplication.restoreOverrideCursor()
        self.status.setText("\n".join(lines))

    def turbine(self) -> TurbineSpec:
        index = self.picker.currentIndex()
        base = TurbineSpec() if index <= 0 else self.library[index - 1].to_spec()
        return replace(base, hub_height_m=self.hub.value())

    def profiles(self) -> HydrogenProfiles:
        """Hourly profiles of the selected sources: real when the weather was fetched."""
        weather = self._weather
        pv_unit = wind_unit = None
        if self.goal.pv.isChecked():
            pv_unit = (prof.pv_profile_from_ghi(weather.ghi_w_m2, self.pv_yield.value())
                       if weather else
                       prof.synthetic_pv_profile(self.lat.value(), self.pv_yield.value()))
        if self.goal.wind.isChecked():
            series = (weather.wind50_ms if weather
                      else prof.synthetic_wind_series(self.speed.value(), self.k.value()))
            rho = wind.air_density(self.elevation.value(), self.temperature.value())
            wind_unit = prof.turbine_unit_profile(
                series, self.speed.value(), self.hub.value(), self.alpha.value(),
                self.turbine(), rho,
                self.availability.value() / 100.0 * (1.0 - self.losses.value() / 100.0))
        source = "NASA POWER" if weather else "synthetic"
        return HydrogenProfiles(pv_unit, wind_unit, source)

    def validatePage(self) -> bool:
        items = [("Latitude", self.lat), ("Longitude", self.lon)]
        if self.goal.pv.isChecked():
            items += [("Tilt", self.tilt), ("Azimuth", self.azimuth),
                      ("PV yield", self.pv_yield)]
        if self.goal.wind.isChecked():
            items += [("Wind speed", self.speed), ("Hub height", self.hub), ("Weibull k", self.k),
                      ("Shear exponent", self.alpha), ("Elevation", self.elevation),
                      ("Temperature", self.temperature), ("Availability", self.availability),
                      ("Other losses", self.losses)]
        return _warn(self, items)


class HydrogenPlantPage(StepPage):
    def __init__(self, goal: HydrogenGoalPage) -> None:
        super().__init__()
        self.goal = goal
        self.setTitle("3. Electrolyser and storage")
        self.setSubTitle("Electrolyser, compression, storage and water. The defaults are typical: change them if you have a datasheet.")
        d = HydrogenInputs()
        self.kwh = NumberField(d.kwh_per_kg_stack, 40, 80, 1, "kWh/kg", "hydrogen.efficiency")
        self.min_load = NumberField(d.min_load * 100, 0, 50, 0, "% of nominal", "hydrogen.dispatch")
        self.outlet = NumberField(d.outlet_bar, 1, 100, 0, "bar", "hydrogen.compression")
        self.storage_bar = NumberField(d.storage_bar, 1, 900, 0, "bar", "hydrogen.storage")
        self.days = NumberField(d.storage_days, 0, 60, 1, "days", "hydrogen.storage")
        self.water = NumberField(d.water_l_per_kg, 9, 30, 0, "L/kg", "hydrogen.water")
        self.cap = NumberField(d.grid_hours_cap, 1, 8760, 0, "full-load hours per year",
                               "hydrogen.dispatch")
        self.part_load = QCheckBox("Efficiency depends on the load")
        self.part_load.setChecked(True)
        self.aux = NumberField(d.aux_share * 100, 0, 30, 0, "% of nominal power",
                               "hydrogen.partload")
        self.gain = NumberField(d.stack_gain * 100, 0, 30, 0, "% at very low load",
                                "hydrogen.partload")
        self.degr = NumberField(0.2, 0, 2, 2, "% per 1000 hours", "hydrogen.ageing")
        self.tank_mode = QComboBox()
        self.tank_mode.addItems(["Days of autonomy (simple)",
                                 "Hour by hour from the production (constant offtake)"])
        self.cheapest = QCheckBox("Buy grid electricity in the cheapest hours (invented hourly prices)")
        self.cheapest.setChecked(True)
        form = QFormLayout()
        form.addRow("Consumption of stack and auxiliaries", self.kwh)
        form.addRow("Minimum load", self.min_load)
        form.addRow("Electrolyser outlet pressure", self.outlet)
        form.addRow("Storage pressure", self.storage_bar)
        form.addRow("Storage autonomy", self.days)
        form.addRow("Water consumption", self.water)
        form.addRow("Grid energy limit", self.cap)
        self.form = form
        deep = QGroupBox("Deeper models (more realistic, a bit slower to read)")
        df = QFormLayout(deep)
        df.addRow(self.part_load)
        df.addRow("Auxiliaries (pumps, cooling)", self.aux)
        df.addRow("Stack gain at part load", self.gain)
        df.addRow("Stack ageing", self.degr)
        df.addRow("Storage sizing", self.tank_mode)
        df.addRow(self.cheapest)
        self.deep_form = df
        box = QGroupBox("Electrolyser, compression and storage")
        box.setLayout(form)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(box)
        layout.addWidget(deep)
        layout.addWidget(_hint(
            "A PEM system needs about 50-58 kWh per kilogram, with a minimum load of 5-10 %. "
            "The grid limit says how many full-load hours a year the grid may supply: "
            "with 8000 the grid alone could run the plant, with 2000 it only tops up the "
            "renewables."))
        layout.addStretch(1)

    def initializePage(self) -> None:
        _show_row(self.form, self.cap, self.goal.grid.isChecked())
        self.cheapest.setVisible(self.goal.grid.isChecked())

    def validatePage(self) -> bool:
        items = [("Consumption", self.kwh), ("Minimum load", self.min_load),
                 ("Outlet pressure", self.outlet), ("Storage pressure", self.storage_bar),
                 ("Storage autonomy", self.days), ("Water", self.water),
                 ("Auxiliaries", self.aux), ("Stack gain", self.gain), ("Stack ageing", self.degr)]
        if self.goal.grid.isChecked():
            items.append(("Grid limit", self.cap))
        if not _warn(self, items):
            return False
        if self.storage_bar.value() < self.outlet.value():
            QMessageBox.warning(self, "Check the value",
                                "The storage pressure cannot be below the electrolyser outlet "
                                "pressure.")
            return False
        return True


class HydrogenCostPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = HydrogenInputs()
        self.setTitle("4. Costs and emissions")
        self.setSubTitle("Costs and emission factors. The defaults are round placeholders that give an order of magnitude: replace them with quotes and local prices.")

        def f(value, lo, hi, dec, unit, why="hydrogen.lcoh") -> NumberField:
            return NumberField(value, lo, hi, dec, unit, why)

        self.el_capex = f(d.electrolyser_capex_per_kw, 100, 10000, 0, "euro/kW")
        self.el_om = f(d.electrolyser_om_fraction * 100, 0, 15, 1, "% of CAPEX per year")
        self.stack_h = f(d.stack_hours, 5000, 200000, 0, "hours", "hydrogen.stack")
        self.stack_cost = f(d.stack_cost_fraction * 100, 0, 100, 0, "% of the electrolyser",
                            "hydrogen.stack")
        self.storage_capex = f(d.storage_capex_per_kg, 0, 5000, 0, "euro per kg stored")
        self.water_price = f(d.water_price_per_m3, 0, 50, 2, "euro/m3", "hydrogen.water")
        self.pv_capex = f(d.pv_capex_per_kwp, 100, 5000, 0, "euro/kWp")
        self.pv_om = f(d.pv_om_per_kwp, 0, 200, 1, "euro/kWp per year")
        self.wind_capex = f(d.wind_capex_per_kw, 100, 6000, 0, "euro/kW")
        self.wind_om = f(d.wind_om_per_kw, 0, 300, 1, "euro/kW per year")
        self.res_life = f(d.res_life_years, 5, 40, 0, "years")
        self.el_life = f(d.electrolyser_life_years, 5, 40, 0, "years")
        self.rate = f(d.discount_rate * 100, 0, 30, 1, "%")
        self.grid_price = f(d.grid_price_per_kwh, 0, 2, 3, "euro/kWh")
        self.grid_ef = f(d.grid_ef, 0, 2, 3, "kg CO2/kWh", "hydrogen.co2")
        self.pv_ef = f(d.pv_ef, 0, 0.5, 3, "kg CO2/kWh", "hydrogen.co2")
        self.wind_ef = f(d.wind_ef, 0, 0.5, 3, "kg CO2/kWh", "hydrogen.co2")
        self.grey = f(d.grey_h2_kg_co2_per_kg, 1, 30, 1, "kg CO2/kg", "hydrogen.co2")

        left = QGroupBox("Electrolyser, storage, water")
        lf = QFormLayout(left)
        lf.addRow("Electrolyser CAPEX", self.el_capex)
        lf.addRow("Operation and maintenance", self.el_om)
        lf.addRow("Stack life", self.stack_h)
        lf.addRow("Stack replacement cost", self.stack_cost)
        lf.addRow("Storage CAPEX", self.storage_capex)
        lf.addRow("Water price", self.water_price)
        lf.addRow("Electrolyser life", self.el_life)
        mid = QGroupBox("Electricity")
        mf = QFormLayout(mid)
        mf.addRow("PV CAPEX", self.pv_capex)
        mf.addRow("PV O&M", self.pv_om)
        mf.addRow("Wind CAPEX", self.wind_capex)
        mf.addRow("Wind O&M", self.wind_om)
        mf.addRow("Renewable plant life", self.res_life)
        mf.addRow("Discount rate", self.rate)
        mf.addRow("Grid price", self.grid_price)
        em = QGroupBox("Emissions (including construction)")
        ef = QFormLayout(em)
        ef.addRow("Grid", self.grid_ef)
        ef.addRow("PV", self.pv_ef)
        ef.addRow("Wind", self.wind_ef)
        ef.addRow("Reference: hydrogen from natural gas", self.grey)
        self._items = [(n, w) for n, w in (
            ("Electrolyser CAPEX", self.el_capex), ("O&M", self.el_om), ("Stack life", self.stack_h),
            ("Stack cost", self.stack_cost), ("Storage CAPEX", self.storage_capex),
            ("Water price", self.water_price), ("PV CAPEX", self.pv_capex), ("PV O&M", self.pv_om),
            ("Wind CAPEX", self.wind_capex), ("Wind O&M", self.wind_om),
            ("Renewable life", self.res_life), ("Electrolyser life", self.el_life),
            ("Discount rate", self.rate), ("Grid price", self.grid_price),
            ("Grid factor", self.grid_ef), ("PV factor", self.pv_ef),
            ("Wind factor", self.wind_ef), ("Reference hydrogen", self.grey))]

        row = QHBoxLayout()
        row.addWidget(left)
        row.addWidget(mid)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addLayout(row)
        layout.addWidget(em)
        self.country_bar = CountryBar({"grid_ef": self.grid_ef})
        self.country = self.country_bar.combo
        layout.insertWidget(0, self.country_bar)
        layout.addWidget(_hint(
            "Defaults are round orders of magnitude for a PEM system installed in Europe, not "
            "quotes. The whole renewable plant is charged to the hydrogen, also the curtailed "
            "energy. No incentives, taxes or grid fees."))
        layout.addStretch(1)

    def initializePage(self) -> None:
        self.country_bar.sync()

    def validatePage(self) -> bool:
        return _warn(self, self._items)


class HydrogenResultsPage(BaseResultsPage):
    topic_order = HYDROGEN_TOPIC_ORDER
    pdf_name = "RESize_hydrogen_report.pdf"
    has_excel = True
    _profiles = None

    def __init__(self, goal: HydrogenGoalPage, site: HydrogenSitePage,
                 plant: HydrogenPlantPage, costs: HydrogenCostPage) -> None:
        self.goal, self.site, self.plant, self.costs = goal, site, plant, costs
        super().__init__()
        self.setTitle("5. Results and design checks")

    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        g, p, c = self.goal, self.plant, self.costs
        inputs = HydrogenInputs(
            mode=g.mode(), use_pv=g.pv.isChecked(), use_wind=g.wind.isChecked(),
            use_grid=g.grid.isChecked(),
            h2_demand_kg_per_year=g.demand.value() if g.mode() == "demand" else 1.0,
            pv_kwp_per_kw_el=g.pv_ratio.value(), wind_kw_per_kw_el=g.wind_ratio.value(),
            pv_kwp=g.pv_kwp.value(), wind_kw=g.wind_kw.value(), electrolyser_kw=g.el_kw.value(),
            kwh_per_kg_stack=p.kwh.value(), min_load=p.min_load.value() / 100.0,
            outlet_bar=p.outlet.value(), storage_bar=p.storage_bar.value(),
            storage_days=p.days.value(), water_l_per_kg=p.water.value(),
            grid_hours_cap=p.cap.value() if g.grid.isChecked() else 1.0,
            part_load_model=p.part_load.isChecked(), aux_share=p.aux.value() / 100.0,
            stack_gain=p.gain.value() / 100.0, degradation_per_1000h=p.degr.value() / 100.0,
            storage_mode="hourly" if p.tank_mode.currentIndex() == 1 else "days",
            cheapest_hours_first=g.grid.isChecked() and p.cheapest.isChecked(),
            electrolyser_capex_per_kw=c.el_capex.value(),
            electrolyser_om_fraction=c.el_om.value() / 100.0, stack_hours=c.stack_h.value(),
            stack_cost_fraction=c.stack_cost.value() / 100.0,
            storage_capex_per_kg=c.storage_capex.value(), water_price_per_m3=c.water_price.value(),
            pv_capex_per_kwp=c.pv_capex.value(), pv_om_per_kwp=c.pv_om.value(),
            wind_capex_per_kw=c.wind_capex.value(), wind_om_per_kw=c.wind_om.value(),
            res_life_years=c.res_life.value(), electrolyser_life_years=c.el_life.value(),
            discount_rate=c.rate.value() / 100.0, grid_price_per_kwh=c.grid_price.value(),
            grid_ef=c.grid_ef.value(), pv_ef=c.pv_ef.value(), wind_ef=c.wind_ef.value(),
            grey_h2_kg_co2_per_kg=c.grey.value(),
        )
        profiles = self.site.profiles()
        if inputs.use_grid and inputs.cheapest_hours_first:
            profiles = replace(profiles, prices=h2.synthetic_price_profile(inputs.grid_price_per_kwh))
        self._profiles = profiles
        design = replace(size_hydrogen_plant(inputs, profiles),
                         sensitivity=hydrogen_sensitivity(inputs, profiles))
        findings = check_hydrogen_design(inputs, design)
        note = f"Site: lat {self.site.lat.value():.4f}, lon {self.site.lon.value():.4f}."
        light = build_hydrogen_report(inputs, design, findings, site_note=note, theme="light")
        screen = build_hydrogen_report(inputs, design, findings, site_note=note, theme="screen")
        return inputs, design, findings, light, screen

    def _flow(self):
        from resize_energy.report.flow_pictures import hydrogen_picture

        return hydrogen_picture(self._inputs, self._design)

    def _workbook(self):
        from resize_energy.report.excel_more import build_hydrogen_workbook

        return build_hydrogen_workbook(self._inputs, self._profiles, self._design)

    def _worked(self, key: str) -> str | None:
        return hydrogen_worked_example(key, self._inputs, self._design)

    def _context(self) -> str:
        return build_hydrogen_context(self._inputs, self._design, self._findings)

    def _charts(self) -> dict[str, ChartSpec]:
        return hydrogen_charts(self._inputs, self._design)
