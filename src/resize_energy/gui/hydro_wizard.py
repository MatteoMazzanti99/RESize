"""Hydropower pages (PySide6): site and river, penstock and turbine, costs, results."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QMessageBox, QVBoxLayout

from resize_energy.core.hydro import TURBINES
from resize_energy.core.hydro_design import HydroInputs, size_hydro_plant
from resize_energy.gui.country import CountryBar
from resize_energy.gui.widgets import StepPage
from resize_energy.gui.wizard import BaseResultsPage, NumberField, _hint, first_error
from resize_energy.report.charts import ChartSpec, hydro_charts
from resize_energy.report.html_report import build_hydro_report
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.checker_hydro import check_hydro_design
from resize_energy.tutor.context_hydro import build_hydro_context
from resize_energy.tutor.explanations_hydro import HYDRO_TOPIC_ORDER
from resize_energy.tutor.worked_hydro import hydro_worked_example

HYDRO_STEP_NAMES = ["Site and river", "Penstock and turbine", "Prices and costs",
                    "Results and checks"]
TURBINE_KEYS = ["auto", *TURBINES]


def _warn(page: StepPage, items: list[tuple[str, NumberField]]) -> bool:
    error = first_error(items)
    if error:
        QMessageBox.warning(page, "Check the value", error)
        return False
    return True


class HydroSitePage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = HydroInputs()
        self.setTitle("1. Site and river")
        self.setSubTitle("A run-of-river plant uses the drop of a river between an intake and "
                         "a powerhouse. Tell me the drop and how much water the river carries.")
        self.head = NumberField(d.gross_head_m, 1, 2000, 1, "m", "hydro.power")
        self.mean_flow = NumberField(d.mean_flow_m3s, 0.001, 5000, 3, "m3/s", "hydro.fdc")
        self.q95 = NumberField(d.q95_m3s, 0.0005, 5000, 3, "m3/s", "hydro.fdc")
        self.eco = NumberField(d.eco_flow_m3s, 0, 5000, 3, "m3/s", "hydro.eco_flow")
        self.exceedance = NumberField(d.design_exceedance * 100, 5, 95, 0,
                                      "% of the time", "hydro.design_flow")
        self.demand = NumberField(d.annual_demand_kwh, 0, 1e12, 0, "kWh per year (0: sell all)",
                                  "hydro.economics")

        head = QGroupBox("The drop")
        hf = QFormLayout(head)
        hf.addRow("Gross head (intake to turbine outlet)", self.head)
        river = QGroupBox("The river")
        rf = QFormLayout(river)
        rf.addRow("Mean flow", self.mean_flow)
        rf.addRow("Q95 (flow exceeded 95 % of the time)", self.q95)
        rf.addRow("Environmental flow left in the river", self.eco)
        plant = QGroupBox("The plant")
        pf = QFormLayout(plant)
        pf.addRow("Design flow: the river exceeds it", self.exceedance)
        pf.addRow("Your electricity demand", self.demand)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(head)
        layout.addWidget(river)
        layout.addWidget(plant)
        layout.addWidget(_hint(
            "Mean flow and Q95 come from a hydrologic study or a gauging station of the river "
            "(or are estimated from the area of the catchment). The environmental flow is set "
            "by the rule of your river basin: about 10 % of the mean flow is a bare minimum. "
            "A design flow that the river exceeds 20-40 % of the time is a usual start; the "
            "results show what a bigger or smaller turbine would do."))
        layout.addStretch(1)

    def validatePage(self) -> bool:
        if not _warn(self, [("Gross head", self.head), ("Mean flow", self.mean_flow),
                            ("Q95", self.q95), ("Environmental flow", self.eco),
                            ("Design flow", self.exceedance), ("Demand", self.demand)]):
            return False
        if self.q95.value() >= self.mean_flow.value():
            QMessageBox.warning(self, "Check the value",
                                "Q95 must be lower than the mean flow: a river has less water "
                                "95 % of the time than on average.")
            return False
        if self.eco.value() >= self.mean_flow.value():
            QMessageBox.warning(self, "Check the value",
                                "The environmental flow must be lower than the mean flow.")
            return False
        return True


class HydroPlantPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = HydroInputs()
        self.setTitle("2. Penstock and turbine")
        self.setSubTitle("The pipe that brings the water down and the machine that turns it "
                         "into power. The defaults are typical: change them with datasheet values.")
        self.length = NumberField(d.penstock_length_m, 0, 20000, 0, "m", "hydro.penstock")
        self.velocity = NumberField(d.penstock_velocity_ms, 0.5, 8, 1, "m/s", "hydro.penstock")
        self.diameter = NumberField(d.penstock_diameter_m, 0, 10, 2, "m (0: from the velocity)",
                                    "hydro.penstock")
        self.roughness = NumberField(d.roughness_mm, 0, 10, 2, "mm", "hydro.penstock")
        self.k = NumberField(d.local_loss_k, 0, 20, 1, "sum of K", "hydro.penstock")
        self.turbine = QComboBox()
        self.turbine.addItem("Chosen from the head and the flow")
        for t in TURBINES.values():
            self.turbine.addItem(t.name)
        self.eta_t = NumberField(0, 0, 99, 0, "% (0: typical of the type)", "hydro.power")
        self.eta_g = NumberField(0, 0, 99.5, 1, "% (0: typical of the size)", "hydro.power")
        self.losses = NumberField(d.operating_losses * 100, 0, 50, 0, "% of the energy",
                                  "hydro.energy")

        pipe = QGroupBox("Penstock")
        pf = QFormLayout(pipe)
        pf.addRow("Length", self.length)
        pf.addRow("Design water velocity", self.velocity)
        pf.addRow("Diameter", self.diameter)
        pf.addRow("Wall roughness (new steel 0.05-0.1)", self.roughness)
        pf.addRow("Local losses (intake, trash rack, bends, valve)", self.k)
        machine = QGroupBox("Turbine and generator")
        mf = QFormLayout(machine)
        mf.addRow("Turbine", self.turbine)
        mf.addRow("Turbine efficiency", self.eta_t)
        mf.addRow("Generator efficiency", self.eta_g)
        mf.addRow("Outages and part-load losses", self.losses)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(pipe)
        layout.addWidget(machine)
        layout.addWidget(_hint(
            "The type of turbine follows the head and the flow of the design: Kaplan for low "
            "heads, Francis for medium ones, Pelton for high heads and small flows. Leave the "
            "efficiencies at 0 to use typical values (ESHA Guide). A velocity of 2-4 m/s is a "
            "common compromise between a cheap, narrow pipe and a small loss of head."))
        layout.addStretch(1)

    def turbine_key(self) -> str:
        return TURBINE_KEYS[max(0, self.turbine.currentIndex())]

    def validatePage(self) -> bool:
        return _warn(self, [("Length", self.length), ("Velocity", self.velocity),
                            ("Diameter", self.diameter), ("Roughness", self.roughness),
                            ("Local losses", self.k), ("Turbine efficiency", self.eta_t),
                            ("Generator efficiency", self.eta_g), ("Losses", self.losses)])


class HydroCostPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        d = HydroInputs()
        self.setTitle("3. Prices and costs")
        self.setSubTitle("What the plant costs and what the electricity is worth. The defaults "
                         "are literature values: replace them with quotes and your tariff.")
        self.capex = NumberField(d.capex_per_kw, 0, 50000, 0, "euro per kW", "hydro.economics")
        self.om = NumberField(d.om_fraction * 100, 0, 20, 1, "% of CAPEX per year", "hydro.economics")
        self.life = NumberField(d.life_years, 5, 100, 0, "years", "hydro.economics")
        self.rate = NumberField(d.discount_rate * 100, 0, 30, 1, "%", "hydro.economics")
        self.retail = NumberField(d.retail_price, 0.001, 2, 3, "euro/kWh bought", "hydro.economics")
        self.export = NumberField(d.export_price, 0, 2, 3, "euro/kWh sold", "hydro.economics")
        self.ef = NumberField(d.grid_ef, 0, 2, 3, "kg CO2/kWh", "hydro.co2")
        self.lifecycle = NumberField(d.lifecycle_g_per_kwh, 0, 500, 0, "g CO2/kWh of the plant",
                                     "hydro.co2")
        cost = QGroupBox("Plant cost")
        cf = QFormLayout(cost)
        cf.addRow("Installed cost", self.capex)
        cf.addRow("Operation and maintenance", self.om)
        cf.addRow("Life", self.life)
        el = QGroupBox("Electricity and finance")
        ef = QFormLayout(el)
        ef.addRow("Price you pay", self.retail)
        ef.addRow("Price you are paid for the energy you sell", self.export)
        ef.addRow("Discount rate", self.rate)
        ef.addRow("Grid emission factor", self.ef)
        ef.addRow("Life-cycle emissions of the plant", self.lifecycle)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(cost)
        layout.addWidget(el)
        self.country_bar = CountryBar({"electricity": self.retail, "export": self.export,
                                       "grid_ef": self.ef})
        self.country = self.country_bar.combo
        layout.insertWidget(0, self.country_bar)
        layout.addWidget(_hint(
            "The cost of a small hydropower plant changes by a factor of two or three with the "
            "site: intake, penstock, access road and grid connection are as important as the "
            "machine. The default is a literature value for the USA (NREL): ask for quotes."))
        layout.addStretch(1)

    def initializePage(self) -> None:
        self.country_bar.sync()

    def validatePage(self) -> bool:
        return _warn(self, [("Installed cost", self.capex), ("O&M", self.om), ("Life", self.life),
                            ("Discount rate", self.rate), ("Price paid", self.retail),
                            ("Price received", self.export), ("Emission factor", self.ef),
                            ("Life-cycle emissions", self.lifecycle)])


class HydroResultsPage(BaseResultsPage):
    topic_order = HYDRO_TOPIC_ORDER
    pdf_name = "RESize_hydropower_report.pdf"
    has_excel = True

    def __init__(self, site: HydroSitePage, plant: HydroPlantPage, costs: HydroCostPage) -> None:
        self.site, self.plant, self.costs = site, plant, costs
        super().__init__()
        self.setTitle("4. Results and design checks")

    def _inputs_from_pages(self) -> HydroInputs:
        s, p, c = self.site, self.plant, self.costs
        return HydroInputs(
            gross_head_m=s.head.value(), mean_flow_m3s=s.mean_flow.value(), q95_m3s=s.q95.value(),
            eco_flow_m3s=s.eco.value(), design_exceedance=s.exceedance.value() / 100.0,
            annual_demand_kwh=s.demand.value(),
            penstock_length_m=p.length.value(), penstock_velocity_ms=p.velocity.value(),
            penstock_diameter_m=p.diameter.value(), roughness_mm=p.roughness.value(),
            local_loss_k=p.k.value(), turbine=p.turbine_key(),
            turbine_efficiency=p.eta_t.value() / 100.0, generator_efficiency=p.eta_g.value() / 100.0,
            operating_losses=p.losses.value() / 100.0,
            grid_ef=c.ef.value(), lifecycle_g_per_kwh=c.lifecycle.value(),
            capex_per_kw=c.capex.value(), om_fraction=c.om.value() / 100.0,
            life_years=c.life.value(), discount_rate=c.rate.value() / 100.0,
            retail_price=c.retail.value(), export_price=c.export.value())

    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        inputs = self._inputs_from_pages()
        design = size_hydro_plant(inputs)
        findings = check_hydro_design(inputs, design)
        light = build_hydro_report(inputs, design, findings, theme="light")
        screen = build_hydro_report(inputs, design, findings, theme="screen")
        return inputs, design, findings, light, screen

    def preview_job(self):
        """Read the pages now (on the main thread); the returned function sizes the design."""
        inputs = self._inputs_from_pages()
        def job():
            design = size_hydro_plant(inputs)
            return design, check_hydro_design(inputs, design)

        return job

    def _flow(self):
        from resize_energy.report.flow_pictures import hydro_picture

        return hydro_picture(self._inputs, self._design)

    def _workbook(self):
        from resize_energy.report.excel_hydro_geo import build_hydro_workbook

        return build_hydro_workbook(self._inputs, self._design)

    def _worked(self, key: str) -> str | None:
        return hydro_worked_example(key, self._inputs, self._design)

    def _context(self) -> str:
        return build_hydro_context(self._inputs, self._design, self._findings)

    def _charts(self) -> dict[str, ChartSpec]:
        return hydro_charts(self._inputs, self._design)
