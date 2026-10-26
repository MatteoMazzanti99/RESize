"""The RESize project file (``.resize``): what is saved, how it is read back.

A project is a small JSON document with the technology, the value of every field of every
step and, when it was downloaded, the real hourly weather year. No Qt here, so the format
can be tested everywhere. The GUI (``gui/project_io.py``) turns widgets into this form.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from resize_energy import __version__
from resize_energy.core import profiles as prof

FORMAT = "resize-project"
FORMAT_VERSION = 1
EXTENSION = ".resize"
TECHS = ("pv", "wind", "biomass", "hydrogen", "battery", "solar", "hydro", "geothermal", "compare")


class ProjectError(ValueError):
    """The file cannot be used; the message says why in plain words."""


@dataclass
class Project:
    tech: str
    pages: list[dict[str, Any]] = field(default_factory=list)   # one dict per step, in order
    compare_techs: tuple[str, ...] = ()
    weather: dict[str, prof.HourlyWeather] = field(default_factory=dict)  # page index -> year
    note: str = ""


def _weather_to_json(w: prof.HourlyWeather) -> dict[str, Any]:
    return {"year": w.year, "source": w.source,
            "wind50": [round(v, 3) for v in w.wind50_ms],
            "ghi": [round(v, 2) for v in w.ghi_w_m2]}


def _weather_from_json(d: Any) -> prof.HourlyWeather:
    try:
        wind, ghi = [float(v) for v in d["wind50"]], [float(v) for v in d["ghi"]]
        if len(wind) != prof.HOURS or len(ghi) != prof.HOURS:
            raise ValueError("wrong number of hours")
        return prof.HourlyWeather(tuple(wind), tuple(ghi), int(d["year"]),
                                  str(d.get("source", "NASA POWER")))
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectError(f"the saved weather data is damaged ({exc})") from exc


def dumps(project: Project) -> str:
    """The text to write to the file."""
    if project.tech not in TECHS:
        raise ProjectError(f"unknown technology {project.tech!r}")
    doc = {
        "format": FORMAT, "version": FORMAT_VERSION, "app_version": __version__,
        "tech": project.tech, "compare_techs": list(project.compare_techs),
        "note": project.note, "pages": project.pages,
        "weather": {k: _weather_to_json(v) for k, v in project.weather.items()},
    }
    return json.dumps(doc, indent=1, ensure_ascii=False)


def loads(text: str) -> Project:
    """Read a project; raises :class:`ProjectError` with a readable message when it is not valid."""
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProjectError("this is not a RESize project file (it is not readable text)") from exc
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise ProjectError("this file is not a RESize project")
    version = doc.get("version")
    if not isinstance(version, int) or version < 1:
        raise ProjectError("the project has no valid version number")
    if version > FORMAT_VERSION:
        raise ProjectError(f"the project was saved by a newer RESize (file format {version}, "
                           f"this one reads up to {FORMAT_VERSION}): update the app")
    tech = doc.get("tech")
    if tech not in TECHS:
        raise ProjectError(f"unknown technology {tech!r} in the project")
    pages = doc.get("pages")
    if not isinstance(pages, list) or not all(isinstance(p, dict) for p in pages):
        raise ProjectError("the saved steps are damaged")
    techs = doc.get("compare_techs", [])
    if not isinstance(techs, list) or not all(isinstance(t, str) for t in techs):
        raise ProjectError("the saved list of compared technologies is damaged")
    weather_doc = doc.get("weather", {})
    if not isinstance(weather_doc, dict):
        raise ProjectError("the saved weather data is damaged")
    return Project(tech=tech, pages=pages, compare_techs=tuple(techs),
                   weather={str(k): _weather_from_json(v) for k, v in weather_doc.items()},
                   note=str(doc.get("note", "")))


def default_name(tech: str) -> str:
    return f"RESize_{tech}{EXTENSION}"
