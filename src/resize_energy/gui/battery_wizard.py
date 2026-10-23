"""Battery storage pages (PySide6): plant and load, site, battery, prices, results."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QMessageBox,
    QVBoxLayout,
)

from resize_energy.core.battery import LOAD_KINDS
from resize_energy.core.battery_design import (
    MODES,
    BatteryInputs,
    BatteryProfiles,
    battery_sensitivity,
    size_battery,
)
from resize_energy.gui.biomass_wizard import _show_row
from resize_energy.gui.country import CountryBar
from resize_energy.gui.hydrogen_wizard import HydrogenSitePage
from resize_energy.gui.widgets import StepPage
from resize_energy.gui.wizard import BaseResultsPage, NumberField, _hint, first_error
from resize_energy.report.charts import ChartSpec, battery_charts
from resize_energy.report.html_report import build_battery_report
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.checker_battery import check_battery_design
from resize_energy.tutor.context_battery import build_battery_context
from resize_energy.tutor.explanations_battery import BATTERY_TOPIC_ORDER
from resize_energy.tutor.worked_battery import battery_worked_example

BATTERY_STEP_NAMES = ["Plant and load", "Site and profiles", "The battery",
                      "Prices and costs", "Results and checks"]
MODE_KEYS = list(MODES)
LOAD_KEYS = list(LOAD_KINDS)


def _warn(page: StepPage, items: list[tuple[str, NumberField]]) -> bool:
    error = first_error(items)
    if error:
        QMessageBox.warning(page, "Check the value", error)
        return False
    return True


class BatteryGoalPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("1. Plant and load")
        self.setSubTitle("A battery stores the surplus of your plant for the hours when the plant produces less than you consume. Tell me the plant and when you consume.")
        self.pv = QCheckBox("Photovoltaic")
        self.pv.setChecked(True)
        self.wind = QCheckBox("Wind")
        for box in (self.pv, self.wind):
            box.stateChanged.connect(self._changed)
        self.pv_kwp = NumberField(5, 0, 1e6, 1, "kWp", "battery.dispatch")
        self.wind_kw = NumberField(0, 0, 1e6, 1, "kW", "battery.dispatch")
        self.demand = NumberField(6000, 1, 1e9, 0, "kWh per year", "battery.load")
        self.kind = QComboBox()
        for key in LOAD_KEYS:
            self.kind.addItem(LOAD_KINDS[key])

        src = QGroupBox("Generation (any combination)")
        sl = QHBoxLayout(src)
        for box in (self.pv, self.wind):
            sl.addWidget(box)
        sl.addStretch(1)
        self.form = QFormLayout()
        self.form.addRow("Photovoltaic plant", self.pv_kwp)
        self.form.addRow("Wind plant", self.wind_kw)
        plant = QGroupBox("Plant size")
        plant.setLayout(self.form)
        load = QGroupBox("Consumption")
        lf = QFormLayout(load)
        lf.addRow("Yearly consumption", self.demand)
        lf.addRow("Type of consumer", self.kind)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(src)
        layout.addWidget(plant)
        layout.addWidget(load)
        layout.addWidget(_hint(
            "What matters for a battery is not only how much you consume but when. A home uses "
            "energy in the morning and evening, when the sun is low: the battery has a lot to do. "
            "An office consumes at midday, when PV produces: it needs little storage. The shape "
            "of the consumption is a typical one for the type you choose."))
        layout.addStretch(1)
        self._changed()

    def load_kind(self) -> str:
        return LOAD_KEYS[max(0, self.kind.currentIndex())]

    def _changed(self, *_args) -> None:
        _show_row(self.form, self.pv_kwp, self.pv.isChecked())
        _show_row(self.form, self.wind_kw, self.wind.isChecked())

    def validatePage(self) -> bool:
        if not (self.pv.isChecked() or self.wind.isChecked()):
            QMessageBox.warning(self, "Check the value", "Choose PV, wind or both.")
            return False
        items = [("Yearly consumption", self.demand)]
        if self.pv.isChecked():
            items.append(("PV plant", self.pv_kwp))
        if self.wind.isChecked():
            items.append(("Wind plant", self.wind_kw))
        return _warn(self, items)


class BatterySitePage(HydrogenSitePage):
    """Same site and hourly-profile page as the hydrogen module (it only reads pv/wind)."""

    def __init__(self, goal: BatteryGoalPage) -> None:
        super().__init__(goal)  # type: ignore[arg-type]
        self.setSubTitle("Where is it? Press the button for real hourly sun and wind data, or keep the defaults to explore: hour by hour, the sun and wind decide how much surplus there is to store.")

    def battery_profiles(self) -> BatteryProfiles:
        p = self.profiles()
        return BatteryProfiles(p.pv_unit, p.wind_unit, p.source)


class BatteryPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = BatteryInputs()
        self.setTitle("3. The battery")
        self.setSubTitle("How do you want to size it, and what are the characteristics of the cells? The defaults are those of a modern lithium iron phosphate (LFP) home battery.")
        self.mode_picker = QComboBox()
        for key in MODE_KEYS:
            self.mode_picker.addItem(MODES[key])
        self.mode_picker.currentIndexChanged.connect(self._changed)
        self.capacity = NumberField(d.capacity_kwh, 0, 1e6, 1, "kWh", "battery.capacity")
        self.target = NumberField(d.target_self_sufficiency * 100, 1, 99, 0, "% of the consumption",
                                  "battery.selfuse")
        self.c_rate = NumberField(d.c_rate, 0.05, 5, 2, "kW per kWh", "battery.capacity")
        self.eta = NumberField(d.eta_roundtrip * 100, 50, 100, 0, "%", "battery.efficiency")
        self.dod = NumberField(d.usable_fraction * 100, 30, 100, 0, "%", "battery.capacity")
        self.health = NumberField(d.health * 100, 50, 100, 0, "%", "battery.capacity")
        self.cycles = NumberField(d.cycle_life, 500, 50000, 0, "full cycles", "battery.life")
        self.calendar = NumberField(d.calendar_life_years, 3, 40, 0, "years", "battery.life")

        top = QGroupBox("Starting point")
        tl = QFormLayout(top)
        tl.addRow(self.mode_picker)
        self.form = tl
        tl.addRow("Capacity", self.capacity)
        tl.addRow("Target self-sufficiency", self.target)
        cells = QGroupBox("Characteristics")
        cf = QFormLayout(cells)
        cf.addRow("Power / capacity (C-rate)", self.c_rate)
        cf.addRow("Round-trip efficiency", self.eta)
        cf.addRow("Usable fraction (depth of discharge)", self.dod)
        cf.addRow("State of health, average over the life", self.health)
        cf.addRow("Cycle life", self.cycles)
        cf.addRow("Calendar life", self.calendar)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(top)
        layout.addWidget(cells)
        layout.addWidget(_hint(
            "A battery is not only kWh but also kW: with a C-rate of 0.5 a full charge takes two "
            "hours. In every case you will see a curve with the results for many sizes: it "
            "shows why the biggest battery is rarely the best."))
        layout.addStretch(1)
        self._changed()

    def mode(self) -> str:
        return MODE_KEYS[max(0, self.mode_picker.currentIndex())]

    def _changed(self, *_args) -> None:
        _show_row(self.form, self.capacity, self.mode() == "given")
        _show_row(self.form, self.target, self.mode() == "target")

    def validatePage(self) -> bool:
        items = [("C-rate", self.c_rate), ("Efficiency", self.eta), ("Usable fraction", self.dod),
                 ("State of health", self.health), ("Cycle life", self.cycles),
                 ("Calendar life", self.calendar)]
        items.append(("Capacity", self.capacity) if self.mode() == "given"
                     else ("Target", self.target))
        return _warn(self, items)


class BatteryCostPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = BatteryInputs()
        self.setTitle("4. Prices and costs")
        self.setSubTitle("What the battery costs and what the electricity is worth. The defaults are round placeholders: replace them with quotes and your tariff.")
        self.capex_kwh = NumberField(d.capex_per_kwh, 0, 5000, 0, "euro per kWh", "battery.economics")
        self.capex_kw = NumberField(d.capex_per_kw, 0, 2000, 0, "euro per kW", "battery.economics")
        self.om = NumberField(d.om_fraction * 100, 0, 10, 1, "% of CAPEX per year", "battery.economics")
        self.retail = NumberField(d.retail_price, 0.001, 2, 3, "euro/kWh bought", "battery.economics")
        self.export = NumberField(d.export_price, 0, 2, 3, "euro/kWh sold", "battery.economics")
        self.rate = NumberField(d.discount_rate * 100, 0, 30, 1, "%", "battery.economics")
        self.ef = NumberField(d.grid_ef, 0, 2, 3, "kg CO2/kWh", "battery.co2")
        box = QGroupBox("Battery cost")
        bf = QFormLayout(box)
        bf.addRow("Cost per kWh of capacity", self.capex_kwh)
        bf.addRow("Cost per kW of power (converter)", self.capex_kw)
        bf.addRow("Operation and maintenance", self.om)
        el = QGroupBox("Electricity and finance")
        ef = QFormLayout(el)
        ef.addRow("Price you pay", self.retail)
        ef.addRow("Price you are paid for the surplus", self.export)
        ef.addRow("Discount rate", self.rate)
        ef.addRow("Grid emission factor", self.ef)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(box)
        layout.addWidget(el)
        self.country_bar = CountryBar({"electricity": self.retail, "export": self.export, "grid_ef": self.ef})
        self.country = self.country_bar.combo
        layout.insertWidget(0, self.country_bar)
        layout.addWidget(_hint(
            "The gain of a battery is the difference between the price you pay and the price "
            "you are paid for the surplus: if the two are close, the battery cannot repay itself. "
            "No incentives or taxes are included."))
        layout.addStretch(1)

    def initializePage(self) -> None:
        self.country_bar.sync()

    def validatePage(self) -> bool:
        return _warn(self, [
            ("Cost per kWh", self.capex_kwh), ("Cost per kW", self.capex_kw), ("O&M", self.om),
            ("Price paid", self.retail), ("Price received", self.export),
            ("Discount rate", self.rate), ("Emission factor", self.ef)])


class BatteryResultsPage(BaseResultsPage):
    topic_order = BATTERY_TOPIC_ORDER
    pdf_name = "RESize_battery_report.pdf"
    has_excel = True
    _profiles = None

    def __init__(self, goal: BatteryGoalPage, site: BatterySitePage, battery: BatteryPage,
                 costs: BatteryCostPage) -> None:
        self.goal, self.site, self.battery, self.costs = goal, site, battery, costs
        super().__init__()

    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        g, b, c = self.goal, self.battery, self.costs
        inputs = BatteryInputs(
            annual_demand_kwh=g.demand.value(), load_kind=g.load_kind(),
            use_pv=g.pv.isChecked(), use_wind=g.wind.isChecked(),
            pv_kwp=g.pv_kwp.value() if g.pv.isChecked() else 0.0,
            wind_kw=g.wind_kw.value() if g.wind.isChecked() else 0.0,
            mode=b.mode(), capacity_kwh=b.capacity.value(),
            target_self_sufficiency=b.target.value() / 100.0, c_rate=b.c_rate.value(),
            eta_roundtrip=b.eta.value() / 100.0, usable_fraction=b.dod.value() / 100.0,
            health=b.health.value() / 100.0, cycle_life=b.cycles.value(),
            calendar_life_years=b.calendar.value(), capex_per_kwh=c.capex_kwh.value(),
            capex_per_kw=c.capex_kw.value(), om_fraction=c.om.value() / 100.0,
            retail_price=c.retail.value(), export_price=c.export.value(),
            discount_rate=c.rate.value() / 100.0, grid_ef=c.ef.value(),
        )
        profiles = self.site.battery_profiles()
        self._profiles = profiles
        design = size_battery(inputs, profiles)
        design = replace(design, sensitivity=battery_sensitivity(inputs, profiles,
                                                                 design.capacity_kwh))
        findings = check_battery_design(inputs, design)
        note = f"Site: lat {self.site.lat.value():.4f}, lon {self.site.lon.value():.4f}."
        light = build_battery_report(inputs, design, findings, site_note=note, theme="light")
        screen = build_battery_report(inputs, design, findings, site_note=note, theme="screen")
        return inputs, design, findings, light, screen

    def _workbook(self):
        from resize_energy.report.excel_more import build_battery_workbook

        return build_battery_workbook(self._inputs, self._profiles, self._design)

    def _worked(self, key: str) -> str | None:
        return battery_worked_example(key, self._inputs, self._design)

    def _context(self) -> str:
        return build_battery_context(self._inputs, self._design, self._findings)

    def _charts(self) -> dict[str, ChartSpec]:
        return battery_charts(self._inputs, self._design)
