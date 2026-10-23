"""Solar thermal pages (PySide6): loads, site, collectors and tank, costs, results."""

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
)

from resize_energy.core.pvgis import PVGISError, fetch_pvcalc
from resize_energy.core.solar_thermal import COLLECTORS
from resize_energy.core.solar_thermal_design import (
    SolarThermalInputs,
    size_solar_thermal,
)
from resize_energy.gui.widgets import StepPage
from resize_energy.gui.wizard import BaseResultsPage, NumberField, _hint, first_error
from resize_energy.report.charts import ChartSpec, solar_charts
from resize_energy.report.html_report import build_solar_report
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.checker_solar import check_solar_design
from resize_energy.tutor.context_solar import build_solar_context
from resize_energy.tutor.explanations_solar import SOLAR_TOPIC_ORDER
from resize_energy.tutor.worked_solar import solar_worked_example

SOLAR_STEP_NAMES = ["What you need", "Site and sun", "Collectors and tank",
                    "Costs and prices", "Results and checks"]


def _warn(page: StepPage, items: list[tuple[str, NumberField]]) -> bool:
    error = first_error(items)
    if error:
        QMessageBox.warning(page, "Check the value", error)
        return False
    return True


class SolarLoadPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = SolarThermalInputs()
        self.setTitle("1. What do you need?")
        self.setSubTitle("Hot water, cooling, or both. Put 0 in the one you do not need.")
        self.litres = NumberField(d.dhw_litres_per_day, 0, 1e6, 0, "litres per day", "solar.load")
        self.t_use = NumberField(d.t_use_c, 30, 90, 0, "degC", "solar.load")
        self.cooling = NumberField(3000, 0, 1e8, 0, "kWh of cold per year", "solar.adsorption")

        water = QGroupBox("Hot water")
        wf = QFormLayout(water)
        wf.addRow("Hot water used per day", self.litres)
        wf.addRow("Temperature at the tap", self.t_use)
        cool = QGroupBox("Cooling with an adsorption chiller (optional)")
        cf = QFormLayout(cool)
        cf.addRow("Cooling needed per year", self.cooling)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(water)
        layout.addWidget(cool)
        layout.addWidget(_hint(
            "A family of four uses about 150-250 litres a day; a small hotel or a gym, a few "
            "thousand. An adsorption chiller makes chilled water from the hot water of the "
            "collectors, with almost no electricity: it makes sense when you need cooling in "
            "summer, exactly when the sun is strongest. The default 3,000 kWh/year is a small "
            "office; set it to 0 for hot water only. Press the (?) next to the field to see how "
            "it works."))
        layout.addStretch(1)

    def validatePage(self) -> bool:
        if not _warn(self, [("Hot water", self.litres), ("Temperature", self.t_use),
                            ("Cooling", self.cooling)]):
            return False
        if self.litres.value() <= 0 and self.cooling.value() <= 0:
            QMessageBox.warning(self, "Check the value",
                                "Give a hot-water demand, a cooling demand, or both.")
            return False
        return True


