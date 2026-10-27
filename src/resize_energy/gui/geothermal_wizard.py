"""Geothermal pages (PySide6): pathway and resource, plant, costs and emissions, results."""

from __future__ import annotations

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
    QWidget,
)

from resize_energy.core.geothermal_design import (
    PATHWAYS,
    PLANTS,
    GeothermalInputs,
    size_geothermal_plant,
)
from resize_energy.core.nasa_power import NasaPowerError, fetch_wind_climate
from resize_energy.gui.country import CountryBar
from resize_energy.gui.widgets import StepPage
from resize_energy.gui.wizard import BaseResultsPage, NumberField, _hint, first_error
from resize_energy.report.charts import ChartSpec, geothermal_charts
from resize_energy.report.html_report import build_geothermal_report
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.checker_geothermal import check_geothermal_design
from resize_energy.tutor.context_geothermal import build_geothermal_context
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.explanations_geothermal import GEOTHERMAL_TOPIC_ORDER, topics_for
from resize_energy.tutor.worked_geothermal import geothermal_worked_example

GEOTHERMAL_STEP_NAMES = ["Pathway and resource", "Plant and demand", "Prices and costs",
                         "Results and checks"]
PATHWAY_KEYS = list(PATHWAYS)
PLANT_KEYS = list(PLANTS)


def _warn(page: StepPage, items: list[tuple[str, NumberField]]) -> bool:
    error = first_error(items)
    if error:
        QMessageBox.warning(page, "Check the value", error)
        return False
    return True


def _show_row(form: QFormLayout, field: QWidget, visible: bool) -> None:
    label = form.labelForField(field)
    if label is not None:
        label.setVisible(visible)
    field.setVisible(visible)


