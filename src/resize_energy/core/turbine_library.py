"""Library of real and reference wind turbines with published power curves.

The data come from NREL's turbine-models archive (BSD-3-Clause), converted by
``tools/build_turbine_library.py`` into ``data/turbines.json``. See THIRD_PARTY_NOTICES.md.
Most curves are 'theoretical' (manufacturer or model based), not measured on site.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

from resize_energy.core.wind_design import TurbineSpec

SOURCE = "NREL turbine-models (BSD-3-Clause)"


@dataclass(frozen=True)
class LibraryTurbine:
    id: str
    name: str
    group: str  # "onshore" or "distributed"
    rated_power_kw: float
    rotor_diameter_m: float
    hub_height_m: float | None
    cut_in_ms: float
    rated_speed_ms: float
    cut_out_ms: float
    curve: tuple[tuple[float, float], ...]

    @property
    def label(self) -> str:
        power = (f"{self.rated_power_kw / 1000:g} MW" if self.rated_power_kw >= 1000
                 else f"{self.rated_power_kw:g} kW")
        return f"{self.name} ({power}, D {self.rotor_diameter_m:g} m)"

    def to_spec(self, default_hub_height_m: float = 80.0) -> TurbineSpec:
        return TurbineSpec(
            name=self.name,
            rated_power_kw=self.rated_power_kw,
            rotor_diameter_m=self.rotor_diameter_m,
            hub_height_m=self.hub_height_m or default_hub_height_m,
            cut_in_ms=self.cut_in_ms,
            rated_speed_ms=self.rated_speed_ms,
            cut_out_ms=self.cut_out_ms,
            power_curve=self.curve,
            curve_source=SOURCE,
        )


@lru_cache(maxsize=1)
def load_library() -> tuple[LibraryTurbine, ...]:
    """All turbines, large machines first within each group (onshore, then distributed)."""
    text = (resources.files("resize_energy") / "data" / "turbines.json").read_text("utf-8")
    items = json.loads(text)["turbines"]
    turbines = [
        LibraryTurbine(
            id=t["id"], name=t["name"], group=t["group"],
            rated_power_kw=t["rated_power_kw"], rotor_diameter_m=t["rotor_diameter_m"],
            hub_height_m=t["hub_height_m"], cut_in_ms=t["cut_in_ms"],
            rated_speed_ms=t["rated_speed_ms"], cut_out_ms=t["cut_out_ms"],
            curve=tuple((float(v), float(p)) for v, p in t["curve"]),
        )
        for t in items
    ]
    order = {"onshore": 0, "distributed": 1}
    turbines.sort(key=lambda t: (order.get(t.group, 9), -t.rated_power_kw, t.name))
    return tuple(turbines)


def get_turbine(turbine_id: str) -> LibraryTurbine:
    for t in load_library():
        if t.id == turbine_id:
            return t
    raise KeyError(turbine_id)
