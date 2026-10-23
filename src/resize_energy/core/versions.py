"""Compare two versions of the same project: what changed, and what each change did.

Qt-free. A *version* is the saved state of every step (see ``gui/project_io``) and the key
results of its design. ``diff_states`` lists the inputs that differ; ``explain`` splits the
difference of each result among those inputs, one at a time from version A, and says how much
is left to their interaction.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from typing import Any


@dataclass(frozen=True)
class KpiSpec:
    path: str          # dotted attribute path on the design, e.g. "economics.npv"
    label: str
    unit: str
    decimals: int = 0
    scale: float = 1.0  # shown value = raw x scale (0.01 turns a share into percent... see pct)


def pct(path: str, label: str) -> KpiSpec:
    return KpiSpec(path, label, "%", 0, 100.0)


KPI_SPECS: dict[str, tuple[KpiSpec, ...]] = {
    "PVDesign": (
        KpiSpec("dc_power_kwp", "Installed power", "kWp", 1),
        KpiSpec("annual_energy_kwh", "Energy per year", "kWh"),
        pct("achieved_coverage", "Demand covered"),
        KpiSpec("economics.lcoe", "Cost of energy", "euro/kWh", 3),
        KpiSpec("economics.payback_years", "Payback", "years", 1),
        KpiSpec("economics.npv", "Net present value", "euro"),
    ),
    "WindDesign": (
        KpiSpec("installed_power_kw", "Installed power", "kW"),
        KpiSpec("annual_energy_kwh", "Energy per year", "kWh"),
        pct("capacity_factor_net", "Capacity factor"),
        pct("wake_loss", "Wake loss"),
        KpiSpec("economics.lcoe", "Cost of energy", "euro/kWh", 3),
        KpiSpec("economics.npv", "Net present value", "euro"),
    ),
    "SolarThermalDesign": (
        KpiSpec("area_m2", "Collector area", "m2", 1),
        pct("run.solar_fraction", "Solar fraction"),
        KpiSpec("solar_useful_kwh", "Useful solar energy", "kWh"),
        KpiSpec("lcoh", "Cost of solar energy", "euro/kWh", 3),
        KpiSpec("payback_years", "Payback", "years", 1),
        KpiSpec("npv", "Net present value", "euro"),
    ),
    "BatteryDesign": (
        KpiSpec("capacity_kwh", "Capacity", "kWh", 1),
        pct("self_sufficiency", "Self-sufficiency"),
        KpiSpec("cycles_per_year", "Cycles per year", ""),
        KpiSpec("lcos", "Cost of storage", "euro/kWh", 3),
        KpiSpec("payback_years", "Payback", "years", 1),
        KpiSpec("npv", "Net present value", "euro"),
    ),
    "HydrogenDesign": (
        KpiSpec("electrolyser_kw", "Electrolyser", "kW"),
        KpiSpec("hydrogen_kg", "Hydrogen per year", "kg"),
        KpiSpec("full_load_hours", "Full-load hours", "h"),
        KpiSpec("lcoh", "Cost of hydrogen", "euro/kg", 2),
        KpiSpec("co2_kg_per_kg", "Carbon intensity", "kg CO2/kg", 2),
    ),
    "BiomassDesign": (
        KpiSpec("thermal_power_kw", "Heat power", "kW"),
        KpiSpec("electric_power_kw", "Electric power", "kW"),
        KpiSpec("mass_t_per_year", "Fuel or substrate", "t/year"),
        KpiSpec("co2_avoided_t_per_year", "CO2 avoided", "t/year", 1),
    ),
}


@dataclass(frozen=True)
class Kpi:
    label: str
    unit: str
    decimals: int
    value: float          # already scaled for display


def _get(obj: Any, path: str) -> float | None:
    for part in path.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    try:
        v = float(obj)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def read_kpis(design: object) -> list[Kpi]:
    """The key results of a design that has an entry in ``KPI_SPECS`` (others: empty)."""
    out = []
    for spec in KPI_SPECS.get(type(design).__name__, ()):
        v = _get(design, spec.path)
        if v is not None:
            out.append(Kpi(spec.label, spec.unit, spec.decimals, v * spec.scale))
    return out


@dataclass(frozen=True)
class Change:
    page: int
    attr: str
    label: str
    old: str
    new: str


def _canon(entry: dict[str, Any]) -> Any:
    if "num" in entry:
        text = str(entry["num"]).strip().replace(",", ".")
        try:
            return round(float(text), 9)
        except ValueError:
            return text
    if "text" in entry:
        return entry["text"]
    if "on" in entry:
        return bool(entry["on"])
    return None


def _show(entry: dict[str, Any]) -> str:
    if "num" in entry:
        return str(entry["num"])
    if "text" in entry:
        return str(entry["text"])
    if "on" in entry:
        return "yes" if entry["on"] else "no"
    return ""


def diff_states(a: Sequence[dict[str, Any]], b: Sequence[dict[str, Any]],
                labels: dict[tuple[int, str], str]) -> list[Change]:
    """Inputs whose value differs between two saved states (page by page)."""
    out = []
    for pi, (pa, pb) in enumerate(zip(a, b, strict=False)):
        for attr, eb in pb.items():
            ea = pa.get(attr)
            if ea is None or attr.startswith("_"):
                continue
            if _canon(ea) != _canon(eb):
                out.append(Change(pi, attr, labels.get((pi, attr), attr),
                                  _show(ea), _show(eb)))
    return out


@dataclass(frozen=True)
class Effect:
    change: Change
    deltas: tuple[float | None, ...]     # per KPI: result with only this change minus A


def explain(a: Sequence[float], b: Sequence[float],
            singles: dict[int, Sequence[float] | None], changes: Sequence[Change]
            ) -> tuple[list[Effect], tuple[float, ...]]:
    """Effect of every change alone, starting from A, and what is left for interactions."""
    effects, sums = [], [0.0] * len(a)
    for i, ch in enumerate(changes):
        s = singles.get(i)
        if s is None or len(s) != len(a):
            effects.append(Effect(ch, (None,) * len(a)))
            continue
        d = tuple(s[k] - a[k] for k in range(len(a)))
        effects.append(Effect(ch, d))
        for k, v in enumerate(d):
            sums[k] += v
    rest = tuple((b[k] - a[k]) - sums[k] for k in range(len(a)))
    return effects, rest


def _fmt(v: float, decimals: int, signed: bool = False) -> str:
    return f"{v:+,.{decimals}f}" if signed else f"{v:,.{decimals}f}"


def comparison_html(a: Sequence[Kpi], b: Sequence[Kpi], changes: Sequence[Change],
                    effects: Sequence[Effect] | None = None,
                    rest: Sequence[float] | None = None, top: int = 3) -> str:
    """The section 'Compared with version A': results, inputs changed and, if asked, why."""
    if not a or not b or len(a) != len(b):
        return ""
    rows = "".join(
        f"<tr><td>{escape(x.label)}</td><td align=\"right\">{_fmt(x.value, x.decimals)} "
        f"{escape(x.unit)}</td><td align=\"right\">{_fmt(y.value, y.decimals)} "
        f"{escape(y.unit)}</td><td align=\"right\">{_fmt(y.value - x.value, y.decimals, True)}"
        f"</td></tr>" for x, y in zip(a, b, strict=True))
    out = ["<h2>Compared with version A</h2>",
           "<table><tr><th align=\"left\">Result</th><th align=\"right\">Version A</th>"
           "<th align=\"right\">This version</th><th align=\"right\">Difference</th></tr>"
           + rows + "</table>"]
    if not changes:
        out.append("<p>The inputs are the same as in version A.</p>")
        return "".join(out)
    out.append(f"<p><b>{len(changes)}</b> input(s) differ from version A:</p><ul>"
               + "".join(f"<li>{escape(c.label)}: {escape(c.old)} &rarr; {escape(c.new)}</li>"
                         for c in changes) + "</ul>")
    if effects:
        k = min(top, len(a))
        head = "".join(f"<th align=\"right\">{escape(x.label)}</th>" for x in a[:k])
        body = ""
        for e in effects:
            cells = "".join(
                "<td align=\"right\">" + ("n/a" if d is None
                                          else _fmt(d, a[j].decimals, True)) + "</td>"
                for j, d in enumerate(e.deltas[:k]))
            body += f"<tr><td>{escape(e.change.label)}</td>{cells}</tr>"
        if rest is not None and any(abs(r) > 10 ** -(a[j].decimals + 1)
                                    for j, r in enumerate(rest[:k])):
            cells = "".join(f"<td align=\"right\">{_fmt(r, a[j].decimals, True)}</td>"
                            for j, r in enumerate(rest[:k]))
            body += f"<tr><td><i>Interaction between the changes</i></td>{cells}</tr>"
        out.append("<h3>Why did it change?</h3><p>Each change applied alone to version A. "
                   "The rows add up to the difference above, up to the interaction row: when "
                   "two inputs act together their effects are not simply additive.</p>"
                   "<table><tr><th align=\"left\">Input changed</th>" + head + "</tr>"
                   + body + "</table>")
    return "".join(out)
