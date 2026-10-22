"""HTML for one 'Why?' topic (used by the GUI panel and the PDF report)."""

from __future__ import annotations

from html import escape

from resize_energy.tutor.explanations import EXPLANATIONS


def _multiline(text: str) -> str:
    return "<br>".join(escape(line) for line in text.split("\n"))


def explanation_html(key: str, worked: str | None = None, heading: bool = True) -> str:
    """Formula, reasoning, user's numbers (if given), assumptions and reference of a topic."""
    entry = EXPLANATIONS.get(key)
    if entry is None:
        return "<p>No explanation is available for this step yet.</p>"
    parts: list[str] = []
    if heading:
        parts.append(f"<h3>{escape(entry['title'])}</h3>")
    parts.append(f"<p><b>Formula</b><br><code>{escape(entry['formula'])}</code></p>")
    parts.append(f"<p><b>Why</b><br>{escape(entry['why'])}</p>")
    if worked:
        parts.append(f"<p><b>With your numbers</b><br><code>{_multiline(worked)}</code></p>")
    parts.append(f"<p><i>Assumptions: {escape(entry['assumptions'])}</i></p>")
    reference = entry.get("reference")
    if reference:
        parts.append(f"<p><i>Reference: {escape(reference)}</i></p>")
    return "".join(parts)
