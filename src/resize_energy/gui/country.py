"""Country selector for the cost pages (PySide6).

Choosing a country fills the electricity price, the price paid for the surplus, the heat price
and the grid emission factor with the typical values of that country (see
:mod:`resize_energy.core.countries`). Every value stays editable, and the "Which values to
check" list of the report shows that it came from the country preset.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from resize_energy.core.countries import COUNTRIES, DATA_YEAR, get_country
from resize_energy.gui.wizard import NumberField

CUSTOM = "Custom values (type your own)"
_chosen = ""        # country picked on an earlier page of this project, "" = none


def forget_choice() -> None:
    """Start of a new project: no country has been picked yet."""
    global _chosen
    _chosen = ""


class CountryBar(QWidget):
    """A label, a drop-down and a one-line note. ``fields`` maps what to fill to the fields.

    Keys: ``electricity``, ``export``, ``heat`` (euro per kWh of boiler heat) and ``grid_ef``.
    The drop-down itself is ``self.combo``; pages keep it as an attribute named ``country`` so
    that saved projects remember the choice.
    """

    def __init__(self, fields: dict[str, NumberField]) -> None:
        super().__init__()
        self.fields = fields
        self.combo = QComboBox()
        self.combo.addItem(CUSTOM, "")
        for c in COUNTRIES:
            self.combo.addItem(c.name, c.code)
        self.combo.setToolTip("Fill the prices and the grid emission factor with typical "
                              "values of a country. You can still edit every number.")
        self.combo.activated.connect(self._picked)   # only the user's choice, not setCurrentIndex
        self.note = QLabel("Or pick a country to start from its typical prices and grid "
                           f"emissions ({DATA_YEAR}). You can edit any value afterwards.")
        self.note.setObjectName("hint")
        self.note.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(QLabel("Country"))
        row.addWidget(self.combo, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self.note)

    def _picked(self, _index: int) -> None:
        global _chosen
        _chosen = str(self.combo.currentData() or "")
        self.apply(_chosen)

    def apply(self, code: str) -> None:
        """Fill the fields from the country ``code`` ('' leaves the numbers as they are)."""
        if not code:
            return
        c = get_country(code)
        source = f"{c.name} preset ({DATA_YEAR})"
        values = {"electricity": c.electricity_eur_kwh, "export": c.export_eur_kwh,
                  "heat": c.heat_eur_kwh, "grid_ef": c.grid_kg_co2_kwh}
        for key, field in self.fields.items():
            if key in values:
                field.set_value(round(values[key], 3), source)
        self.note.setText(c.note)

    def sync(self) -> None:
        """On arriving at the page: follow the country chosen earlier, unless this page
        already has its own choice."""
        if _chosen and self.combo.currentIndex() == 0:
            index = self.combo.findData(_chosen)
            if index > 0:
                self.combo.setCurrentIndex(index)
                self.apply(_chosen)