class GeothermalResourcePage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = GeothermalInputs()
        self.setTitle("1. Pathway and resource")
        self.setSubTitle("Choose what the plant produces, then describe the hot water under "
                         "the ground: how hot it is and how much each well gives.")
        self.picker = QComboBox()
        for key in PATHWAY_KEYS:
            self.picker.addItem(PATHWAYS[key])
        self.picker.currentIndexChanged.connect(self._changed)
        self.temp = NumberField(d.reservoir_temp_c, 30, 400, 0, "degC", "geo.wells")
        self.flow = NumberField(d.flow_per_well_kg_s, 1, 500, 0, "kg/s per well", "geo.heat_power")
        self.lat = NumberField(45.07, -90, 90, 4, "deg N")
        self.lon = NumberField(7.69, -180, 180, 4, "deg E")
        self.ambient = NumberField(d.ambient_temp_c, -20, 40, 0, "degC", "geo.exergy")
        self.fetch_status = QLabel("")
        self.fetch_status.setWordWrap(True)
        fetch = QPushButton("Get the mean air temperature of the place (NASA POWER)")
        fetch.clicked.connect(self._fetch_temperature)
        self.gradient = NumberField(d.gradient_k_per_km, 10, 200, 0, "degC per km", "geo.wells")
        self.pressure = NumberField(d.pump_pressure_bar, 0, 100, 0, "bar", "geo.pumping")
        self.pump_eff = NumberField(d.pump_efficiency * 100, 20, 90, 0, "%", "geo.pumping")
        self.avail = NumberField(d.availability * 100, 50, 100, 0, "%", "geo.net_power")

        box = QGroupBox("Technology")
        bl = QVBoxLayout(box)
        bl.addWidget(self.picker)
        self.note = _hint("")
        bl.addWidget(self.note)
        res = QGroupBox("Resource")
        rf = QFormLayout(res)
        rf.addRow("Temperature of the water at the wellhead", self.temp)
        rf.addRow("Flow of one production well", self.flow)
        rf.addRow("Latitude (north positive)", self.lat)
        rf.addRow("Longitude (east positive)", self.lon)
        fetch_row = QHBoxLayout()
        fetch_row.addWidget(fetch)
        fetch_row.addStretch(1)
        rf.addRow(fetch_row)
        rf.addRow(self.fetch_status)
        rf.addRow("Mean ambient temperature", self.ambient)
        rf.addRow("Temperature gradient of the ground", self.gradient)
        pump = QGroupBox("Wells and pumps")
        pf = QFormLayout(pump)
        pf.addRow("Pressure rise of the pumps (per well pair)", self.pressure)
        pf.addRow("Pump efficiency", self.pump_eff)
        pf.addRow("Availability of the plant", self.avail)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(box)
        layout.addWidget(res)
        layout.addWidget(pump)
        layout.addWidget(_hint(
            "Temperature and flow of a well are only known after a test well, or from a "
            "study of the geology of the area: here they are your hypothesis. In a normal "
            "crust the temperature rises by about 30 degC per km; in volcanic areas much "
            "faster. 50 kg/s is a typical flow for a good low-temperature well."))
        layout.addStretch(1)
        self._changed(0)

    def pathway(self) -> str:
        return PATHWAY_KEYS[max(0, self.picker.currentIndex())]

    def _fetch_temperature(self) -> None:
        error = first_error([("Latitude", self.lat), ("Longitude", self.lon)])
        if error:
            self.fetch_status.setText(error)
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            climate = fetch_wind_climate(self.lat.value(), self.lon.value())
        except (NasaPowerError, ValueError) as exc:
            self.fetch_status.setText(f"Could not get the temperature ({exc}): type it by hand.")
            return
        finally:
            QApplication.restoreOverrideCursor()
        if climate.mean_temperature_c is None:
            self.fetch_status.setText("NASA POWER has no temperature for this place.")
            return
        self.ambient.set_value(round(climate.mean_temperature_c), "NASA POWER")
        self.fetch_status.setText(
            f"NASA POWER: mean air temperature {climate.mean_temperature_c:.1f} degC (it sets "
            "the depth of the wells and the exergy of the water).")

    def _changed(self, _index: int = 0) -> None:
        notes = {
            "heat": "A pair of wells (production and injection) feeds a heat network through "
                    "a heat exchanger. Sized on the heat demand.",
            "power": "The hot water drives a binary plant (below about 180 degC) or a flash "
                     "plant (above). Sized on the electricity demand.",
        }
        self.note.setText(notes[self.pathway()])

    def validatePage(self) -> bool:
        if not _warn(self, [("Temperature", self.temp), ("Flow", self.flow),
                            ("Ambient temperature", self.ambient), ("Gradient", self.gradient),
                            ("Pump pressure", self.pressure), ("Pump efficiency", self.pump_eff),
                            ("Availability", self.avail)]):
            return False
        if self.temp.value() <= self.ambient.value():
            QMessageBox.warning(self, "Check the value",
                                "The water must be hotter than the ambient temperature.")
            return False
        return True


