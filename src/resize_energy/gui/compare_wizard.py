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
    QWidget,
)

from resize_energy.core import profiles as prof
from resize_energy.core.bhe_design import BheInputs
from resize_energy.core.biomass_design import BiomassInputs
from resize_energy.core.comparison import (
    ALL_TECHS,
    ELECTRICITY_TECHS,
    HEAT_TECHS,
    TECH_NAMES,
    ComparisonInputs,
    CostAssumptions,
    compare_technologies,
    comparison_sensitivity,
)
from resize_energy.core.comparison_heat import HeatCosts, HeatInputs
from resize_energy.core.fuel_library import SOLID_FUELS, SUBSTRATES
from resize_energy.core.geothermal_design import GeothermalInputs
from resize_energy.core.hydro_design import HydroInputs
from resize_energy.core.nasa_power import NasaPowerError, fetch_wind_climate
from resize_energy.core.pvgis import PVGISError, fetch_pvcalc
from resize_energy.core.solar_thermal import COLLECTORS
from resize_energy.core.solar_thermal_design import SolarThermalInputs
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
    """The technologies chosen on the home page (always in the canonical order) and what is
    compared: "electricity", "heat" or "both"."""

    def __init__(self, techs: tuple[str, ...] = ("pv", "wind"),
                 carrier: str = "electricity") -> None:
        self.carrier = carrier
        self.techs = techs

    @property
    def techs(self) -> tuple[str, ...]:
        return self._techs

    @techs.setter
    def techs(self, value: tuple[str, ...]) -> None:
        self._techs = tuple(t for t in ALL_TECHS if t in value)

    @property
    def uses_electricity(self) -> bool:
        return self.carrier in ("electricity", "both")

    @property
    def uses_heat(self) -> bool:
        return self.carrier in ("heat", "both")

    def electricity_techs(self) -> tuple[str, ...]:
        """The chosen technologies that enter the electricity comparison."""
        return tuple(t for t in self._techs if t in ELECTRICITY_TECHS) if self.uses_electricity else ()

    def heat_techs(self) -> tuple[str, ...]:
        """The chosen technologies that enter the heat comparison."""
        return tuple(t for t in self._techs if t in HEAT_TECHS) if self.uses_heat else ()

    def has(self, key: str) -> bool:
        """True when ``key`` takes part in the electricity comparison."""
        return key in self.electricity_techs()

    def has_heat(self, key: str) -> bool:
        """True when ``key`` takes part in the heat comparison."""
        return key in self.heat_techs()

    def names(self) -> str:
        used = [t for t in self._techs if t in self.electricity_techs() or t in self.heat_techs()]
        names = [TECH_NAMES[t] for t in used]
        return ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else "".join(names)

    # the resource groups are needed by a technology or by the hydrogen plant
    def needs_sun(self) -> bool:
        return self.has("pv") or self.has("hydrogen") or self.has_heat("solar")

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
        hd = HeatInputs()
        self.heat_demand = NumberField(hd.annual_heat_kwh, 1, 1e12, 0, "kWh per year",
                                       "econ.same_demand")
        self.heat_peak = NumberField(hd.peak_kw, 0.1, 1e9, 0, "kW", "econ.same_demand")
        self.heat_coverage = NumberField(hd.coverage * 100, 1, 100, 0, "%", "econ.same_demand")
        self.supply_temp = NumberField(hd.supply_temp_c, 20, 250, 0, "degC", "econ.same_demand")
        self.ground_temp = NumberField(hd.ground_temp_c, -10, 40, 0, "degC", "econ.same_demand")
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
        self.elec_box = QGroupBox("Electricity demand")
        ef = QFormLayout(self.elec_box)
        ef.addRow("Annual energy demand (kWh of electricity)", self.demand)
        ef.addRow("Share of the demand to cover", self.coverage)
        self.heat_box = QGroupBox("Heat demand")
        hf = QFormLayout(self.heat_box)
        hf.addRow("Annual heat demand (useful heat)", self.heat_demand)
        hf.addRow("Peak heat load", self.heat_peak)
        hf.addRow("Share of the heat to cover", self.heat_coverage)
        hf.addRow("Temperature at which the heat is delivered", self.supply_temp)
        hf.addRow("Mean ground / air temperature", self.ground_temp)

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
        layout.addWidget(self.elec_box)
        layout.addWidget(self.heat_box)
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
        self.elec_box.setVisible(sel.uses_electricity)
        self.heat_box.setVisible(sel.uses_heat)
        self.setSubTitle(f"One site and one demand: {sel.names()} are sized for the same job.")

    def implied_pr(self) -> float | None:
        return self._implied_pr

    def weather(self) -> prof.HourlyWeather | None:
        """Real hourly year, when it was downloaded (used by the hydrogen plant)."""
        return self._weather

    def _items(self) -> list[tuple[str, NumberField]]:
        items = [("Latitude", self.lat), ("Longitude", self.lon), ("Tilt", self.tilt),
                 ("Azimuth", self.azimuth)]
        if self.selection.uses_electricity:
            items += [("Annual demand", self.demand), ("Coverage", self.coverage)]
        if self.selection.uses_heat:
            items += [("Annual heat demand", self.heat_demand), ("Peak heat load", self.heat_peak),
                      ("Heat coverage", self.heat_coverage),
                      ("Delivery temperature", self.supply_temp),
                      ("Mean ground temperature", self.ground_temp)]
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
                         "the biogas feed, the hydrogen electricity source, the river and the geothermal well.")
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
        hd, gd = HydroInputs(), GeothermalInputs()
        self.hy_head = NumberField(hd.gross_head_m, 1, 2000, 1, "m", "hydro.power")
        self.hy_flow = NumberField(hd.mean_flow_m3s, 0.001, 5000, 3, "m3/s", "hydro.fdc")
        self.hy_q95 = NumberField(hd.q95_m3s, 0.0005, 5000, 3, "m3/s", "hydro.fdc")
        self.hy_eco = NumberField(hd.eco_flow_m3s, 0, 5000, 3, "m3/s", "hydro.eco_flow")
        self.hy_exceed = NumberField(hd.design_exceedance * 100, 5, 95, 0, "% of the time",
                                     "hydro.fdc")
        self.hy_length = NumberField(hd.penstock_length_m, 0, 20000, 0, "m", "hydro.penstock")
        self.geo_temp = NumberField(140, 30, 400, 0, "degC", "geo.wells")
        self.geo_flow = NumberField(80, 1, 500, 0, "kg/s per well", "geo.heat_power")
        self.geo_ambient = NumberField(gd.ambient_temp_c, -20, 40, 0, "degC", "geo.exergy")
        self.geo_gradient = NumberField(gd.gradient_k_per_km, 10, 200, 0, "degC per km",
                                        "geo.wells")
        self.geo_reinject = NumberField(gd.reinjection_temp_c, 20, 200, 0, "degC", "geo.binary")
        gh, bh = GeothermalInputs(pathway="heat"), BheInputs()
        self.fuel = QComboBox()
        for fuel in SOLID_FUELS:
            self.fuel.addItem(fuel.name)
        self.geoh_temp = NumberField(90, 30, 400, 0, "degC", "geo.wells")
        self.geoh_flow = NumberField(gh.flow_per_well_kg_s, 1, 500, 0, "kg/s per well", "geo.heat_power")
        self.geoh_return = NumberField(gh.return_temp_c, 10, 200, 0, "degC", "geo.heat_power")
        self.geoh_gradient = NumberField(gh.gradient_k_per_km, 10, 200, 0, "degC per km", "geo.wells")
        self.collector = QComboBox()
        for key, collector in COLLECTORS.items():
            self.collector.addItem(collector.name, key)
        self.collector.setCurrentIndex(self.collector.findData("flat"))
        self.bh_cond = NumberField(bh.ground_conductivity, 0.3, 6, 2, "W/(m K)", "bhe.ground")
        self.bh_cop = NumberField(bh.cop_seasonal, 1.1, 10, 2, "", "bhe.loads")
        self.bh_spacing = NumberField(bh.spacing_m, 3, 20, 1, "m", "bhe.field")
        self.bh_depth = NumberField(bh.max_depth_m, 30, 500, 0, "m", "bhe.field")
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

        self.hydro_box = QGroupBox("Hydropower: run-of-river plant (its size comes from the river)")
        hyf = QFormLayout(self.hydro_box)
        hyf.addRow("Gross head", self.hy_head)
        hyf.addRow("Mean flow of the river", self.hy_flow)
        hyf.addRow("Q95 (flow exceeded 95 % of the time)", self.hy_q95)
        hyf.addRow("Environmental flow left in the river", self.hy_eco)
        hyf.addRow("Design flow available for", self.hy_exceed)
        hyf.addRow("Penstock length", self.hy_length)
        self.geo_box = QGroupBox("Geothermal power plant (binary or flash, from the temperature)")
        gf = QFormLayout(self.geo_box)
        gf.addRow("Water temperature at the wellhead", self.geo_temp)
        gf.addRow("Flow of one production well", self.geo_flow)
        gf.addRow("Mean ambient temperature", self.geo_ambient)
        gf.addRow("Temperature gradient of the ground", self.geo_gradient)
        gf.addRow("Reinjection temperature (binary)", self.geo_reinject)

        self.fuel_box = QGroupBox("Biomass boiler (heat only)")
        ff = QFormLayout(self.fuel_box)
        ff.addRow("Fuel", self.fuel)
        self.geoh_box = QGroupBox("Geothermal heat: doublet and heat network")
        ghf = QFormLayout(self.geoh_box)
        ghf.addRow("Water temperature at the wellhead", self.geoh_temp)
        ghf.addRow("Flow of one production well", self.geoh_flow)
        ghf.addRow("Return temperature after the exchanger", self.geoh_return)
        ghf.addRow("Temperature gradient of the ground", self.geoh_gradient)
        self.solar_box = QGroupBox("Solar thermal: collectors and tank")
        sof = QFormLayout(self.solar_box)
        sof.addRow("Collector type", self.collector)
        self.bhe_box = QGroupBox("Ground-source heat pump: borehole field (heating only)")
        bhf = QFormLayout(self.bhe_box)
        bhf.addRow("Thermal conductivity of the ground", self.bh_cond)
        bhf.addRow("Seasonal COP of the heat pump", self.bh_cop)
        bhf.addRow("Spacing between boreholes", self.bh_spacing)
        bhf.addRow("Maximum depth of a borehole", self.bh_depth)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(self.pv_box)
        layout.addWidget(self.wind_box)
        layout.addWidget(self.bio_box)
        layout.addWidget(self.h2_box)
        layout.addWidget(self.hydro_box)
        layout.addWidget(self.geo_box)
        layout.addWidget(self.fuel_box)
        layout.addWidget(self.geoh_box)
        layout.addWidget(self.solar_box)
        layout.addWidget(self.bhe_box)
        layout.addWidget(_hint(
            "A hydropower plant takes what the river gives and a geothermal plant is built in "
            "whole well pairs: neither matches the demand exactly, so read the share of the "
            "demand they cover, and the cost of one kWh, together. The PV array is sized exactly on the target. The wind plant uses a whole number "
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
        self.hydro_box.setVisible(sel.has("hydro"))
        self.geo_box.setVisible(sel.has("geothermal"))
        self.fuel_box.setVisible(sel.has_heat("biomass"))
        self.geoh_box.setVisible(sel.has_heat("geothermal"))
        self.solar_box.setVisible(sel.has_heat("solar"))
        self.bhe_box.setVisible(sel.has_heat("bhe"))

    def heat_templates(self) -> dict[str, object]:
        """The plant assumptions of the heat comparison, for :class:`HeatInputs`."""
        bh = BheInputs()
        cop = self.bh_cop.value()
        return {
            "fuel": SOLID_FUELS[self.fuel.currentIndex()],
            "geothermal": GeothermalInputs(
                pathway="heat", reservoir_temp_c=self.geoh_temp.value(),
                flow_per_well_kg_s=self.geoh_flow.value(), return_temp_c=self.geoh_return.value(),
                gradient_k_per_km=self.geoh_gradient.value()),
            "solar": SolarThermalInputs(collector=str(self.collector.currentData())),
            "bhe": replace(bh, ground_conductivity=self.bh_cond.value(), cop_seasonal=cop,
                           cop_design=max(1.2, cop * bh.cop_design / bh.cop_seasonal),
                           spacing_m=self.bh_spacing.value(), max_depth_m=self.bh_depth.value()),
        }

    def hydro(self) -> HydroInputs:
        return HydroInputs(
            gross_head_m=self.hy_head.value(), mean_flow_m3s=self.hy_flow.value(),
            q95_m3s=self.hy_q95.value(), eco_flow_m3s=self.hy_eco.value(),
            design_exceedance=self.hy_exceed.value() / 100.0,
            penstock_length_m=self.hy_length.value())

    def geothermal(self) -> GeothermalInputs:
        return GeothermalInputs(
            pathway="power", reservoir_temp_c=self.geo_temp.value(),
            flow_per_well_kg_s=self.geo_flow.value(), ambient_temp_c=self.geo_ambient.value(),
            gradient_k_per_km=self.geo_gradient.value(),
            reinjection_temp_c=self.geo_reinject.value())

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
        if sel.has("hydro"):
            items += [("Gross head", self.hy_head), ("Mean flow", self.hy_flow),
                      ("Q95", self.hy_q95), ("Environmental flow", self.hy_eco),
                      ("Design flow exceedance", self.hy_exceed),
                      ("Penstock length", self.hy_length)]
        if sel.has("geothermal"):
            items += [("Wellhead temperature", self.geo_temp), ("Flow per well", self.geo_flow),
                      ("Ambient temperature", self.geo_ambient),
                      ("Temperature gradient", self.geo_gradient),
                      ("Reinjection temperature", self.geo_reinject)]
        if sel.has_heat("geothermal"):
            items += [("Geothermal heat: wellhead temperature", self.geoh_temp),
                      ("Geothermal heat: flow per well", self.geoh_flow),
                      ("Geothermal heat: return temperature", self.geoh_return),
                      ("Geothermal heat: gradient", self.geoh_gradient)]
        if sel.has_heat("bhe"):
            items += [("Ground conductivity", self.bh_cond), ("Seasonal COP", self.bh_cop),
                      ("Borehole spacing", self.bh_spacing), ("Borehole depth", self.bh_depth)]
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
        self.hy_capex = nf(c.hydro_capex_eur_per_kw, 1, 50000, 0, "euro/kW")
        self.hy_om = nf(c.hydro_om_eur_per_kw_year, 0, 3000, 0, "euro/kW per year")
        self.hy_life = nf(c.hydro_lifetime_years, 1, 100, 0, "years", "econ.crf")
        self.hy_co2 = nf(c.hydro_lifecycle_g_per_kwh, 0, 1000, 0, "g CO2/kWh", "econ.co2")
        self.ge_capex = nf(c.geo_capex_eur_per_kw, 1, 50000, 0, "euro/kW net")
        self.ge_om = nf(c.geo_om_eur_per_kw_year, 0, 3000, 0, "euro/kW per year")
        self.ge_life = nf(c.geo_lifetime_years, 1, 100, 0, "years", "econ.crf")
        self.ge_co2 = nf(c.geo_lifecycle_g_per_kwh, 0, 1000, 0, "g CO2/kWh", "econ.co2")
        hc, gh, bh = HeatCosts(), GeothermalInputs(pathway="heat"), BheInputs()
        self.gas_price = nf(hc.gas_heat_eur_per_kwh, 0.001, 5, 3, "euro/kWh of heat", "econ.savings")
        self.gas_eff = nf(hc.gas_boiler_efficiency * 100, 30, 120, 0, "%", "econ.co2")
        self.gas_ef = nf(hc.gas_kg_co2_per_kwh_fuel, 0, 1, 3, "kg CO2/kWh of gas", "econ.co2")
        self.boiler_capex = nf(hc.boiler_capex_eur_per_kw, 1, 10000, 0, "euro/kW of heat")
        self.boiler_om = nf(hc.boiler_om_fraction * 100, 0, 30, 1, "% of the CAPEX per year")
        self.wood = nf(hc.wood_eur_per_t, 0, 2000, 0, "euro per tonne (as received)")
        self.boiler_life = nf(hc.boiler_life_years, 1, 60, 0, "years", "econ.crf")
        self.hp_capex = nf(hc.heat_pump_capex_eur_per_kw, 10, 10000, 0, "euro/kW of heat")
        self.geoh_drill = nf(gh.drilling_eur_per_m, 0, 20000, 0, "euro/m, one well")
        self.geoh_surface = nf(gh.surface_eur_per_kw_th, 0, 5000, 0, "euro/kW of heat")
        self.bore_drill = nf(bh.drilling_eur_per_m, 0, 1000, 0, "euro/m of borehole")
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
        self.hydro_box = QGroupBox("Hydropower: run-of-river plant")
        hyf = QFormLayout(self.hydro_box)
        hyf.addRow("Investment (CAPEX)", self.hy_capex)
        hyf.addRow("Operation and maintenance", self.hy_om)
        hyf.addRow("Lifetime", self.hy_life)
        hyf.addRow("Life-cycle emissions", self.hy_co2)
        self.geo_box = QGroupBox("Geothermal power plant, wells included")
        gef = QFormLayout(self.geo_box)
        gef.addRow("Investment (CAPEX)", self.ge_capex)
        gef.addRow("Operation and maintenance", self.ge_om)
        gef.addRow("Lifetime", self.ge_life)
        gef.addRow("Life-cycle emissions", self.ge_co2)
        self.heat_ref_box = QGroupBox("Heat you would otherwise make with a gas boiler")
        hrf = QFormLayout(self.heat_ref_box)
        hrf.addRow("Price of the heat", self.gas_price)
        hrf.addRow("Efficiency of the boiler", self.gas_eff)
        hrf.addRow("Emissions of the gas", self.gas_ef)
        self.boiler_box = QGroupBox("Biomass boiler")
        bof = QFormLayout(self.boiler_box)
        bof.addRow("Investment (CAPEX)", self.boiler_capex)
        bof.addRow("Operation and maintenance", self.boiler_om)
        bof.addRow("Wood", self.wood)
        bof.addRow("Lifetime", self.boiler_life)
        self.geoh_cost_box = QGroupBox("Geothermal heat: wells and surface plant")
        gcf = QFormLayout(self.geoh_cost_box)
        gcf.addRow("Drilling, all included", self.geoh_drill)
        gcf.addRow("Exchangers, pumps and connection", self.geoh_surface)
        self.bhe_cost_box = QGroupBox("Ground-source heat pump")
        bcf = QFormLayout(self.bhe_cost_box)
        bcf.addRow("Heat pump", self.hp_capex)
        bcf.addRow("Drilling and grouting the boreholes", self.bore_drill)
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
        row3 = QHBoxLayout()
        row3.addWidget(self.hydro_box)
        row3.addWidget(self.geo_box)
        layout.addLayout(row2)
        layout.addLayout(row3)
        layout.addWidget(self.heat_ref_box)
        row4 = QHBoxLayout()
        row4.addWidget(self.boiler_box)
        row4.addWidget(self.geoh_cost_box)
        layout.addLayout(row4)
        layout.addWidget(self.bhe_cost_box)
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
        self.hydro_box.setVisible(sel.has("hydro"))
        self.geo_box.setVisible(sel.has("geothermal"))
        self.heat_ref_box.setVisible(sel.uses_heat)
        self.boiler_box.setVisible(sel.has_heat("biomass"))
        self.geoh_cost_box.setVisible(sel.has_heat("geothermal"))
        self.bhe_cost_box.setVisible(sel.has_heat("bhe"))

    def heat_costs(self) -> HeatCosts:
        return HeatCosts(
            gas_heat_eur_per_kwh=self.gas_price.value(),
            gas_boiler_efficiency=self.gas_eff.value() / 100.0,
            gas_kg_co2_per_kwh_fuel=self.gas_ef.value(),
            boiler_capex_eur_per_kw=self.boiler_capex.value(),
            boiler_om_fraction=self.boiler_om.value() / 100.0,
            wood_eur_per_t=self.wood.value(), boiler_life_years=self.boiler_life.value(),
            heat_pump_capex_eur_per_kw=self.hp_capex.value())

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
            hydro_capex_eur_per_kw=self.hy_capex.value(),
            hydro_om_eur_per_kw_year=self.hy_om.value(),
            hydro_lifetime_years=self.hy_life.value(),
            hydro_lifecycle_g_per_kwh=self.hy_co2.value(),
            geo_capex_eur_per_kw=self.ge_capex.value(),
            geo_om_eur_per_kw_year=self.ge_om.value(),
            geo_lifetime_years=self.ge_life.value(),
            geo_lifecycle_g_per_kwh=self.ge_co2.value(),
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
        if sel.has("hydro"):
            items += [("Hydropower CAPEX", self.hy_capex), ("Hydropower O&M", self.hy_om),
                      ("Hydropower lifetime", self.hy_life),
                      ("Hydropower life-cycle emissions", self.hy_co2)]
        if sel.has("geothermal"):
            items += [("Geothermal CAPEX", self.ge_capex), ("Geothermal O&M", self.ge_om),
                      ("Geothermal lifetime", self.ge_life),
                      ("Geothermal life-cycle emissions", self.ge_co2)]
        if sel.uses_heat:
            items += [("Heat price", self.gas_price), ("Boiler efficiency", self.gas_eff),
                      ("Gas emissions", self.gas_ef)]
        if sel.has_heat("biomass"):
            items += [("Boiler CAPEX", self.boiler_capex), ("Boiler O&M", self.boiler_om),
                      ("Wood price", self.wood), ("Boiler lifetime", self.boiler_life)]
        if sel.has_heat("geothermal"):
            items += [("Geothermal drilling", self.geoh_drill),
                      ("Geothermal surface plant", self.geoh_surface)]
        if sel.has_heat("bhe"):
            items += [("Heat pump cost", self.hp_capex), ("Borehole cost", self.bore_drill)]
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
        # with "both", one comparison at a time (the PDF and the tutor follow the one on show)
        self._switching = False
        self.carrier_box = QComboBox()
        self.carrier_box.addItem("Electricity", "electricity")
        self.carrier_box.addItem("Heat", "heat")
        self.carrier_box.currentIndexChanged.connect(lambda *_: self._switch_carrier())
        self.carrier_row = QWidget()
        cr = QHBoxLayout(self.carrier_row)
        cr.setContentsMargins(0, 0, 0, 0)
        cr.addWidget(QLabel("Showing the comparison of:"))
        cr.addWidget(self.carrier_box)
        cr.addStretch(1)
        self.layout().insertWidget(0, self.carrier_row)

    def _shown_carrier(self) -> str:
        """The comparison on show: the chosen one, or the one picked in the box for both."""
        sel = self.selection
        if sel.carrier != "both":
            return sel.carrier
        return str(self.carrier_box.currentData() or "electricity")

    def _inputs_for(self, carrier: str) -> ComparisonInputs:
        s, p = self.site, self.plant
        sel = self.selection
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
        base = ComparisonInputs(
            annual_irradiation_kwh_m2=s.irr.value(),
            performance_ratio=p.pr.value(),
            wind=wind,
            costs=self.costs_page.costs(),
            techs=sel.electricity_techs() if carrier == "electricity" else sel.heat_techs(),
            latitude_deg=s.lat.value(),
            biomass=p.biomass(),
            hydro=p.hydro(),
            geothermal=p.geothermal(),
            h2_use_pv=p.h2_pv.isChecked(),
            h2_use_wind=p.h2_wind.isChecked(),
            hourly_weather=s.weather(),
        )
        if carrier != "heat":
            return base
        t = p.heat_templates()
        c = self.costs_page
        heat = HeatInputs(
            annual_heat_kwh=s.heat_demand.value(), peak_kw=s.heat_peak.value(),
            coverage=s.heat_coverage.value() / 100.0, costs=c.heat_costs(),
            supply_temp_c=s.supply_temp.value(), ground_temp_c=s.ground_temp.value(),
            solar=t["solar"],
            bhe=replace(t["bhe"], drilling_eur_per_m=c.bore_drill.value()),
            geothermal=replace(t["geothermal"], drilling_eur_per_m=c.geoh_drill.value(),
                               surface_eur_per_kw_th=c.geoh_surface.value()))
        return replace(base, carrier="heat", heat=heat,
                       biomass=replace(BiomassInputs(pathway="boiler"), fuel=t["fuel"]))

    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        s = self.site
        carrier = self._shown_carrier()
        inputs = self._inputs_for(carrier)
        result = replace(compare_technologies(inputs),
                         sensitivity=comparison_sensitivity(inputs))
        findings = check_comparison(inputs, result)
        note = f"Site: lat {s.lat.value():.4f}, lon {s.lon.value():.4f}."
        light = build_comparison_report(inputs, result, findings, site_note=note, theme="light")
        dark = build_comparison_report(inputs, result, findings, site_note=note, theme="screen")
        return inputs, result, findings, light, dark

    def _switch_carrier(self) -> None:
        if self._switching:
            return
        self.initializePage()

    def initializePage(self) -> None:
        both = self.selection.carrier == "both"
        self._switching = True
        try:
            self.carrier_row.setVisible(both)
        finally:
            self._switching = False
        what = {"electricity": "electricity", "heat": "heat", "both": "electricity and heat"}
        self.setSubTitle(f"{self.selection.names()} side by side ({what[self.selection.carrier]}). "
                         "Pick a step on the right for the why.")
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
