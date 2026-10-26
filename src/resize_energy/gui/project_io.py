"""Turn the fields of the step pages into a saved project and back (PySide6).

Every ``NumberField``, drop-down and check box that a page keeps as an attribute is saved
by its attribute name, so a new field is saved without writing anything else.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QCheckBox, QComboBox

from resize_energy.core import profiles as prof
from resize_energy.core.wind_rose import WindRose
from resize_energy.gui.wizard import NumberField


def capture(page: Any) -> dict[str, Any]:
    """The state of one page: {attribute: value}. Weather years are returned apart."""
    state: dict[str, Any] = {}
    for name, obj in vars(page).items():
        if isinstance(obj, NumberField):
            state[name] = {"num": obj.edit.text()}
            if obj.source:
                state[name]["src"] = obj.source
        elif isinstance(obj, QComboBox):
            state[name] = {"idx": obj.currentIndex(), "text": obj.currentText()}
        elif isinstance(obj, QCheckBox):
            state[name] = {"on": obj.isChecked()}
    rose = getattr(page, "_rose", None)
    if isinstance(rose, WindRose):
        state["_rose"] = {"rose": rose.to_dict()}
    implied = getattr(page, "_implied_pr", None)
    if isinstance(implied, float):
        state["_implied_pr"] = {"num": repr(implied)}
    return state


def weather_of(page: Any) -> prof.HourlyWeather | None:
    w = getattr(page, "_weather", None)
    return w if isinstance(w, prof.HourlyWeather) else None


def restore(page: Any, state: dict[str, Any], weather: prof.HourlyWeather | None = None) -> list[str]:
    """Put the saved values back. Returns the names of the fields that could not be restored.

    Drop-downs and check boxes go first: changing them can reset other fields (the turbine
    model fills its datasheet values), which the saved numbers must then overwrite.
    """
    problems: list[str] = []
    widgets = vars(page)
    for name, saved in state.items():
        obj = widgets.get(name)
        try:
            if isinstance(obj, QComboBox) and "text" in saved:
                idx = obj.findText(saved["text"])
                if idx < 0:
                    idx = int(saved.get("idx", -1))
                if 0 <= idx < obj.count():
                    obj.setCurrentIndex(idx)
                else:
                    problems.append(name)
            elif isinstance(obj, QCheckBox) and "on" in saved:
                obj.setChecked(bool(saved["on"]))
        except (TypeError, ValueError, KeyError):
            problems.append(name)
    for name, saved in state.items():
        obj = widgets.get(name)
        try:
            if isinstance(obj, NumberField) and "num" in saved:
                obj.edit.setText(str(saved["num"]))
                obj._mark()
                obj.source = saved.get("src")
            elif name == "_implied_pr" and "num" in saved:
                page._implied_pr = float(saved["num"])
            elif name == "_rose" and "rose" in saved and hasattr(page, "restore_rose"):
                page.restore_rose(WindRose.from_dict(saved["rose"]))
        except (TypeError, ValueError, KeyError):
            problems.append(name)
    if weather is not None and hasattr(page, "_weather"):
        page._weather = weather
    return problems
