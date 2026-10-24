"""Country selector for the cost pages (PySide6).

Choosing a country fills the electricity price, the price paid for the surplus, the heat price
and the grid emission factor with the typical values of that country (see
:mod:`resize_energy.core.countries`). Every value stays editable, and the "Which values to
check" list of the report shows that it came from the country preset.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from resize_energy.core import geo
from resize_energy.core.countries import COUNTRIES, DATA_YEAR, get_country
from resize_energy.gui.theme import COLORS
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
        self.site: tuple[NumberField, NumberField] | None = None   # latitude and longitude fields
        self.warning = QLabel()
        self.warning.setWordWrap(True)
        self.warning.setStyleSheet(f"color: {COLORS['warning']}; font-weight: 600;")
        self.warning.hide()
        row = QHBoxLayout()
        row.addWidget(QLabel("Country"))
        row.addWidget(self.combo, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self.note)
        layout.addWidget(self.warning)

    def check_site(self) -> str:
        """Warn when the coordinates typed in the site step are not in the chosen country.

        Returns the warning text ('' when there is nothing to say)."""
        text = ""
        code = str(self.combo.currentData() or "")
        if code and self.site is not None:
            try:
                lat, lon = self.site[0].value(), self.site[1].value()
            except ValueError:
                lat = lon = None
            if lat is not None and geo.in_country(code, lat, lon) is False:
                here = geo.country_near(lat, lon)
                where = f"in {geo.country_name(here)}" if here else "not in any country (open sea?)"
                text = (f"Check the country: the site coordinates ({lat:.4f}, {lon:.4f}) are "
                        f"{where}, not in {get_country(code).name}. The prices and the grid "
                        "emission factor may not match your site.")
                if geo.distance_to_country_km(code, lat, lon, 3.0) < 3.0:
                    text += (" The site is within about 3 km of the border, and the border data "
                             "is accurate to 1-2 km: if the plant is on the "
                             f"{get_country(code).name} side, ignore this note.")
        self.warning.setText(text)
        self.warning.setVisible(bool(text))
        return text

    def _picked(self, _index: int) -> None:
        global _chosen
        _chosen = str(self.combo.currentData() or "")
        self.apply(_chosen)
        self.check_site()

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
        self.check_site()