class SolarSitePage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = SolarThermalInputs()
        self.setTitle("2. Site and sun")
        self.setSubTitle("Where is it, and how much sun reaches the collectors? Press the button to get the value from PVGIS, or type your own.")
        self.lat = NumberField(45.07, -90, 90, 4, "deg N")
        self.lon = NumberField(7.69, -180, 180, 4, "deg E")
        self.tilt = NumberField(40, 0, 90, 0, "deg")
        self.azimuth = NumberField(0, -180, 180, 0, "deg")
        self.irr = NumberField(d.irradiation_kwh_m2, 300, 3500, 0, "kWh/m2 per year",
                               "solar.resource")
        self.t_mean = NumberField(d.t_mean_c, -20, 35, 0, "degC", "solar.resource")
        self.t_amp = NumberField(d.t_season_amp_c, 0, 25, 0, "K", "solar.resource")
        self.status = QLabel("")
        self.status.setWordWrap(True)
        fetch = QPushButton("Get irradiation from PVGIS")
        fetch.clicked.connect(self._fetch)
        fetch_row = QHBoxLayout()
        fetch_row.addWidget(fetch)
        fetch_row.addStretch(1)

        place = QFormLayout()
        place.addRow("Latitude (north positive)", self.lat)
        place.addRow("Longitude (east positive)", self.lon)
        place.addRow("Tilt of the collectors", self.tilt)
        place.addRow("Azimuth (0 = south, 90 = west, -90 = east)", self.azimuth)
        sun = QGroupBox("Sun and air")
        sf = QFormLayout(sun)
        sf.addRow("Irradiation on the collector plane", self.irr)
        sf.addRow("Mean air temperature of the year", self.t_mean)
        sf.addRow("Summer-winter swing (half the difference)", self.t_amp)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addLayout(place)
        layout.addLayout(fetch_row)
        layout.addWidget(self.status)
        layout.addWidget(sun)
        layout.addWidget(_hint(
            "A tilt equal to the latitude favours the whole year; a steeper tilt favours winter "
            "(good for heating), a flatter one summer (good for cooling). The temperature "
            "numbers set the heat losses and the cold-water temperature: Turin is about 13 degC "
            "with a swing of 11 K, Rome 16 and 8, Palermo 18 and 7."))
        layout.addStretch(1)

    def _query_items(self) -> list[tuple[str, NumberField]]:
        return [("Latitude", self.lat), ("Longitude", self.lon), ("Tilt", self.tilt),
                ("Azimuth", self.azimuth)]

    def _fetch(self) -> None:
        error = first_error(self._query_items())
        if error:
            self.status.setText(error)
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = fetch_pvcalc(self.lat.value(), self.lon.value(), self.tilt.value(),
                                  self.azimuth.value(), 14.0)
        except (PVGISError, ValueError) as exc:
            self.status.setText(f"Could not get PVGIS data: {exc}\nYou can type the value by hand.")
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.irr.set_value(result.annual_irradiation_kwh_m2, "PVGIS")
        self.status.setText(f"PVGIS: {result.annual_irradiation_kwh_m2:,.0f} kWh/m2 per year on "
                            "the collector plane.")

    def validatePage(self) -> bool:
        return _warn(self, self._query_items() + [
            ("Irradiation", self.irr), ("Mean temperature", self.t_mean),
            ("Temperature swing", self.t_amp)])


class SolarCollectorPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = SolarThermalInputs()
        self.setTitle("3. Collectors and tank")
        self.setSubTitle("The type of collector, how many square metres, and the tank. The chiller values matter only if you asked for cooling.")
        self.kind = QComboBox()
        for c in COLLECTORS.values():
            self.kind.addItem(c.name)
        self.kind.setCurrentIndex(list(COLLECTORS).index("flat"))
        c0 = COLLECTORS["flat"]
        self.eta0 = NumberField(c0.eta0, 0.3, 0.95, 2, "", "solar.collector")
        self.a1 = NumberField(c0.a1, 0.0, 30, 2, "W/(m2 K)", "solar.collector")
        self.a2 = NumberField(c0.a2, 0.0, 0.1, 3, "W/(m2 K2)", "solar.collector")
        self.cost = NumberField(c0.cost_per_m2, 0, 5000, 0, "euro per m2", "solar.economics")
        self.mode = QComboBox()
        self.mode.addItems(["I choose the area", "Find the area for a target solar fraction"])
        self.area = NumberField(d.area_m2, 0.5, 5000, 1, "m2", "solar.area")
        self.target = NumberField(d.target_fraction * 100, 5, 95, 0, "%", "solar.solar_fraction")
        self.store = NumberField(d.store_l_per_m2, 10, 300, 0, "litres per m2", "solar.store")
        self.loop = NumberField(d.loop_loss * 100, 0, 40, 0, "%", "solar.simulation")
        self.cop = NumberField(d.cop_nominal, 0.2, 1.1, 2, "", "solar.chiller_cop")
        self.t_min = NumberField(d.t_drive_min_c, 40, 90, 0, "degC", "solar.chiller_cop")
        self.t_nom = NumberField(d.t_drive_nominal_c, 50, 110, 0, "degC", "solar.chiller_cop")
        self.chiller = NumberField(0, 0, 5000, 1, "kW of cooling (0 = automatic)",
                                   "solar.adsorption")
        self.kind.currentIndexChanged.connect(self._picked)

        coll = QGroupBox("Collector")
        cf = QFormLayout(coll)
        cf.addRow("Type", self.kind)
        cf.addRow("Zero-loss efficiency eta0", self.eta0)
        cf.addRow("Heat-loss coefficient a1", self.a1)
        cf.addRow("Heat-loss coefficient a2", self.a2)
        cf.addRow("Installed cost of the collectors", self.cost)
        size = QGroupBox("Size")
        zf = QFormLayout(size)
        zf.addRow("How to size", self.mode)
        zf.addRow("Collector area", self.area)
        zf.addRow("Target solar fraction", self.target)
        zf.addRow("Tank volume", self.store)
        zf.addRow("Pipe and pump losses", self.loop)
        chill = QGroupBox("Adsorption chiller")
        hf = QFormLayout(chill)
        hf.addRow("Thermal COP at nominal drive", self.cop)
        hf.addRow("Minimum drive temperature", self.t_min)
        hf.addRow("Nominal drive temperature", self.t_nom)
        hf.addRow("Chiller size", self.chiller)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addWidget(coll)
        layout.addWidget(size)
        layout.addWidget(chill)
        layout.addWidget(_hint(
            "Take eta0, a1 and a2 from the Solar Keymark certificate of the collector. Flat "
            "plates suit hot water; evacuated tubes keep their efficiency at the 70-90 degC a "
            "chiller needs. The silica-gel chillers on the market have a thermal COP of about "
            "0.5-0.65 and start at about 55-60 degC: use the datasheet."))
        layout.addStretch(1)

    def kind_key(self) -> str:
        return list(COLLECTORS)[self.kind.currentIndex()]

    def _picked(self, _index: int) -> None:
        c = COLLECTORS[self.kind_key()]
        self.eta0.set_value(c.eta0)
        self.a1.set_value(c.a1)
        self.a2.set_value(c.a2)
        self.cost.set_value(c.cost_per_m2)

    def validatePage(self) -> bool:
        if not _warn(self, [
                ("eta0", self.eta0), ("a1", self.a1), ("a2", self.a2), ("Cost", self.cost),
                ("Area", self.area), ("Target", self.target), ("Tank volume", self.store),
                ("Losses", self.loop), ("COP", self.cop), ("Minimum drive", self.t_min),
                ("Nominal drive", self.t_nom), ("Chiller", self.chiller)]):
            return False
        if self.t_min.value() >= self.t_nom.value():
            QMessageBox.warning(self, "Check the value",
                                "The minimum drive temperature must be below the nominal one.")
            return False
        return True


class SolarCostPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = SolarThermalInputs()
        self.setTitle("4. Costs and prices")
        self.setSubTitle("What the rest of the plant costs and what the heat you replace is worth. The defaults are round placeholders: replace them with quotes and your tariff.")
        key = "solar.economics"
        self.store = NumberField(d.store_cost_per_litre, 0, 50, 2, "euro per litre", key)
        self.fixed = NumberField(d.fixed_cost, 0, 1e7, 0, "euro", key)
        self.chiller = NumberField(d.chiller_cost_per_kw, 0, 20000, 0, "euro per kW of cooling", key)
        self.om = NumberField(d.om_fraction * 100, 0, 10, 1, "% of CAPEX per year", key)
        self.heat = NumberField(d.heat_price, 0.001, 2, 3, "euro per kWh of heat", key)
        self.elec = NumberField(d.electricity_price, 0.001, 2, 3, "euro/kWh", key)
        self.comp = NumberField(d.compressor_cop, 1, 10, 1, "", key)
        self.life = NumberField(d.life_years, 1, 40, 0, "years", key)
        self.rate = NumberField(d.discount_rate * 100, 0, 30, 1, "%", key)
        self.heat_ef = NumberField(d.heat_ef_kg_per_kwh, 0, 2, 3, "kg CO2/kWh of heat", "solar.co2")
        self.grid_ef = NumberField(d.grid_ef_kg_per_kwh, 0, 2, 3, "kg CO2/kWh", "solar.co2")

        plant = QGroupBox("Rest of the plant")
        pf = QFormLayout(plant)
        pf.addRow("Storage tank", self.store)
        pf.addRow("Controller, pumps, piping, labour", self.fixed)
        pf.addRow("Adsorption chiller (with heat rejection)", self.chiller)
        pf.addRow("Operation and maintenance", self.om)
        pf.addRow("Lifetime", self.life)
        price = QGroupBox("Prices and finance")
        mf = QFormLayout(price)
        mf.addRow("Heat from the backup boiler", self.heat)
        mf.addRow("Electricity", self.elec)
        mf.addRow("COP of the compressor chiller you replace", self.comp)
        mf.addRow("Discount rate", self.rate)
        co2 = QGroupBox("Carbon")
        cf = QFormLayout(co2)
        cf.addRow("Backup heat (natural gas about 0.23)", self.heat_ef)
        cf.addRow("Grid electricity", self.grid_ef)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addWidget(plant)
        layout.addWidget(price)
        layout.addWidget(co2)
        layout.addWidget(_hint(
            "The saving is the backup heat you do not buy, plus (with cooling) the electricity "
            "of the compressor chiller that the adsorption chiller replaces. No incentives or "
            "taxes: in many countries they change the result a lot."))
        layout.addStretch(1)

    def validatePage(self) -> bool:
        return _warn(self, [
            ("Tank", self.store), ("Fixed cost", self.fixed), ("Chiller", self.chiller),
            ("O&M", self.om), ("Heat price", self.heat), ("Electricity", self.elec),
            ("Compressor COP", self.comp), ("Lifetime", self.life), ("Discount rate", self.rate),
            ("Heat emissions", self.heat_ef), ("Grid emissions", self.grid_ef)])


