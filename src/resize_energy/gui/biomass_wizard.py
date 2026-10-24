"""Biomass sizing pages (PySide6): pathway and demand, fuel or substrate, plant, results."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from resize_energy.core.biomass_design import (
    PATHWAYS,
    BiomassInputs,
    default_efficiencies,
    size_biomass_plant,
)
from resize_energy.core.fuel_library import SOLID_FUELS, SUBSTRATES, SolidFuel
from resize_energy.gui.country import CountryBar
from resize_energy.gui.widgets import StepPage
from resize_energy.gui.wizard import BaseResultsPage, NumberField, _hint, first_error
from resize_energy.report.charts import ChartSpec, biomass_charts
from resize_energy.report.html_report import build_biomass_report
from resize_energy.tutor.checker import Finding
from resize_energy.tutor.checker_biomass import check_biomass_design
from resize_energy.tutor.context_biomass import build_biomass_context
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.explanations_biomass import BIOMASS_TOPIC_ORDER, topics_for
from resize_energy.tutor.worked_biomass import biomass_worked_example

BIOMASS_STEP_NAMES = ["Pathway and demand", "Fuel or substrate", "Plant and emissions",
                      "Results and checks"]
PATHWAY_KEYS = list(PATHWAYS)


def _warn(page: StepPage, items: list[tuple[str, NumberField]]) -> bool:
    error = first_error(items)
    if error:
        QMessageBox.warning(page, "Check the value", error)
        return False
    return True


def _show_row(form: QFormLayout, field: QWidget, visible: bool) -> None:
    """Show or hide a form row (label and field together)."""
    label = form.labelForField(field)
    if label is not None:
        label.setVisible(visible)
    field.setVisible(visible)


class BiomassDemandPage(StepPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("1. Pathway and demand")
        self.setSubTitle("What must the plant supply? Choose the pathway first, then enter the heat or electricity you need.")
        self.picker = QComboBox()
        for key in PATHWAY_KEYS:
            self.picker.addItem(PATHWAYS[key])
        self.picker.currentIndexChanged.connect(self._changed)

        self.heat = NumberField(2_000_000, 0, 1e12, 0, "kWh per year", "biomass.load_duration")
        self.peak = NumberField(800, 0, 1e7, 0, "kW", "biomass.load_duration")
        self.electricity = NumberField(1_500_000, 0, 1e12, 0, "kWh per year",
                                       "biomass.chp_biogas")
        self.coverage = NumberField(85, 1, 100, 0, "%", "biomass.plant_power")

        box = QGroupBox("Technology")
        bl = QVBoxLayout(box)
        bl.addWidget(self.picker)
        self.note = _hint("")
        bl.addWidget(self.note)
        self.form = QFormLayout()
        self.form.addRow("Annual heat demand", self.heat)
        self.form.addRow("Peak heat load", self.peak)
        self.form.addRow("Annual electricity demand", self.electricity)
        self.form.addRow("Share of the demand to cover", self.coverage)
        demand = QGroupBox("Demand")
        demand.setLayout(self.form)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(box)
        layout.addWidget(demand)
        layout.addWidget(_hint(
            "Solid-fuel plants are sized on the heat: the peak load and the yearly demand give "
            "the load duration curve. Biogas plants are sized on the electricity: the heat of "
            "the engine is a by-product (after heating the digester). For a heat network or "
            "a district, 80-90 % of the heat with a backup boiler is a usual target."))
        layout.addStretch(1)
        self._changed(0)

    def pathway(self) -> str:
        return PATHWAY_KEYS[max(0, self.picker.currentIndex())]

    def _changed(self, _index: int = 0) -> None:
        key = self.pathway()
        solid = key != "biogas"
        _show_row(self.form, self.peak, solid)
        _show_row(self.form, self.heat, True)
        _show_row(self.form, self.electricity, key in ("orc", "biogas"))
        notes = {
            "boiler": "Heat only. Sized on the heat load duration curve.",
            "orc": "Heat and power from an organic Rankine cycle. Heat-led: the electricity "
                   "follows the heat.",
            "biogas": "Digester and gas engine. Power-led: sized on the electricity demand.",
        }
        self.note.setText(notes[key])
        self.coverage.edit.setToolTip("Share of the heat (solid) or of the electricity (biogas)")

    def _items(self) -> list[tuple[str, NumberField]]:
        key = self.pathway()
        items = [("Coverage", self.coverage), ("Heat demand", self.heat)]
        if key != "biogas":
            items.append(("Peak heat load", self.peak))
        if key in ("orc", "biogas"):
            items.append(("Electricity demand", self.electricity))
        return items

    def validatePage(self) -> bool:
        if not _warn(self, self._items()):
            return False
        key = self.pathway()
        if key != "biogas" and (self.heat.value() <= 0 or self.peak.value() <= 0):
            QMessageBox.warning(self, "Check the value",
                                "Heat demand and peak load must be greater than zero.")
            return False
        if key == "biogas" and self.electricity.value() <= 0:
            QMessageBox.warning(self, "Check the value",
                                "The biogas plant is sized on the electricity demand: enter a "
                                "value above zero.")
            return False
        return True


class BiomassFuelPage(StepPage):
    def __init__(self, demand: BiomassDemandPage) -> None:
        super().__init__()
        self.demand = demand
        self.setTitle("2. Fuel or substrate")
        self.setSubTitle("What do you burn or ferment? Pick one from the list and the typical values fill in; moisture decides how much material you need.")
        f = SOLID_FUELS[0]

        self.fuel_picker = QComboBox()
        for fuel in SOLID_FUELS:
            self.fuel_picker.addItem(fuel.name)
        self.fuel_picker.currentIndexChanged.connect(self._fuel_picked)
        self.moisture = NumberField(f.moisture_wb * 100, 0, 70, 0, "%", "biomass.lhv")
        self.lhv = NumberField(f.lhv_dry_kwh_per_kg, 3, 7, 2, "kWh/kg (dry)", "biomass.lhv")
        self.bulk = NumberField(f.bulk_density_kg_m3, 50, 900, 0, "kg/m3", "biomass.storage")
        self.ash = NumberField(f.ash_dry * 100, 0, 30, 1, "% of dry matter")
        for field in (self.moisture, self.lhv, self.bulk, self.ash):
            field.edit.textEdited.connect(self._fuel_edited)
        self._fuel_name = f.name

        self.solid_box = QGroupBox("Solid fuel")
        sf = QFormLayout(self.solid_box)
        sf.addRow("Fuel", self.fuel_picker)
        sf.addRow("Moisture as delivered (wet basis)", self.moisture)
        sf.addRow("Heating value of the dry matter", self.lhv)
        sf.addRow("Bulk density as delivered", self.bulk)
        sf.addRow("Ash content", self.ash)

        self.sub_a = QComboBox()
        self.sub_b = QComboBox()
        for sub in SUBSTRATES:
            self.sub_a.addItem(sub.name)
            self.sub_b.addItem(sub.name)
        self.sub_a.setCurrentIndex(2)   # maize silage
        self.sub_b.setCurrentIndex(0)   # cattle slurry
        self.share_b = NumberField(50, 0, 100, 0, "% of the mass", "biomass.biogas_yield")
        self.hrt = NumberField(45, 5, 120, 0, "days", "biomass.digester")
        self.biogas_box = QGroupBox("Substrates (typical handbook values)")
        gf = QFormLayout(self.biogas_box)
        gf.addRow("Substrate A", self.sub_a)
        gf.addRow("Substrate B", self.sub_b)
        gf.addRow("Share of substrate B", self.share_b)
        gf.addRow("Hydraulic retention time", self.hrt)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(self.solid_box)
        layout.addWidget(self.biogas_box)
        self.hint = _hint("")
        layout.addWidget(self.hint)
        layout.addStretch(1)

    def initializePage(self) -> None:
        biogas = self.demand.pathway() == "biogas"
        self.solid_box.setVisible(not biogas)
        self.biogas_box.setVisible(biogas)
        self.hint.setText(
            "Yields are typical values: a laboratory methane potential (BMP) test of your own "
            "substrates is needed before investing. Slurry is dilute and rich substrates raise "
            "the loading rate: mix them." if biogas else
            "Values come from typical handbook figures. Use the specification of your supplier "
            "when you have it: moisture is the number that changes the result most.")

    def _fuel_picked(self, index: int) -> None:
        fuel = SOLID_FUELS[max(0, index)]
        self._fuel_name = fuel.name
        self.moisture.set_value(fuel.moisture_wb * 100)
        self.lhv.set_value(fuel.lhv_dry_kwh_per_kg)
        self.bulk.set_value(fuel.bulk_density_kg_m3)
        self.ash.set_value(fuel.ash_dry * 100)

    def _fuel_edited(self, *_args) -> None:
        self._fuel_name = "Custom fuel"

    def fuel(self) -> SolidFuel:
        return SolidFuel(self._fuel_name, self.lhv.value(), self.moisture.value() / 100.0,
                         self.bulk.value(), self.ash.value() / 100.0)

    def validatePage(self) -> bool:
        if self.demand.pathway() == "biogas":
            return _warn(self, [("Share of substrate B", self.share_b),
                                ("Retention time", self.hrt)])
        return _warn(self, [("Moisture", self.moisture), ("Heating value", self.lhv),
                            ("Bulk density", self.bulk), ("Ash", self.ash)])


class BiomassPlantPage(StepPage):
    def __init__(self, demand: BiomassDemandPage) -> None:
        super().__init__()
        self.demand = demand
        self._last = ""
        self.setTitle("3. Plant and emissions")
        self.setSubTitle("Plant efficiency, storage and emission factors. The defaults are typical: change them only if you have datasheet values.")
        self.eta_th = NumberField(85, 20, 99, 0, "%", "biomass.plant_power")
        self.eta_el = NumberField(0, 0, 60, 0, "%", "biomass.plant_power")
        self.storage = NumberField(10, 0, 120, 0, "days", "biomass.storage")
        self.truck = NumberField(30, 5, 120, 0, "m3", "biomass.storage")
        self.hours = NumberField(8000, 1000, 8760, 0, "h per year", "biomass.chp_biogas")
        self.parasitic = NumberField(8, 0, 30, 0, "% of the electricity", "biomass.chp_biogas")
        self.dig_heat = NumberField(25, 0, 60, 0, "% of the CHP heat", "biomass.heat_balance")
        self.ref_eff = NumberField(90, 40, 100, 0, "%", "biomass.co2")
        self.ref_ef = NumberField(0.202, 0, 1, 3, "kg CO2/kWh", "biomass.co2")
        self.grid = NumberField(0.25, 0, 2, 3, "kg CO2/kWh", "biomass.co2")
        self.supply = NumberField(0.02, 0, 0.5, 3, "kg CO2/kWh of fuel", "biomass.co2")

        self.eff_form = QFormLayout()
        self.eff_form.addRow("Thermal efficiency", self.eta_th)
        self.eff_form.addRow("Electrical efficiency", self.eta_el)
        self.eff_form.addRow("Fuel autonomy (storage)", self.storage)
        self.eff_form.addRow("Truck capacity", self.truck)
        self.eff_form.addRow("CHP operating hours", self.hours)
        self.eff_form.addRow("Electricity used by the plant", self.parasitic)
        self.eff_form.addRow("Heat used by the digester", self.dig_heat)
        plant = QGroupBox("Plant")
        plant.setLayout(self.eff_form)
        em = QGroupBox("Emissions (CO2 of the biomass itself counted as neutral)")
        ef = QFormLayout(em)
        ef.addRow("Reference heat boiler efficiency", self.ref_eff)
        ef.addRow("Reference fuel (natural gas)", self.ref_ef)
        ef.addRow("Electricity grid", self.grid)
        ef.addRow("Supply chain of the biomass", self.supply)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(plant)
        layout.addWidget(em)
        self.country_bar = CountryBar({"grid_ef": self.grid})
        self.country = self.country_bar.combo
        layout.insertWidget(0, self.country_bar)
        layout.addWidget(_hint(
            "Typical efficiencies: boiler 80-90 %, ORC about 70 % thermal and 15 % electrical, "
            "gas engine about 45 % thermal and 38 % electrical. The supply-chain factor and the "
            "grid factor are placeholders: use your own data."))
        layout.addStretch(1)

    def initializePage(self) -> None:
        self.country_bar.sync()
        key = self.demand.pathway()
        solid, biogas = key != "biogas", key == "biogas"
        if key != self._last:  # new pathway: start from its typical efficiencies
            th, el = default_efficiencies(key)
            self.eta_th.set_value(th * 100)
            self.eta_el.set_value(el * 100)
            self._last = key
        for field, visible in ((self.eta_el, key != "boiler"), (self.storage, solid),
                               (self.truck, solid), (self.hours, biogas),
                               (self.parasitic, biogas), (self.dig_heat, biogas)):
            _show_row(self.eff_form, field, visible)

    def _items(self) -> list[tuple[str, NumberField]]:
        items = [("Thermal efficiency", self.eta_th), ("Reference efficiency", self.ref_eff),
                 ("Reference fuel factor", self.ref_ef), ("Grid factor", self.grid),
                 ("Supply chain factor", self.supply)]
        key = self.demand.pathway()
        if key != "boiler":
            items.append(("Electrical efficiency", self.eta_el))
        if key == "biogas":
            items += [("Operating hours", self.hours), ("Plant electricity", self.parasitic),
                      ("Digester heat", self.dig_heat)]
        else:
            items += [("Storage", self.storage), ("Truck capacity", self.truck)]
        return items

    def validatePage(self) -> bool:
        return _warn(self, self._items())


class BiomassResultsPage(BaseResultsPage):
    """Results of the biomass design; the Why? list follows the chosen pathway."""

    topic_order = BIOMASS_TOPIC_ORDER
    pdf_name = "RESize_biomass_report.pdf"
    has_excel = True

    def __init__(self, demand: BiomassDemandPage, fuel: BiomassFuelPage,
                 plant: BiomassPlantPage) -> None:
        self.demand, self.fuel_page, self.plant = demand, fuel, plant
        super().__init__()
        self.setTitle("4. Results and design checks")

    def initializePage(self) -> None:
        self.topic_order = topics_for(self.demand.pathway())
        self.topics.clear()
        for key in self.topic_order:
            self.topics.addItem(EXPLANATIONS[key]["title"])
        super().initializePage()

    def _inputs_from_pages(self) -> BiomassInputs:
        d, p, f = self.demand, self.plant, self.fuel_page
        key = d.pathway()
        base = BiomassInputs(
            pathway=key,
            annual_heat_demand_kwh=d.heat.value(),
            peak_heat_kw=d.peak.value() if key != "biogas" else 1.0,
            annual_electricity_demand_kwh=d.electricity.value() if key != "boiler" else 0.0,
            coverage=d.coverage.value() / 100.0,
            eta_th=p.eta_th.value() / 100.0,
            eta_el=p.eta_el.value() / 100.0 if key != "boiler" else 0.0,
            reference_heat_efficiency=p.ref_eff.value() / 100.0,
            reference_heat_ef=p.ref_ef.value(),
            grid_ef=p.grid.value(),
            supply_chain_ef=p.supply.value(),
        )
        if key == "biogas":
            return replace(
                base,
                substrate_a=SUBSTRATES[f.sub_a.currentIndex()],
                substrate_b=SUBSTRATES[f.sub_b.currentIndex()],
                share_b=f.share_b.value() / 100.0, hrt_days=f.hrt.value(),
                operating_hours=p.hours.value(),
                parasitic_electricity=p.parasitic.value() / 100.0,
                digester_heat_share=p.dig_heat.value() / 100.0,
            )
        return replace(base, fuel=f.fuel(), storage_days=p.storage.value(),
                       truck_volume_m3=p.truck.value())

    def _compute(self) -> tuple[object, object, list[Finding], str, str]:
        inputs = self._inputs_from_pages()
        design = size_biomass_plant(inputs)
        findings = check_biomass_design(inputs, design)
        light = build_biomass_report(inputs, design, findings, theme="light")
        screen = build_biomass_report(inputs, design, findings, theme="screen")
        return inputs, design, findings, light, screen

    def _flow(self):
        from resize_energy.report.flow_pictures import biomass_picture

        return biomass_picture(self._inputs, self._design)

    def _workbook(self):
        from resize_energy.report.excel_more import build_biomass_workbook

        return build_biomass_workbook(self._inputs, self._design)

    def _worked(self, key: str) -> str | None:
        return biomass_worked_example(key, self._inputs, self._design)

    def _context(self) -> str:
        return build_biomass_context(self._inputs, self._design, self._findings)

    def _charts(self) -> dict[str, ChartSpec]:
        return biomass_charts(self._inputs, self._design)