class GeothermalPlantPage(StepPage):
    def __init__(self, resource: GeothermalResourcePage) -> None:
        super().__init__()
        d = GeothermalInputs()
        self.resource = resource
        self.setTitle("2. Plant and demand")
        self.setSubTitle("What the plant must supply and how the water is used after the "
                         "heat or the power has been taken from it.")
        self.heat = NumberField(d.annual_heat_demand_kwh, 0, 1e13, 0, "kWh per year", "geo.coverage")
        self.peak = NumberField(d.peak_heat_kw, 0, 1e8, 0, "kW", "geo.coverage")
        self.coverage = NumberField(d.coverage * 100, 1, 100, 0, "%", "geo.coverage")
        self.return_temp = NumberField(d.return_temp_c, 10, 150, 0, "degC", "geo.heat_power")
        self.hx = NumberField(d.exchanger_efficiency * 100, 50, 100, 0, "%", "geo.heat_power")
        self.electricity = NumberField(d.annual_electricity_demand_kwh, 0, 1e13, 0,
                                       "kWh per year", "geo.net_power")
        self.reinject = NumberField(d.reinjection_temp_c, 20, 200, 0, "degC", "geo.binary")
        self.plant = QComboBox()
        for key in PLANT_KEYS:
            self.plant.addItem(PLANTS[key])
        self.flash_util = NumberField(d.flash_utilization * 100, 5, 70, 0, "% of the exergy",
                                      "geo.flash")
        self.parasitic = NumberField(d.flash_parasitic * 100, 0, 30, 0, "% of gross power",
                                     "geo.flash")
        self.hours = NumberField(d.operating_hours, 1000, 8760, 0, "hours per year",
                                 "geo.net_power")

        self.form = QFormLayout()
        self.form.addRow("Annual heat demand", self.heat)
        self.form.addRow("Peak heat load", self.peak)
        self.form.addRow("Share of the heat to cover", self.coverage)
        self.form.addRow("Return temperature of the network", self.return_temp)
        self.form.addRow("Heat exchanger and network efficiency", self.hx)
        self.form.addRow("Annual electricity demand", self.electricity)
        self.form.addRow("Temperature of the water reinjected", self.reinject)
        self.form.addRow("Type of power plant", self.plant)
        self.form.addRow("Flash plant: utilization efficiency", self.flash_util)
        self.form.addRow("Flash plant: own consumption", self.parasitic)
        self.form.addRow("Operating hours", self.hours)
        box = QGroupBox("Demand and plant")
        box.setLayout(self.form)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(box)
        layout.addWidget(_hint(
            "A heat network with low return temperatures (40-50 degC) takes more heat from "
            "every kilogram of water. For a power plant, the water must not be cooled too "
            "much before it goes back down: silica could plug the wells. The flash values "
            "are for a single-flash plant at 200 degC."))
        layout.addStretch(1)

    def initializePage(self) -> None:
        heat = self.resource.pathway() == "heat"
        for field in (self.heat, self.peak, self.coverage, self.return_temp, self.hx):
            _show_row(self.form, field, heat)
        for field in (self.electricity, self.reinject, self.plant, self.flash_util,
                      self.parasitic, self.hours):
            _show_row(self.form, field, not heat)

    def plant_key(self) -> str:
        return PLANT_KEYS[max(0, self.plant.currentIndex())]

    def _items(self) -> list[tuple[str, NumberField]]:
        if self.resource.pathway() == "heat":
            return [("Heat demand", self.heat), ("Peak load", self.peak),
                    ("Coverage", self.coverage), ("Return temperature", self.return_temp),
                    ("Exchanger efficiency", self.hx)]
        return [("Electricity demand", self.electricity), ("Reinjection temperature", self.reinject),
                ("Utilization", self.flash_util), ("Own consumption", self.parasitic),
                ("Operating hours", self.hours)]

    def validatePage(self) -> bool:
        if not _warn(self, self._items()):
            return False
        heat = self.resource.pathway() == "heat"
        if heat and (self.heat.value() <= 0 or self.peak.value() <= 0):
            QMessageBox.warning(self, "Check the value",
                                "Heat demand and peak load must be greater than zero.")
            return False
        if heat and self.return_temp.value() >= self.resource.temp.value():
            QMessageBox.warning(self, "Check the value",
                                "The return temperature must be lower than the temperature of "
                                "the water from the wells.")
            return False
        if not heat and self.electricity.value() <= 0:
            QMessageBox.warning(self, "Check the value",
                                "The power plant is sized on the electricity demand: enter a "
                                "value above zero.")
            return False
        if not heat and self.reinject.value() >= self.resource.temp.value():
            QMessageBox.warning(self, "Check the value",
                                "The reinjection temperature must be lower than the "
                                "temperature of the water from the wells.")
            return False
        return True