class SolarResultsPage(BaseResultsPage):
    topic_order = SOLAR_TOPIC_ORDER
    pdf_name = "RESize_solar_thermal_report.pdf"

    def __init__(self, load: SolarLoadPage, site: SolarSitePage, coll: SolarCollectorPage,
                 costs: SolarCostPage) -> None:
        self.load, self.site, self.coll, self.costs = load, site, coll, costs
        super().__init__()
        self.setTitle("5. Results and design checks")

    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        ld, st, cp, ct = self.load, self.site, self.coll, self.costs
        inputs = SolarThermalInputs(
            dhw_litres_per_day=ld.litres.value(), t_use_c=ld.t_use.value(),
            cooling_kwh_per_year=ld.cooling.value(),
            latitude_deg=st.lat.value(), irradiation_kwh_m2=st.irr.value(),
            t_mean_c=st.t_mean.value(), t_season_amp_c=st.t_amp.value(),
            collector=cp.kind_key(), eta0=cp.eta0.value(), a1=cp.a1.value(), a2=cp.a2.value(),
            collector_cost_per_m2=cp.cost.value(),
            mode="given" if cp.mode.currentIndex() == 0 else "target",
            area_m2=cp.area.value(), target_fraction=cp.target.value() / 100.0,
            store_l_per_m2=cp.store.value(), loop_loss=cp.loop.value() / 100.0,
            chiller_kw=cp.chiller.value(), cop_nominal=cp.cop.value(),
            t_drive_min_c=cp.t_min.value(), t_drive_nominal_c=cp.t_nom.value(),
            store_cost_per_litre=ct.store.value(), fixed_cost=ct.fixed.value(),
            chiller_cost_per_kw=ct.chiller.value(), om_fraction=ct.om.value() / 100.0,
            heat_price=ct.heat.value(), electricity_price=ct.elec.value(),
            compressor_cop=ct.comp.value(), life_years=ct.life.value(),
            discount_rate=ct.rate.value() / 100.0, heat_ef_kg_per_kwh=ct.heat_ef.value(),
            grid_ef_kg_per_kwh=ct.grid_ef.value(),
        )
        design = size_solar_thermal(inputs)
        findings = check_solar_design(inputs, design)
        note = f"Site: lat {st.lat.value():.4f}, lon {st.lon.value():.4f}."
        light = build_solar_report(inputs, design, findings, site_note=note, theme="light")
        dark = build_solar_report(inputs, design, findings, site_note=note, theme="screen")
        return inputs, design, findings, light, dark

    def _worked(self, key: str) -> str | None:
        return solar_worked_example(key, self._inputs, self._design)

    def _context(self) -> str:
        return build_solar_context(self._inputs, self._design, self._findings)

    def _charts(self) -> dict[str, ChartSpec]:
        return solar_charts(self._inputs, self._design)
