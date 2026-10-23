"""Wind sizing pages (PySide6): site and resource, demand and losses, turbine, results."""

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

from resize_energy.core.nasa_power import NasaPowerError, fetch_wind_climate
from resize_energy.core.turbine_library import SOURCE, load_library
from resize_energy.core.wind_design import TurbineSpec, WindInputs, size_wind_plant
from resize_energy.gui.widgets import StepPage
from resize_energy.gui.wizard import BaseResultsPage, NumberField, _hint, first_error
from resize_energy.report.charts import ChartSpec, wind_charts
from resize_energy.report.html_report import build_wind_report
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.checker_wind import check_wind_design
from resize_energy.tutor.context_wind import build_wind_context
from resize_energy.tutor.explanations_wind import WIND_TOPIC_ORDER
from resize_energy.tutor.worked_wind import wind_worked_example

WIND_STEP_NAMES = ["Site and wind resource", "Demand and losses", "Turbine and layout",
                   "Costs and savings", "Results and checks"]


def _warn(page: StepPage, items: list[tuple[str, NumberField]]) -> bool:
    error = first_error(items)
    if error:
        QMessageBox.warning(page, "Check the value", error)
        return False
    return True


class WindSitePage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("1. Site and wind resource")
        self.setSubTitle("Where is it? Press the button to get the wind speed of this place, or type your own measurement: wind speed is the biggest driver of the energy.")

        self.lat = NumberField(45.07, -90, 90, 4, "deg N")
        self.lon = NumberField(7.69, -180, 180, 4, "deg E")
        self.speed = NumberField(6.0, 0.5, 20, 2, "m/s", "wind.resource")
        self.ref_height = NumberField(50, 5, 300, 0, "m")
        self.k = NumberField(2.0, 1.0, 5.0, 2, "", "wind.weibull")
        self.alpha = NumberField(0.14, 0.0, 0.5, 2, "", "wind.shear")
        self.elevation = NumberField(100, -400, 5000, 0, "m a.s.l.", "wind.air_density")
        self.temperature = NumberField(12, -30, 40, 0, "degC", "wind.air_density")

        self.status = QLabel("")
        self.status.setWordWrap(True)
        fetch = QPushButton("Get mean wind speed from NASA POWER")
        fetch.clicked.connect(self._fetch)
        fetch_row = QHBoxLayout()
        fetch_row.addWidget(fetch)
        fetch_row.addStretch(1)

        place = QFormLayout()
        place.addRow("Latitude (north positive)", self.lat)
        place.addRow("Longitude (east positive)", self.lon)

        resource = QGroupBox("Wind resource")
        form = QFormLayout(resource)
        form.addRow("Mean wind speed", self.speed)
        form.addRow("... measured at height", self.ref_height)
        form.addRow("Weibull shape k", self.k)
        form.addRow("Shear exponent alpha", self.alpha)

        air = QGroupBox("Air density")
        af = QFormLayout(air)
        af.addRow("Elevation", self.elevation)
        af.addRow("Mean temperature", self.temperature)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addLayout(place)
        layout.addLayout(fetch_row)
        layout.addWidget(self.status)
        layout.addWidget(_hint(
            "NASA POWER gives a smooth, long-term value at 50 m (resolution about 50 km): good "
            "for a first estimate, not for hills or coasts. If you have a mast measurement or "
            "an atlas value (e.g. Global Wind Atlas), type it below."))
        layout.addWidget(resource)
        layout.addWidget(air)
        layout.addStretch(1)

    def _items(self) -> list[tuple[str, NumberField]]:
        return [("Latitude", self.lat), ("Longitude", self.lon), ("Mean wind speed", self.speed),
                ("Reference height", self.ref_height), ("Weibull k", self.k),
                ("Shear exponent", self.alpha), ("Elevation", self.elevation),
                ("Temperature", self.temperature)]

    def _fetch(self) -> None:
        error = first_error([("Latitude", self.lat), ("Longitude", self.lon)])
        if error:
            self.status.setText(error)
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            climate = fetch_wind_climate(self.lat.value(), self.lon.value())
        except (NasaPowerError, ValueError) as exc:
            self.status.setText(f"Could not get NASA POWER data: {exc}\nType the values below.")
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.speed.set_value(round(climate.mean_speed_50m_ms, 2), "NASA POWER")
        self.ref_height.set_value(50, "NASA POWER")
        text = f"NASA POWER: mean wind speed {climate.mean_speed_50m_ms:.2f} m/s at 50 m"
        if climate.mean_temperature_c is not None:
            self.temperature.set_value(round(climate.mean_temperature_c), "NASA POWER")
            text += f", mean temperature {climate.mean_temperature_c:.1f} degC"
        if climate.elevation_m is not None:
            self.elevation.set_value(round(climate.elevation_m), "NASA POWER")
            text += f", elevation {climate.elevation_m:.0f} m"
        self.status.setText(text + ".")

    def validatePage(self) -> bool:
        return _warn(self, self._items())


class WindLoadPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("2. Demand and losses")
        self.setSubTitle("How much energy do you need, and what share should wind cover? Losses (wake, availability) reduce what the turbines deliver.")
        self.demand = NumberField(10_000_000, 1, 1e12, 0, "kWh per year")
        self.coverage = NumberField(100, 1, 100, 0, "%", "wind.number_of_turbines")
        self.availability = NumberField(97, 50, 100, 1, "%", "wind.losses")
        self.losses = NumberField(10, 0, 50, 1, "%", "wind.losses")

        form = QFormLayout()
        form.addRow("Annual electricity demand", self.demand)
        form.addRow("Share of the demand to cover with wind", self.coverage)
        form.addRow("Turbine availability", self.availability)
        form.addRow("Other losses (wake, electrical, ...)", self.losses)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(_hint(
            "Availability is typically 96-98 %. Other losses group wakes, electrical losses, "
            "icing and curtailment: 10-15 % is common for a first-pass design. A 100 % target "
            "does not consider the hour-by-hour match of wind and consumption."))
        layout.addStretch(1)

    def validatePage(self) -> bool:
        return _warn(self, [("Annual demand", self.demand), ("Coverage", self.coverage),
                            ("Availability", self.availability), ("Other losses", self.losses)])


class WindTurbinePage(StepPage):
    GENERIC = "Generic turbine (type the datasheet values)"

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("3. Turbine and layout")
        self.setSubTitle("Pick a turbine from the list (its real power curve is used) or type the datasheet values.")
        t = TurbineSpec()
        self.library = load_library()
        self._selected = None  # LibraryTurbine in use, or None for the generic curve

        self.picker = QComboBox()
        self.picker.setMaxVisibleItems(20)
        self.picker.addItem(self.GENERIC)
        for turbine in self.library:
            self.picker.addItem(turbine.label)
        self.picker.currentIndexChanged.connect(self._picked)
        self.curve_note = QLabel("")
        self.curve_note.setWordWrap(True)
        self.curve_note.setObjectName("hint")

        self.power = NumberField(t.rated_power_kw, 0.5, 20000, 1, "kW")
        self.rotor = NumberField(t.rotor_diameter_m, 1, 250, 1, "m", "wind.cp_betz")
        self.hub = NumberField(t.hub_height_m, 5, 300, 0, "m", "wind.shear")
        self.cut_in = NumberField(t.cut_in_ms, 0.5, 8, 1, "m/s", "wind.power_curve")
        self.rated = NumberField(t.rated_speed_ms, 4, 25, 1, "m/s", "wind.power_curve")
        self.cut_out = NumberField(t.cut_out_ms, 10, 40, 1, "m/s", "wind.power_curve")
        self.crosswind = NumberField(5, 1, 20, 1, "D", "wind.spacing")
        self.downwind = NumberField(7, 1, 30, 1, "D", "wind.spacing")
        for field in (self.power, self.rotor, self.cut_in, self.rated, self.cut_out):
            field.edit.textEdited.connect(self._edited)  # typing means: not the library curve

        pick_box = QGroupBox("Turbine model")
        pf = QVBoxLayout(pick_box)
        pf.addWidget(self.picker)
        pf.addWidget(self.curve_note)

        box = QGroupBox("Datasheet values")
        form = QFormLayout(box)
        form.addRow("Rated power", self.power)
        form.addRow("Rotor diameter D", self.rotor)
        form.addRow("Hub height", self.hub)
        form.addRow("Cut-in wind speed", self.cut_in)
        form.addRow("Rated wind speed", self.rated)
        form.addRow("Cut-out wind speed", self.cut_out)
        self.wake = QCheckBox("Calculate the wake losses (Jensen model, wind rose)")
        self.per_row = NumberField(0, 0, 100, 0, "turbines (0 = about a square)", "wind.rose")
        self.stagger = QCheckBox("Stagger the rows")
        self.stagger.setChecked(True)
        self.decay = NumberField(0.075, 0.02, 0.12, 3, "0.075 land, 0.04 sea", "wind.wake")
        self.prevailing = NumberField(270, 0, 359, 0, "deg the wind comes from (270 = west)",
                                      "wind.rose")
        self.conc = NumberField(1.0, 0, 5, 1, "0 = all directions equal", "wind.rose")
        lay = QGroupBox("Layout")
        lf = QFormLayout(lay)
        lf.addRow("Spacing across the wind", self.crosswind)
        lf.addRow("Spacing along the wind", self.downwind)
        lf.addRow(self.wake)
        lf.addRow("Turbines per row", self.per_row)
        lf.addRow(self.stagger)
        lf.addRow("Wake decay constant k", self.decay)
        lf.addRow("Prevailing wind", self.prevailing)
        lf.addRow("Rose concentration", self.conc)
        self._items = [("Rated power", self.power), ("Rotor diameter", self.rotor),
                       ("Hub height", self.hub), ("Cut-in speed", self.cut_in),
                       ("Rated speed", self.rated), ("Cut-out speed", self.cut_out),
                       ("Spacing across", self.crosswind), ("Spacing along", self.downwind),
                       ("Turbines per row", self.per_row), ("Wake decay", self.decay),
                       ("Prevailing wind", self.prevailing), ("Rose concentration", self.conc)]

        layout = QVBoxLayout(self)
        layout.addWidget(pick_box)
        layout.addWidget(box)
        layout.addWidget(lay)
        layout.addWidget(_hint(
            "Library curves come from " + SOURCE + "; most are theoretical, not measured on "
            "site. With the generic option the power rises with the cube of the speed between "
            "cut-in and rated. Spacing is in rotor diameters D: 3-5 D across and 5-9 D along "
            "the prevailing wind is a usual compromise."))
        layout.addStretch(1)
        self._picked(0)

    def _picked(self, index: int) -> None:
        if index <= 0:
            self._selected = None
            self.curve_note.setText("The generic curve built from the speeds below is used.")
            return
        turbine = self.library[index - 1]
        self._selected = turbine
        self.power.set_value(turbine.rated_power_kw)
        self.rotor.set_value(turbine.rotor_diameter_m)
        if turbine.hub_height_m:
            self.hub.set_value(turbine.hub_height_m)
        self.cut_in.set_value(turbine.cut_in_ms)
        self.rated.set_value(turbine.rated_speed_ms)
        self.cut_out.set_value(turbine.cut_out_ms)
        self.curve_note.setText(
            f"The tabulated power curve of this turbine ({len(turbine.curve)} points) is used. "
            "Hub height and spacing can be changed freely; editing the other values switches "
            "back to the generic curve."
        )

    def _edited(self, *_args) -> None:
        if self._selected is not None:
            self.picker.blockSignals(True)
            self.picker.setCurrentIndex(0)
            self.picker.blockSignals(False)
            self._selected = None
            self.curve_note.setText("Values edited: the generic curve built from them is used.")

    def spec(self) -> TurbineSpec:
        hub = self.hub.value()
        if self._selected is not None:
            return replace(self._selected.to_spec(), hub_height_m=hub)
        return TurbineSpec(
            name="User turbine", rated_power_kw=self.power.value(),
            rotor_diameter_m=self.rotor.value(), hub_height_m=hub,
            cut_in_ms=self.cut_in.value(), rated_speed_ms=self.rated.value(),
            cut_out_ms=self.cut_out.value(),
        )

    def validatePage(self) -> bool:
        if not _warn(self, self._items):
            return False
        if not self.cut_in.value() < self.rated.value() < self.cut_out.value():
            QMessageBox.warning(self, "Check the value",
                                "Speeds must satisfy: cut-in < rated < cut-out.")
            return False
        return True


