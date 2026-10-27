"""Wind sizing pages (PySide6): site and resource, demand and losses, turbine, results."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from resize_energy.core.nasa_power import NasaPowerError, fetch_wind_climate
from resize_energy.core.satellite import fetch_satellite
from resize_energy.core.site_files import (
    SiteFileError,
    SiteShape,
    compare_with_typed,
    exclusions_from_file,
    site_from_file,
)
from resize_energy.core.turbine_library import SOURCE, load_library
from resize_energy.core.wind_design import TurbineSpec, WindInputs, size_wind_plant
from resize_energy.core.wind_rose import WindRose, fetch_wind_rose
from resize_energy.gui.widgets import StepPage
from resize_energy.gui.wizard import BaseResultsPage, NumberField, _hint, first_error
from resize_energy.report.charts import ChartSpec, wind_charts
from resize_energy.report.html_report import build_wind_report
from resize_energy.report.layout_art import layout_window
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.checker_wind import check_wind_design
from resize_energy.tutor.context_wind import build_wind_context
from resize_energy.tutor.explanations_wind import WIND_TOPIC_ORDER
from resize_energy.tutor.worked_wind import wind_worked_example

WIND_STEP_NAMES = ["Site and wind resource", "Demand and losses", "Turbine and layout",
                   "Costs and savings", "Results and checks"]


def _show_row(form: QFormLayout, field: QWidget, visible: bool) -> None:
    """Show or hide a form row (label and field together)."""
    label = form.labelForField(field)
    if label is not None:
        label.setVisible(visible)
    field.setVisible(visible)


def compass(deg: float) -> str:
    names = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W",
             "WNW", "NW", "NNW")
    return names[int(((deg % 360.0) + 11.25) // 22.5) % 16]


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

        self.lat = NumberField(45.07, -90, 90, 5, "deg N")
        self.lon = NumberField(7.69, -180, 180, 5, "deg E")
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
        self._rose: WindRose | None = None
        rose_button = QPushButton("Get the wind rose from NASA POWER (3 years, hourly)")
        rose_button.clicked.connect(self._fetch_rose)
        self.rose_clear = QPushButton("Use a typed rose instead")
        self.rose_clear.clicked.connect(self._clear_rose)
        self.rose_clear.setVisible(False)
        rose_row = QHBoxLayout()
        rose_row.addWidget(rose_button)
        rose_row.addWidget(self.rose_clear)
        rose_row.addStretch(1)
        self.rose_status = QLabel("")
        self.rose_status.setWordWrap(True)

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
        layout.addLayout(rose_row)
        layout.addWidget(self.rose_status)
        layout.addWidget(_hint(
            "NASA POWER gives a smooth, long-term value at 50 m (resolution about 50 km): good "
            "for a first estimate, not for hills or coasts. If you have a mast measurement or "
            "an atlas value (e.g. Global Wind Atlas), type it below. The wind rose says from "
            "which directions the wind blows and how hard: the wake model and the layout of "
            "the turbines use it (it can take half a minute to download)."))
        layout.addWidget(resource)
        layout.addWidget(air)
        layout.addStretch(1)
        self._rose_changed()

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

    def _fetch_rose(self) -> None:
        error = first_error([("Latitude", self.lat), ("Longitude", self.lon)])
        if error:
            self.rose_status.setText(error)
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            rose = fetch_wind_rose(self.lat.value(), self.lon.value())
        except (NasaPowerError, ValueError) as exc:
            self.rose_status.setText(
                f"Could not get the wind rose: {exc}\nYou can type a prevailing direction and a "
                "concentration in the turbine step instead.")
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._rose = rose
        self._rose_changed()

    def _clear_rose(self) -> None:
        self._rose = None
        self._rose_changed()

    def _rose_changed(self) -> None:
        rose = self._rose
        self.rose_clear.setVisible(rose is not None)
        if rose is None:
            self.rose_status.setText("No wind rose downloaded: the turbine step asks for a "
                                     "prevailing direction and a concentration.")
            return
        top = max(range(rose.sectors), key=lambda i: rose.frequency[i])
        self.rose_status.setText(
            f"{rose.source}: {rose.hours:,} hours of {', '.join(str(y) for y in rose.years)}. "
            f"The wind energy comes mainly from {compass(rose.prevailing_deg())} "
            f"({rose.prevailing_deg():.0f} deg); the most frequent sector is "
            f"{compass(top * 360.0 / rose.sectors)} ({rose.frequency[top]:.0%} of the hours).")

    def rose(self) -> WindRose | None:
        return self._rose

    def restore_rose(self, rose: WindRose | None) -> None:
        """Called when a saved project is opened."""
        self._rose = rose
        self._rose_changed()

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
    GRID, PLACED = "Regular grid: I set the spacing", "The program places the turbines in my site"

    def __init__(self, site: WindSitePage | None = None) -> None:
        super().__init__()
        self.site = site
        self.setTitle("3. Turbine and layout")
        self.setSubTitle("Pick a turbine from the list (its real power curve is used) or type the datasheet values.")
        t = TurbineSpec()
        self.library = load_library()
        self._selected = None  # LibraryTurbine in use, or None for the generic curve
        self._shape: SiteShape | None = None   # boundary and exclusion zones from a file

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
        self.layout_mode = QComboBox()
        self.layout_mode.addItems([self.GRID, self.PLACED])
        self.layout_mode.currentIndexChanged.connect(self._layout_changed)
        self.site_width = NumberField(2500, 50, 100000, 0, "m (across)", "wind.layout")
        self.site_length = NumberField(2500, 50, 100000, 0, "m (along)", "wind.layout")
        self.site_rotation = NumberField(0, 0, 359, 0, "deg: where the length points (0 = north)",
                                         "wind.layout")
        self.min_spacing = NumberField(3.0, 1.0, 10, 1, "D (closest two turbines)", "wind.layout")
        self.shape_load = QPushButton("Load the site boundary (KML, KMZ, GeoJSON)...")
        self.shape_load.clicked.connect(self._load_shape)
        self.excl_load = QPushButton("Add exclusion zones...")
        self.excl_load.clicked.connect(self._load_exclusions)
        self.shape_clear = QPushButton("Use a rectangle instead")
        self.shape_clear.clicked.connect(self._clear_shape)
        self.shape_status = QLabel("")
        self.shape_status.setWordWrap(True)
        self.shape_status.setObjectName("hint")
        self.setback = NumberField(0, 0, 2000, 0, "m kept from the boundary and the zones",
                                   "wind.layout")
        self.shape_box = QWidget()
        sb = QVBoxLayout(self.shape_box)
        sb.setContentsMargins(0, 0, 0, 0)
        buttons = QHBoxLayout()
        for b in (self.shape_load, self.excl_load, self.shape_clear):
            buttons.addWidget(b)
        buttons.addStretch(1)
        sb.addLayout(buttons)
        sb.addWidget(self.shape_status)
        self.satellite = QCheckBox("Show a satellite picture under the layout map (needs internet)")
        self.satellite.setChecked(True)
        self.rose_note = QLabel("")
        self.rose_note.setWordWrap(True)
        self.rose_note.setObjectName("hint")
        self.lay_form = QFormLayout()
        lay = QGroupBox("Layout")
        lf = self.lay_form
        lay.setLayout(lf)
        lf.addRow("Who decides where the turbines stand?", self.layout_mode)
        lf.addRow(self.shape_box)
        lf.addRow("Site width", self.site_width)
        lf.addRow("Site length", self.site_length)
        lf.addRow("Direction of the length", self.site_rotation)
        lf.addRow("Setback", self.setback)
        lf.addRow("Minimum distance", self.min_spacing)
        lf.addRow("Spacing across the wind", self.crosswind)
        lf.addRow("Spacing along the wind", self.downwind)
        lf.addRow(self.wake)
        lf.addRow("Turbines per row", self.per_row)
        lf.addRow(self.stagger)
        lf.addRow("Wake decay constant k", self.decay)
        lf.addRow(self.satellite)
        lf.addRow(self.rose_note)
        lf.addRow("Prevailing wind", self.prevailing)
        lf.addRow("Rose concentration", self.conc)
        self._items = [("Rated power", self.power), ("Rotor diameter", self.rotor),
                       ("Hub height", self.hub), ("Cut-in speed", self.cut_in),
                       ("Rated speed", self.rated), ("Cut-out speed", self.cut_out),
                       ("Wake decay", self.decay), ("Prevailing wind", self.prevailing),
                       ("Rose concentration", self.conc)]

        layout = QVBoxLayout(self)
        layout.addWidget(pick_box)
        layout.addWidget(box)
        layout.addWidget(lay)
        layout.addWidget(_hint(
            "Library curves come from " + SOURCE + "; most are theoretical, not measured on "
            "site. With the generic option the power rises with the cube of the speed between "
            "cut-in and rated. Spacing is in rotor diameters D: 3-5 D across and 5-9 D along "
            "the prevailing wind is a usual compromise. If you let the program place the "
            "turbines, give the rectangle of land you have and the closest two turbines may "
            "stand: it moves them to lose the least energy to the wakes of the wind rose."))
        layout.addStretch(1)
        self._picked(0)
        self._shape_changed()

    def placed(self) -> bool:
        return self.layout_mode.currentIndex() == 1

    def _layout_changed(self, _index: int = 0) -> None:
        placed = self.placed()
        rose = self.site.rose() if self.site is not None else None
        form = self.lay_form
        rectangle = placed and self._shape is None
        for f in (self.site_width, self.site_length, self.site_rotation):
            _show_row(form, f, rectangle)
        for f in (self.shape_box, self.min_spacing):
            _show_row(form, f, placed)
        _show_row(form, self.setback, placed and self._shape is not None)
        self.excl_load.setEnabled(self._shape is not None)
        self.shape_clear.setVisible(self._shape is not None)
        for f in (self.crosswind, self.downwind, self.per_row):
            _show_row(form, f, not placed)
        self.wake.setVisible(not placed)
        self.stagger.setVisible(not placed)
        _show_row(form, self.decay, True)
        # a typed rose only when no measured rose is available
        typed = rose is None
        _show_row(form, self.prevailing, typed or not placed)
        _show_row(form, self.conc, typed)
        self.rose_note.setVisible(not typed)
        if rose is not None:
            self.rose_note.setText(
                f"Wind rose of the site ({rose.source}, {rose.hours:,} hours): the wake model "
                f"uses it. The wind energy comes mainly from {rose.prevailing_deg():.0f} deg"
                + ("." if placed else ", which sets the direction of the rows: change it below "
                   "if you want."))

    # --- the land: boundary and exclusion zones from a file --------------------------------
    def shape(self) -> SiteShape | None:
        return self._shape

    def _pick_file(self, title: str) -> tuple[bytes, str] | None:
        path, _ = QFileDialog.getOpenFileName(
            self, title, "", "Site files (*.kml *.kmz *.geojson *.json);;All files (*)")
        if not path:
            return None
        try:
            with open(path, "rb") as handle:
                return handle.read(), path
        except OSError as exc:
            self.shape_status.setText(f"The file cannot be read: {exc.strerror or exc}")
            return None

    def _load_shape(self) -> None:
        picked = self._pick_file("Site boundary (a polygon)")
        if picked is None:
            return
        data, path = picked
        try:
            shape = site_from_file(data, path)
        except SiteFileError as exc:
            self.shape_status.setText(f"Could not use the file: {exc}")
            return
        self._shape = shape
        verdict = ""
        if self.site is not None:        # the centre of the site is the origin of the map
            try:
                verdict = compare_with_typed(shape, self.site.lat.value(), self.site.lon.value())
            except ValueError:
                verdict = ""
            self.site.lat.set_value(round(shape.lat, 5), "site file")
            self.site.lon.set_value(round(shape.lon, 5), "site file")
        self._shape_changed()
        if verdict:
            self.shape_status.setText(self.shape_status.text() + "\n" + verdict)

    def _load_exclusions(self) -> None:
        if self._shape is None:
            return
        picked = self._pick_file("Zones to avoid (polygons)")
        if picked is None:
            return
        data, path = picked
        try:
            rings = exclusions_from_file(data, path, self._shape.lat, self._shape.lon)
        except SiteFileError as exc:
            self.shape_status.setText(f"Could not use the file: {exc}")
            return
        self._shape = SiteShape(self._shape.lat, self._shape.lon, self._shape.boundary,
                                self._shape.exclusions + rings, self._shape.name)
        self._shape_changed()

    def _clear_shape(self) -> None:
        self._shape = None
        self._shape_changed()

    def restore_shape(self, shape: SiteShape | None) -> None:
        """Called when a saved project is opened."""
        self._shape = shape
        self._shape_changed()

    def _shape_changed(self) -> None:
        shape = self._shape
        if shape is None:
            self.shape_status.setText(
                "A rectangle is used. Load the real boundary of your land (and the zones to "
                "avoid: houses, roads, protected areas) from a KML, KMZ or GeoJSON file, for "
                "instance drawn in Google Earth.")
        else:
            from resize_energy.core.site_files import ring_area

            area = ring_area(shape.boundary) / 1e6
            self.shape_status.setText(
                f"Boundary of {len(shape.boundary)} corners, {area:.2f} km2, centred on "
                f"{shape.lat:.5f}, {shape.lon:.5f} (these are now the site coordinates: keep "
                f"them). {len(shape.exclusions)} exclusion zone(s).")
        self._layout_changed()

    def initializePage(self) -> None:
        rose = self.site.rose() if self.site is not None else None
        if rose is not None:
            self.prevailing.set_value(round(rose.prevailing_deg()), "Wind rose")
        self._layout_changed()

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
        items = list(self._items)
        if self.placed():
            items += [("Minimum distance", self.min_spacing)]
            items += ([("Setback", self.setback)] if self._shape is not None else
                      [("Site width", self.site_width), ("Site length", self.site_length),
                       ("Direction of the length", self.site_rotation)])
        else:
            items += [("Spacing across", self.crosswind), ("Spacing along", self.downwind),
                      ("Turbines per row", self.per_row)]
        if not _warn(self, items):
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
        self._satellite_saved = None      # the aerial tiles of the last map, kept in the project
        super().__init__()
        self.setTitle("5. Results and design checks")

    def _wind_inputs(self):
        """The wind inputs read from the pages (also used by the live preview)."""
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
            wake_model=self.turbine.wake.isChecked() or self.turbine.placed(),
            rose=self.site.rose(),
            layout_mode="optimized" if self.turbine.placed() else "grid",
            site_width_m=self.turbine.site_width.value(),
            site_length_m=self.turbine.site_length.value(),
            site_rotation_deg=self.turbine.site_rotation.value(),
            min_spacing_d=self.turbine.min_spacing.value(),
            site_polygon=self.turbine.shape().boundary if self.turbine.shape() else (),
            site_exclusions=self.turbine.shape().exclusions if self.turbine.shape() else (),
            setback_m=self.turbine.setback.value() if self.turbine.shape() else 0.0,
            turbines_per_row=int(self.turbine.per_row.value()),
            stagger_rows=self.turbine.stagger.isChecked(), wake_decay=self.turbine.decay.value(),
            prevailing_direction_deg=self.turbine.prevailing.value(),
            rose_concentration=self.turbine.conc.value(),
            turbine=self.turbine.spec(), economics=self.costs.inputs(),
        )
        return inputs

    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        inputs = self._wind_inputs()
        design = size_wind_plant(inputs)   # a site that is too small raises ValueError: shown
        if self.turbine.satellite.isChecked() and design.wake is not None:
            inputs = replace(inputs, satellite=self._satellite(inputs, design))
        findings = check_wind_design(inputs, design)
        note = f"Site: lat {self.site.lat.value():.4f}, lon {self.site.lon.value():.4f}."
        light = build_wind_report(inputs, design, findings, site_note=note, theme="light")
        dark = build_wind_report(inputs, design, findings, site_note=note, theme="screen")
        return inputs, design, findings, light, dark

    def _satellite(self, inputs: WindInputs, design):
        """Aerial tiles for the part of the ground the layout map shows (never raises)."""
        w = design.wake
        prevailing = inputs.rose.prevailing_deg() if inputs.rose else inputs.prevailing_direction_deg
        outline = design.site.corners() if design.site else None
        window = layout_window(w.positions, inputs.turbine.rotor_diameter_m, outline, prevailing)
        lat, lon = self.site.lat.value(), self.site.lon.value()
        saved = self._satellite_saved       # a reopened project shows the same picture, offline
        if saved is not None and saved.covers(lat, lon, window):
            return saved
        fresh = fetch_satellite(lat, lon, window)
        if fresh.ok:
            self._satellite_saved = fresh
        return fresh

    def preview_job(self):
        """Read the pages now (on the main thread); the returned function sizes the design."""
        inputs = self._wind_inputs()
        def job():
            design = size_wind_plant(inputs)
            return design, check_wind_design(inputs, design)

        return job

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
