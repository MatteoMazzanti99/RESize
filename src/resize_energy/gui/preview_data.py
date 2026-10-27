"""What the live-preview panel shows (pure data, no Qt, so it can be tested)."""

from __future__ import annotations

from dataclasses import dataclass

from resize_energy.core.versions import read_kpis
from resize_energy.gui.kpi_format import format_value

# Which key number is the big one (index in KPI_SPECS); the first one otherwise.
HEADLINE = {"PVDesign": 1, "WindDesign": 1}


@dataclass(frozen=True)
class Preview:
    """One headline number, a small bar chart and a few one-line checks."""

    label: str                                   # "Energy per year"
    value: str                                   # "73.4"
    unit: str                                    # "MWh"
    bars: tuple[float, ...] = ()                 # e.g. the 12 months
    bar_labels: tuple[str, ...] = ()             # shown under the first, middle and last bar
    notes: tuple[tuple[str, str], ...] = ()      # (kind, text): kind is ok / warning / error
    extra: tuple[tuple[str, str], ...] = ()      # small (label, value) rows


def _energy(kwh: float) -> tuple[str, str]:
    if abs(kwh) >= 1e6:
        return f"{kwh / 1e6:.2f}", "GWh"
    if abs(kwh) >= 1e4:
        return f"{kwh / 1e3:,.1f}", "MWh"
    return f"{kwh:,.0f}", "kWh"


def _shown(kpi) -> tuple[str, str]:
    if kpi.unit == "kWh":
        return _energy(kpi.value)
    return format_value(kpi.value, kpi.decimals), kpi.unit


def design_preview(design, findings) -> Preview:
    """Preview of any design that has key numbers: the main one, three more, the checks."""
    kpis = read_kpis(design)
    if not kpis:
        raise ValueError("this design has no preview")
    head = min(HEADLINE.get(type(design).__name__, 0), len(kpis) - 1)
    value, unit = _shown(kpis[head])
    extra = []
    for i, kpi in enumerate(kpis):
        if i == head or len(extra) == 3:
            continue
        number, u = _shown(kpi)
        extra.append((kpi.label, f"{number} {u}".strip()))
    notes = [(f.severity, f.message) for f in findings if f.severity in ("error", "warning")]
    if not notes:
        notes.append(("ok", "All design checks pass."))
    months = tuple(getattr(design, "monthly_kwh", None) or ())
    return Preview(
        label=kpis[head].label, value=value, unit=unit, bars=months,
        bar_labels=("Jan", "Jun", "Dec") if months else (), notes=tuple(notes[:3]),
        extra=tuple(extra),
    )
