"""Ground-source pages (PySide6): loads and heat pump, ground and borehole, field and costs,
results (vertical borehole heat exchangers, ASHRAE length method)."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QMessageBox, QVBoxLayout

from resize_energy.core.bhe_design import BheInputs, size_bhe_field
from resize_energy.gui.widgets import StepPage
from resize_energy.gui.wizard import BaseResultsPage, NumberField, _hint, first_error
from resize_energy.report.charts import ChartSpec
from resize_energy.report.charts_bhe import bhe_charts
from resize_energy.report.html_report_bhe import build_bhe_report
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.checker_bhe import check_bhe_design
from resize_energy.tutor.context_bhe import build_bhe_context
from resize_energy.tutor.explanations_bhe import BHE_TOPIC_ORDER
from resize_energy.tutor.worked_bhe import bhe_worked_example

BHE_STEP_NAMES = ["Loads and heat pump", "Ground and borehole", "Field and costs",
                  "Results and checks"]
PENALTY_KEYS = ["neighbours", "storage"]
PENALTY_LABELS = ["Neighbouring boreholes as line sources (recommended)",
                  "Stored yearly energy per ground column (formula used in teaching)"]


def _warn(page: StepPage, items: list[tuple[str, NumberField]]) -> bool:
    error = first_error(items)
    if error:
        QMessageBox.warning(page, "Check the value", error)
        return False
    return True


class BheLoadPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = BheInputs()
        self.setTitle("1. Loads and heat pump")
        self.setSubTitle("What the building needs from the heat pump, and how the heat pump "
                         "behaves. The boreholes are sized on the heat it takes from the ground "
                         "and gives to it.")
        self.heat = NumberField(d.heating_kwh_per_year, 0, 1e12, 0, "kWh per year", "bhe.loads")
        self.heat_peak = NumberField(d.heating_peak_kw, 0, 1e7, 1, "kW", "bhe.loads")
        self.cool = NumberField(d.cooling_kwh_per_year, 0, 1e12, 0, "kWh per year", "bhe.loads")
        self.cool_peak = NumberField(d.cooling_peak_kw, 0, 1e7, 1, "kW", "bhe.loads")
        self.heat_share = NumberField(d.design_month_heating_share * 100, 1, 100, 0,
                                      "% of the year", "bhe.length")
        self.cool_share = NumberField(d.design_month_cooling_share * 100, 1, 100, 0,
                                      "% of the year", "bhe.length")
        self.cop = NumberField(d.cop_design, 1.1, 10, 2, "", "bhe.loads")
        self.cop_ms = NumberField(d.cop_seasonal, 1.1, 10, 2, "", "bhe.loads")
        self.eer = NumberField(d.eer_design, 0.5, 15, 2, "", "bhe.loads")
        self.eer_ms = NumberField(d.eer_seasonal, 0.5, 15, 2, "", "bhe.loads")
        self.h_in = NumberField(d.fluid_in_heating_c, -10, 30, 1, "degC", "bhe.length")
        self.h_out = NumberField(d.fluid_out_heating_c, -10, 30, 1, "degC", "bhe.length")
        self.c_in = NumberField(d.fluid_in_cooling_c, 10, 50, 1, "degC", "bhe.length")
        self.c_out = NumberField(d.fluid_out_cooling_c, 10, 60, 1, "degC", "bhe.length")

        loads = QGroupBox("Building loads (heat delivered or removed by the heat pump)")
        lf = QFormLayout(loads)
        lf.addRow("Heating energy", self.heat)
        lf.addRow("Heating peak power", self.heat_peak)
        lf.addRow("Share of the heating in the design month", self.heat_share)
        lf.addRow("Cooling energy", self.cool)
        lf.addRow("Cooling peak power", self.cool_peak)
        lf.addRow("Share of the cooling in the design month", self.cool_share)
        pump = QGroupBox("Heat pump")
        pf = QFormLayout(pump)
        pf.addRow("COP at the design point (heating)", self.cop)
        pf.addRow("Seasonal COP (heating)", self.cop_ms)
        pf.addRow("EER at the design point (cooling)", self.eer)
        pf.addRow("Seasonal EER (cooling)", self.eer_ms)
        fluid = QGroupBox("Temperature of the fluid in the boreholes")
        ff = QFormLayout(fluid)
        ff.addRow("Heating: fluid back from the ground to the heat pump", self.h_in)
        ff.addRow("Heating: fluid sent to the ground", self.h_out)
        ff.addRow("Cooling: fluid sent to the ground", self.c_out)
        ff.addRow("Cooling: fluid back from the ground", self.c_in)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(loads)
        layout.addWidget(pump)
        layout.addWidget(fluid)
        layout.addWidget(_hint(
            "Leave a load at zero for a heating-only or cooling-only building. The design "
            "month is the one that stresses the ground most (usually January or July): the "
            "share is the part of the yearly energy used in it, 15-25 % for heating."))
        layout.addStretch(1)

    def _items(self) -> list[tuple[str, NumberField]]:
        return [("Heating energy", self.heat), ("Heating peak", self.heat_peak),
                ("Cooling energy", self.cool), ("Cooling peak", self.cool_peak),
                ("Heating month share", self.heat_share), ("Cooling month share", self.cool_share),
                ("COP", self.cop), ("Seasonal COP", self.cop_ms), ("EER", self.eer),
                ("Seasonal EER", self.eer_ms), ("Heating fluid in", self.h_in),
                ("Heating fluid out", self.h_out), ("Cooling fluid in", self.c_in),
                ("Cooling fluid out", self.c_out)]

    def validatePage(self) -> bool:
        if not _warn(self, self._items()):
            return False
        if self.heat.value() <= 0 and self.cool.value() <= 0:
            QMessageBox.warning(self, "Check the value",
                                "Give a heating demand, a cooling demand, or both.")
            return False
        for energy, peak, name in ((self.heat, self.heat_peak, "heating"),
                                   (self.cool, self.cool_peak, "cooling")):
            if energy.value() > 0 and peak.value() * 8760 < energy.value():
                QMessageBox.warning(
                    self, "Check the value",
                    f"The {name} peak is too low for the yearly energy: it needs at least "
                    f"{energy.value() / 8760:,.0f} kW.")
                return False
        if self.h_in.value() <= self.h_out.value():
            QMessageBox.warning(self, "Check the value",
                                "In heating the fluid must come back from the ground warmer "
                                "than it is sent.")
            return False
        if self.c_out.value() <= self.c_in.value():
            QMessageBox.warning(self, "Check the value",
                                "In cooling the fluid must be sent to the ground warmer "
                                "than it comes back.")
            return False
        return True


class BheGroundPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = BheInputs()
        self.setTitle("2. Ground and borehole")
        self.setSubTitle("The ground around the field and the pipes inside each borehole.")
        self.t_ground = NumberField(d.ground_temp_c, -5, 40, 1, "degC", "bhe.ground")
        self.k_ground = NumberField(d.ground_conductivity, 0.3, 6, 2, "W/(m K)", "bhe.ground")
        self.rho = NumberField(d.ground_density, 800, 3500, 0, "kg/m3", "bhe.ground")
        self.cp = NumberField(d.ground_cp, 400, 3000, 0, "J/(kg K)", "bhe.ground")
        self.db = NumberField(d.borehole_diameter_mm, 80, 300, 0, "mm", "bhe.borehole")
        self.de = NumberField(d.pipe_outer_mm, 16, 63, 1, "mm", "bhe.borehole")
        self.di = NumberField(d.pipe_inner_mm, 10, 55, 1, "mm", "bhe.borehole")
        self.spacing = NumberField(d.pipe_spacing_mm, 20, 150, 1, "mm centre to centre",
                                   "bhe.borehole")
        self.k_pipe = NumberField(d.pipe_conductivity, 0.1, 1.0, 2, "W/(m K)", "bhe.borehole")
        self.k_grout = NumberField(d.grout_conductivity, 0.3, 4, 2, "W/(m K)", "bhe.borehole")
        self.fsc = NumberField(d.short_circuit_factor, 1.0, 1.5, 2, "", "bhe.length")
        self.f_cp = NumberField(d.fluid_cp, 3000, 4300, 0, "J/(kg K)", "bhe.borehole")
        self.f_mu = NumberField(d.fluid_viscosity * 1000, 0.5, 20, 2, "mPa s", "bhe.borehole")
        self.f_k = NumberField(d.fluid_conductivity, 0.3, 0.7, 2, "W/(m K)", "bhe.borehole")

        ground = QGroupBox("Ground")
        gf = QFormLayout(ground)
        gf.addRow("Undisturbed temperature", self.t_ground)
        gf.addRow("Thermal conductivity", self.k_ground)
        gf.addRow("Density", self.rho)
        gf.addRow("Specific heat", self.cp)
        hole = QGroupBox("Borehole (single U-tube)")
        hf = QFormLayout(hole)
        hf.addRow("Borehole diameter", self.db)
        hf.addRow("Pipe outer diameter", self.de)
        hf.addRow("Pipe inner diameter", self.di)
        hf.addRow("Distance between the two pipes", self.spacing)
        hf.addRow("Pipe conductivity", self.k_pipe)
        hf.addRow("Grout conductivity", self.k_grout)
        hf.addRow("Short-circuit factor between the legs", self.fsc)
        fluid = QGroupBox("Heat-carrier fluid (water with antifreeze)")
        ff = QFormLayout(fluid)
        ff.addRow("Specific heat", self.f_cp)
        ff.addRow("Dynamic viscosity", self.f_mu)
        ff.addRow("Thermal conductivity", self.f_k)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(ground)
        layout.addWidget(hole)
        layout.addWidget(fluid)
        layout.addWidget(_hint(
            "The conductivity of the ground is the number that matters most: 1-2 W/(m K) for "
            "clay and dry sand, 2-3 for gravel and rock; a thermal response test measures it "
            "on site. Density and specific heat of rock are about 2200 kg/m3 and 1000 J/(kg K)."))
        layout.addStretch(1)

    def _items(self) -> list[tuple[str, NumberField]]:
        return [("Ground temperature", self.t_ground), ("Ground conductivity", self.k_ground),
                ("Ground density", self.rho), ("Ground specific heat", self.cp),
                ("Borehole diameter", self.db), ("Outer pipe diameter", self.de),
                ("Inner pipe diameter", self.di), ("Pipe distance", self.spacing),
                ("Pipe conductivity", self.k_pipe), ("Grout conductivity", self.k_grout),
                ("Short-circuit factor", self.fsc), ("Fluid specific heat", self.f_cp),
                ("Fluid viscosity", self.f_mu), ("Fluid conductivity", self.f_k)]

    def validatePage(self) -> bool:
        if not _warn(self, self._items()):
            return False
        de, di = self.de.value(), self.di.value()
        db, sp = self.db.value(), self.spacing.value()
        if di >= de:
            QMessageBox.warning(self, "Check the value",
                                "The inner diameter of the pipe must be smaller than the outer one.")
            return False
        if not (de < sp < db):
            QMessageBox.warning(self, "Check the value",
                                "The distance between the pipes must be larger than the pipe "
                                "diameter and smaller than the borehole diameter.")
            return False
        return True


class BheFieldPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = BheInputs()
        self.setTitle("3. Field and costs")
        self.setSubTitle("How the boreholes are laid out and what the drilling costs.")
        self.dist = NumberField(d.spacing_m, 2, 30, 1, "m", "bhe.field")
        self.max_depth = NumberField(d.max_depth_m, 30, 500, 0, "m", "bhe.field")
        self.area = NumberField(d.available_area_m2, 0, 1e7, 0, "m2 (0 = do not check)",
                                "bhe.field")
        self.columns = NumberField(d.columns, 0, 200, 0, "(0 = about square)", "bhe.field")
        self.method = QComboBox()
        for label in PENALTY_LABELS:
            self.method.addItem(label)
        self.years = NumberField(d.pulse_years, 1, 50, 0, "years", "bhe.ground")
        self.drill = NumberField(d.drilling_eur_per_m, 0, 1000, 0, "euro per metre", "bhe.economics")
        self.om = NumberField(d.om_fraction * 100, 0, 10, 1, "% of CAPEX per year", "bhe.economics")
        self.life = NumberField(d.life_years, 5, 100, 0, "years", "bhe.economics")
        self.rate = NumberField(d.discount_rate * 100, 0, 30, 1, "%", "bhe.economics")

        field = QGroupBox("Field")
        ff = QFormLayout(field)
        ff.addRow("Distance between boreholes", self.dist)
        ff.addRow("Maximum depth of a borehole", self.max_depth)
        ff.addRow("Land available", self.area)
        ff.addRow("Boreholes in a row", self.columns)
        ff.addRow("Temperature penalty", self.method)
        ff.addRow("Duration of the long-term pulse", self.years)
        cost = QGroupBox("Cost")
        cf = QFormLayout(cost)
        cf.addRow("Drilling, pipes and grout", self.drill)
        cf.addRow("Operation and maintenance", self.om)
        cf.addRow("Life", self.life)
        cf.addRow("Discount rate", self.rate)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(field)
        layout.addWidget(cost)
        layout.addWidget(_hint(
            "Boreholes 6-8 m apart are the usual compromise between land and interference. "
            "The price per metre is a placeholder: ask a driller for a quote, it changes a lot "
            "with the ground and the country."))
        layout.addStretch(1)

    def method_key(self) -> str:
        return PENALTY_KEYS[max(0, self.method.currentIndex())]

    def _items(self) -> list[tuple[str, NumberField]]:
        return [("Spacing", self.dist), ("Maximum depth", self.max_depth), ("Area", self.area),
                ("Columns", self.columns), ("Pulse years", self.years), ("Drilling", self.drill),
                ("O&M", self.om), ("Life", self.life), ("Discount rate", self.rate)]

    def validatePage(self) -> bool:
        return _warn(self, self._items())


class BheResultsPage(BaseResultsPage):
    topic_order = BHE_TOPIC_ORDER
    pdf_name = "RESize_ground_source_report.pdf"

    def __init__(self, load: BheLoadPage, ground: BheGroundPage, field: BheFieldPage) -> None:
        self.load, self.ground, self.field = load, ground, field
        super().__init__()
        self.setTitle("4. Results and design checks")

    def _inputs_from_pages(self) -> BheInputs:
        a, g, f = self.load, self.ground, self.field
        return BheInputs(
            heating_kwh_per_year=a.heat.value(), heating_peak_kw=a.heat_peak.value(),
            cooling_kwh_per_year=a.cool.value(), cooling_peak_kw=a.cool_peak.value(),
            design_month_heating_share=a.heat_share.value() / 100.0,
            design_month_cooling_share=a.cool_share.value() / 100.0,
            cop_design=a.cop.value(), cop_seasonal=a.cop_ms.value(), eer_design=a.eer.value(),
            eer_seasonal=a.eer_ms.value(), fluid_in_heating_c=a.h_in.value(),
            fluid_out_heating_c=a.h_out.value(), fluid_in_cooling_c=a.c_in.value(),
            fluid_out_cooling_c=a.c_out.value(),
            ground_temp_c=g.t_ground.value(), ground_conductivity=g.k_ground.value(),
            ground_density=g.rho.value(), ground_cp=g.cp.value(),
            pipe_outer_mm=g.de.value(), pipe_inner_mm=g.di.value(),
            pipe_spacing_mm=g.spacing.value(), pipe_conductivity=g.k_pipe.value(),
            borehole_diameter_mm=g.db.value(), grout_conductivity=g.k_grout.value(),
            short_circuit_factor=g.fsc.value(), fluid_cp=g.f_cp.value(),
            fluid_viscosity=g.f_mu.value() / 1000.0, fluid_conductivity=g.f_k.value(),
            spacing_m=f.dist.value(), max_depth_m=f.max_depth.value(),
            available_area_m2=f.area.value(), columns=int(round(f.columns.value())),
            pulse_years=f.years.value(), penalty_method=f.method_key(),
            drilling_eur_per_m=f.drill.value(), life_years=f.life.value(),
            discount_rate=f.rate.value() / 100.0, om_fraction=f.om.value() / 100.0)

    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        inputs = self._inputs_from_pages()
        design = size_bhe_field(inputs)
        findings = check_bhe_design(inputs, design)
        light = build_bhe_report(inputs, design, findings, theme="light")
        screen = build_bhe_report(inputs, design, findings, theme="screen")
        return inputs, design, findings, light, screen

    def _flow(self):
        from resize_energy.report.flow_pictures import bhe_picture

        return bhe_picture(self._inputs, self._design)

    def _worked(self, key: str) -> str | None:
        return bhe_worked_example(key, self._inputs, self._design)

    def _context(self) -> str:
        return build_bhe_context(self._inputs, self._design, self._findings)

    def _charts(self) -> dict[str, ChartSpec]:
        return bhe_charts(self._inputs, self._design)
