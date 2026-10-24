"""HTML for one 'Why?' topic (used by the GUI panel and the PDF report)."""

from __future__ import annotations

from html import escape

from resize_energy.report.formula_art import register, worked_html
from resize_energy.tutor.cost_sources import costs_html
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.sources import SOURCES, sources_html


def _multiline(text: str) -> str:
    return "<br>".join(escape(line) for line in text.split("\n"))


def explanation_html(key: str, worked: str | None = None, heading: bool = True,
                     math: bool = False, full_refs: bool = False) -> str:
    """Formula, reasoning, user's numbers (if given), assumptions and reference of a topic.

    With ``math`` the formula is a picture (``<img src="chart:fx_...">``, drawn by
    :mod:`resize_energy.report.formula_art`; the window or the PDF document must answer it)
    and the numbers are set in the body font; without it both are plain text.
    """
    entry = EXPLANATIONS.get(key)
    if entry is None:
        return "<p>No explanation is available for this step yet.</p>"
    parts: list[str] = []
    if heading:
        parts.append(f"<h3>{escape(entry['title'])}</h3>")
    if math:
        picture = register(entry["formula"])
        parts.append(f'<p><b>Formula</b><br><img src="chart:{picture.key}" width="{picture.w}" '
                     f'height="{picture.h}"></p>')
    else:
        parts.append(f"<p><b>Formula</b><br><code>{escape(entry['formula'])}</code></p>")
    parts.append(f"<p><b>Why</b><br>{escape(entry['why'])}</p>")
    if worked and math:
        parts.append(f"<p><b>With your numbers</b><br>{worked_html(worked)}</p>")
    elif worked:
        parts.append(f"<p><b>With your numbers</b><br><code>{_multiline(worked)}</code></p>")
    parts.append(f"<p><i>Assumptions: {escape(entry['assumptions'])}</i></p>")
    parts.append(costs_html(key))
    if key in SOURCES:
        parts.append(sources_html(key, full=full_refs))
    elif entry.get("reference"):
        parts.append(f"<p><i>Reference: {escape(entry['reference'])}</i></p>")
    return "".join(parts)