class GeothermalCostPage(StepPage):
    def __init__(self, resource: GeothermalResourcePage) -> None:
        super().__init__()
        d = GeothermalInputs()
        self.resource = resource
        self.setTitle("3. Prices and costs")
        self.setSubTitle("What the plant costs and what its energy is worth. The defaults are "
                         "literature values: replace them with quotes and your tariffs.")
        self.drill = NumberField(d.drilling_eur_per_m, 0, 20000, 0, "euro per metre of well",
                                 "geo.wells")
        self.surface = NumberField(d.surface_eur_per_kw_th, 0, 5000, 0, "euro per kW of heat",
                                   "geo.economics")
        self.capex_el = NumberField(d.capex_per_kw_el, 0, 50000, 0, "euro per kW net",
                                    "geo.economics")
        self.om = NumberField(d.om_fraction * 100, 0, 20, 1, "% of CAPEX per year", "geo.economics")
        self.life = NumberField(d.life_years, 5, 100, 0, "years", "geo.economics")
        self.rate = NumberField(d.discount_rate * 100, 0, 30, 1, "%", "geo.economics")
        self.heat_price = NumberField(d.heat_price_eur_per_kwh, 0, 2, 3, "euro/kWh of heat",
                                      "geo.economics")
        self.retail = NumberField(d.retail_price, 0.001, 2, 3, "euro/kWh bought", "geo.economics")
        self.export = NumberField(d.export_price, 0, 2, 3, "euro/kWh sold", "geo.economics")
        self.ef = NumberField(d.grid_ef, 0, 2, 3, "kg CO2/kWh", "geo.co2")
        self.lifecycle = NumberField(d.lifecycle_g_per_kwh, 0, 500, 0, "g CO2/kWh", "geo.co2")
        self.ref_eff = NumberField(d.reference_heat_efficiency * 100, 30, 110, 0, "%", "geo.co2")
        self.ref_ef = NumberField(d.reference_heat_ef, 0, 1, 3, "kg CO2/kWh of fuel", "geo.co2")

        self.cost_form = QFormLayout()
        self.cost_form.addRow("Drilling, one well", self.drill)
        self.cost_form.addRow("Surface equipment", self.surface)
        self.cost_form.addRow("Installed cost of the power plant, wells included", self.capex_el)
        self.cost_form.addRow("Operation and maintenance", self.om)
        self.cost_form.addRow("Life", self.life)
        cost = QGroupBox("Plant cost")
        cost.setLayout(self.cost_form)
        self.price_form = QFormLayout()
        self.price_form.addRow("Value of the heat you replace", self.heat_price)
        self.price_form.addRow("Price you pay for electricity", self.retail)
        self.price_form.addRow("Price paid for the energy you sell", self.export)
        self.price_form.addRow("Discount rate", self.rate)
        prices = QGroupBox("Energy prices and finance")
        prices.setLayout(self.price_form)
        self.co2_form = QFormLayout()
        self.co2_form.addRow("Grid emission factor", self.ef)
        self.co2_form.addRow("Life-cycle emissions of the power plant", self.lifecycle)
        self.co2_form.addRow("Efficiency of the boiler it replaces", self.ref_eff)
        self.co2_form.addRow("Emission factor of its fuel", self.ref_ef)
        co2 = QGroupBox("Emissions")
        co2.setLayout(self.co2_form)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        self.country_bar = CountryBar({"electricity": self.retail, "export": self.export,
                                       "heat": self.heat_price, "grid_ef": self.ef})
        self.country = self.country_bar.combo
        layout.addWidget(self.country_bar)
        layout.addWidget(cost)
        layout.addWidget(prices)
        layout.addWidget(co2)
        layout.addWidget(_hint(
            "Drilling is the largest cost of geothermal energy and the main risk: the "
            "default is a value of the MIT study (2004 dollars), without exploration or "
            "failed wells. Ask a driller for a quote."))
        layout.addStretch(1)

    def initializePage(self) -> None:
        self.country_bar.sync()
        heat = self.resource.pathway() == "heat"
        for f in (self.drill, self.surface):
            _show_row(self.cost_form, f, heat)
        _show_row(self.cost_form, self.capex_el, not heat)
        _show_row(self.price_form, self.heat_price, heat)
        _show_row(self.price_form, self.retail, not heat)
        _show_row(self.price_form, self.export, not heat)
        _show_row(self.co2_form, self.lifecycle, not heat)
        _show_row(self.co2_form, self.ref_eff, heat)
        _show_row(self.co2_form, self.ref_ef, heat)

    def _items(self) -> list[tuple[str, NumberField]]:
        items = [("O&M", self.om), ("Life", self.life), ("Discount rate", self.rate),
                 ("Emission factor", self.ef)]
        if self.resource.pathway() == "heat":
            items += [("Drilling", self.drill), ("Surface equipment", self.surface),
                      ("Heat value", self.heat_price), ("Boiler efficiency", self.ref_eff),
                      ("Fuel emission factor", self.ref_ef)]
        else:
            items += [("Plant cost", self.capex_el), ("Price paid", self.retail),
                      ("Price received", self.export), ("Life-cycle emissions", self.lifecycle)]
        return items

    def validatePage(self) -> bool:
        return _warn(self, self._items())


