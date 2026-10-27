"""What the live-preview panel shows (pure data, no Qt, so it can be tested)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preview:
    """One headline number, a small bar chart and a few one-line checks."""

    label: str                                   # "Yearly yield, as you type"
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


def pv_preview(inputs, design, findings) -> Preview:
    """Preview of a photovoltaic design: yearly energy, the months and the design checks."""
    value, unit = _energy(design.annual_energy_kwh)
    notes: list[tuple[str, str]] = []
    for finding in findings:
        if finding.severity in ("error", "warning"):
            notes.append((finding.severity, finding.message))
    if not notes:
        notes.append(("ok", "All design checks pass."))
    extra = (
        ("Array power", f"{design.dc_power_kwp:,.1f} kWp"),
        ("Covers", f"{design.achieved_coverage:.0%} of the demand"),
    )
    return Preview(
        label="Yearly energy, as you type", value=value, unit=unit,
        bars=tuple(design.monthly_kwh or ()), bar_labels=("Jan", "Jun", "Dec"),
        notes=tuple(notes[:3]), extra=extra,
    )
