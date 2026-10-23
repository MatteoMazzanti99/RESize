"""'Costs and savings' step shared by the photovoltaic and wind flows (PySide6)."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGroupBox, QMessageBox, QVBoxLayout

from resize_energy.core.plant_economics import EconomicInputs
from resize_energy.gui.widgets import StepPage
from resize_energy.gui.wizard import NumberField, _hint, first_error

# Round placeholder values (euro, 2025-26 order of magnitude): replace them with quotes.
_DEFAULTS = {
    "pv": dict(capex=1100.0, om=15.0, life=25.0, lifecycle=45.0, unit="kWp",
               text="Small rooftop and ground-mounted plants cost about 900-1,500 euro/kWp "
                    "installed. Maintenance is mostly cleaning and the inverter reserve."),
    "wind": dict(capex=1700.0, om=45.0, life=25.0, lifecycle=12.0, unit="kW",
                 text="Onshore turbines cost about 1,300-2,200 euro/kW installed (small wind "
                      "is much more expensive). Maintenance is a larger share than for PV."),
}


class PlantCostPage(StepPage):
    """Asks for costs, prices and finance. ``kind`` is "pv" or "wind"."""

    def __init__(self, kind: str, number: int) -> None:
        super().__init__()
        d = _DEFAULTS[kind]
        e = EconomicInputs()
        self.kind = kind
        unit = d["unit"]
        key = f"{kind}.economics"
        self.setTitle(f"{number}. Costs and savings")
        self.setSubTitle("What the plant costs and what the electricity is worth. The defaults "
                         "are round placeholders: replace them with quotes and your tariff.")
        self.capex = NumberField(d["capex"], 0, 20000, 0, f"euro per {unit}", key)
        self.om = NumberField(d["om"], 0, 1000, 0, f"euro per {unit} per year", key)
        self.life = NumberField(d["life"], 1, 60, 0, "years", key)
        self.rate = NumberField(e.discount_rate * 100, 0, 30, 1, "%", key)
        self.retail = NumberField(e.retail_price, 0.001, 2, 3, "euro/kWh bought", key)
        self.export = NumberField(e.export_price, 0, 2, 3, "euro/kWh sold", key)
        self.ef = NumberField(e.grid_ef, 0, 2, 3, "kg CO2/kWh", f"{kind}.economics")
        self.lifecycle = NumberField(d["lifecycle"], 0, 500, 0, "g CO2/kWh", f"{kind}.economics")

        plant = QGroupBox("Plant cost")
        pf = QFormLayout(plant)
        pf.addRow(f"Installed cost per {unit}", self.capex)
        pf.addRow("Operation and maintenance", self.om)
        pf.addRow("Lifetime", self.life)
        money = QGroupBox("Electricity and finance")
        mf = QFormLayout(money)
        mf.addRow("Price you pay for electricity", self.retail)
        mf.addRow("Price you are paid for the surplus", self.export)
        mf.addRow("Discount rate", self.rate)
        co2 = QGroupBox("Carbon")
        cf = QFormLayout(co2)
        cf.addRow("Grid emission factor", self.ef)
        cf.addRow("Life-cycle emissions of the plant", self.lifecycle)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(plant)
        layout.addWidget(money)
        layout.addWidget(co2)
        layout.addWidget(_hint(
            d["text"] + " The saving counts the energy you use at the price you pay and the "
            "surplus at the export price. No incentives, taxes or financing are included."))
        layout.addStretch(1)

    def inputs(self) -> EconomicInputs:
        return EconomicInputs(
            capex_per_kw=self.capex.value(), om_per_kw_year=self.om.value(),
            life_years=self.life.value(), discount_rate=self.rate.value() / 100.0,
            retail_price=self.retail.value(), export_price=self.export.value(),
            grid_ef=self.ef.value(), lifecycle_g_per_kwh=self.lifecycle.value())

    def validatePage(self) -> bool:
        error = first_error([
            ("Cost", self.capex), ("Maintenance", self.om), ("Lifetime", self.life),
            ("Price paid", self.retail), ("Price received", self.export),
            ("Discount rate", self.rate), ("Emission factor", self.ef),
            ("Life-cycle emissions", self.lifecycle)])
        if error:
            QMessageBox.warning(self, "Check the value", error)
            return False
        return True