class GeothermalResultsPage(BaseResultsPage):
    """Results of the geothermal design; the Why? list follows the chosen pathway."""

    topic_order = GEOTHERMAL_TOPIC_ORDER
    pdf_name = "RESize_geothermal_report.pdf"
    has_excel = True

    def __init__(self, resource: GeothermalResourcePage, plant: GeothermalPlantPage,
                 costs: GeothermalCostPage) -> None:
        self.resource, self.plant, self.costs = resource, plant, costs
        super().__init__()
        self.setTitle("4. Results and design checks")

    def initializePage(self) -> None:
        self.topic_order = topics_for(self.resource.pathway())
        self.topics.clear()
        for key in self.topic_order:
            self.topics.addItem(EXPLANATIONS[key]["title"])
        super().initializePage()

    def _inputs_from_pages(self) -> GeothermalInputs:
        r, p, c = self.resource, self.plant, self.costs
        return GeothermalInputs(
            pathway=r.pathway(), reservoir_temp_c=r.temp.value(),
            flow_per_well_kg_s=r.flow.value(), ambient_temp_c=r.ambient.value(),
            gradient_k_per_km=r.gradient.value(), pump_pressure_bar=r.pressure.value(),
            pump_efficiency=r.pump_eff.value() / 100.0, availability=r.avail.value() / 100.0,
            annual_heat_demand_kwh=p.heat.value(), peak_heat_kw=p.peak.value(),
            coverage=p.coverage.value() / 100.0, return_temp_c=p.return_temp.value(),
            exchanger_efficiency=p.hx.value() / 100.0,
            annual_electricity_demand_kwh=p.electricity.value(),
            reinjection_temp_c=p.reinject.value(), plant=p.plant_key(),
            flash_utilization=p.flash_util.value() / 100.0,
            flash_parasitic=p.parasitic.value() / 100.0, operating_hours=p.hours.value(),
            reference_heat_efficiency=c.ref_eff.value() / 100.0,
            reference_heat_ef=c.ref_ef.value(), grid_ef=c.ef.value(),
            lifecycle_g_per_kwh=c.lifecycle.value(),
            drilling_eur_per_m=c.drill.value(), surface_eur_per_kw_th=c.surface.value(),
            capex_per_kw_el=c.capex_el.value(), om_fraction=c.om.value() / 100.0,
            life_years=c.life.value(), discount_rate=c.rate.value() / 100.0,
            heat_price_eur_per_kwh=c.heat_price.value(), retail_price=c.retail.value(),
            export_price=c.export.value())

    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        inputs = self._inputs_from_pages()
        design = size_geothermal_plant(inputs)
        findings = check_geothermal_design(inputs, design)
        light = build_geothermal_report(inputs, design, findings, theme="light")
        screen = build_geothermal_report(inputs, design, findings, theme="screen")
        return inputs, design, findings, light, screen

    def preview_job(self):
        """Read the pages now (on the main thread); the returned function sizes the design."""
        inputs = self._inputs_from_pages()
        def job():
            design = size_geothermal_plant(inputs)
            return design, check_geothermal_design(inputs, design)

        return job

    def _flow(self):
        from resize_energy.report.flow_pictures import geothermal_picture

        return geothermal_picture(self._inputs, self._design)

    def _workbook(self):
        from resize_energy.report.excel_hydro_geo import build_geothermal_workbook

        return build_geothermal_workbook(self._inputs, self._design)

    def _worked(self, key: str) -> str | None:
        return geothermal_worked_example(key, self._inputs, self._design)

    def _context(self) -> str:
        return build_geothermal_context(self._inputs, self._design, self._findings)

    def _charts(self) -> dict[str, ChartSpec]:
        return geothermal_charts(self._inputs, self._design)