class WindResultsPage(BaseResultsPage):
    """Results of the wind design."""

    topic_order = WIND_TOPIC_ORDER
    pdf_name = "RESize_wind_report.pdf"
    has_excel = True

    def __init__(self, site: WindSitePage, load: WindLoadPage, turbine: WindTurbinePage,
                 costs) -> None:
        self.site, self.load, self.turbine, self.costs = site, load, turbine, costs
        super().__init__()
        self.setTitle("5. Results and design checks")

    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        inputs = WindInputs(
            annual_demand_kwh=self.load.demand.value(),
            mean_speed_ref_ms=self.site.speed.value(),
            ref_height_m=self.site.ref_height.value(),
            weibull_k=self.site.k.value(),
            shear_alpha=self.site.alpha.value(),
            elevation_m=self.site.elevation.value(),
            temperature_c=self.site.temperature.value(),
            coverage=self.load.coverage.value() / 100.0,
            availability=self.load.availability.value() / 100.0,
            other_losses=self.load.losses.value() / 100.0,
            crosswind_spacing_d=self.turbine.crosswind.value(),
            downwind_spacing_d=self.turbine.downwind.value(),
            wake_model=self.turbine.wake.isChecked(),
            turbines_per_row=int(self.turbine.per_row.value()),
            stagger_rows=self.turbine.stagger.isChecked(), wake_decay=self.turbine.decay.value(),
            prevailing_direction_deg=self.turbine.prevailing.value(),
            rose_concentration=self.turbine.conc.value(),
            turbine=self.turbine.spec(), economics=self.costs.inputs(),
        )
        design = size_wind_plant(inputs)
        findings = check_wind_design(inputs, design)
        note = f"Site: lat {self.site.lat.value():.4f}, lon {self.site.lon.value():.4f}."
        light = build_wind_report(inputs, design, findings, site_note=note, theme="light")
        dark = build_wind_report(inputs, design, findings, site_note=note, theme="screen")
        return inputs, design, findings, light, dark

    def _flow(self):
        from resize_energy.report.flow_pictures import wind_picture

        return wind_picture(self._inputs, self._design)

    def _workbook(self):
        from resize_energy.report.excel import build_wind_workbook

        return build_wind_workbook(self._inputs, self._design)

    def _worked(self, key: str) -> str | None:
        return wind_worked_example(key, self._inputs, self._design)

    def _context(self) -> str:
        return build_wind_context(self._inputs, self._design, self._findings)

    def _charts(self) -> dict[str, ChartSpec]:
        return wind_charts(self._inputs, self._design)
