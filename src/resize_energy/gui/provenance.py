"""Where every input came from: the program's default, a data source, or you (PySide6).

The results page adds a short section listing the values still at the program's defaults,
because those are placeholders nobody has checked. Never raises: if anything goes wrong the
report is simply left as it was.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from PySide6.QtWidgets import QFormLayout, QLabel

from resize_energy.gui.widgets import StepPage

MARKER = "<h2>Method and formulas</h2>"


@dataclass(frozen=True)
class Row:
    step: str
    label: str
    text: str
    status: str            # "default", "changed" or the name of a data source


def _unit(field) -> str:
    labels = [w.text() for w in field.findChildren(QLabel) if w.text()]
    return labels[0] if labels else ""


def collect(pages: list[StepPage]) -> list[Row]:
    from resize_energy.gui.wizard import NumberField  # here: wizard imports this module

    rows: list[Row] = []
    for page in pages:
        step = page.title()
        for form in page.findChildren(QFormLayout):
            for i in range(form.rowCount()):
                field_item = form.itemAt(i, QFormLayout.ItemRole.FieldRole)
                label_item = form.itemAt(i, QFormLayout.ItemRole.LabelRole)
                field = field_item.widget() if field_item else None
                if not isinstance(field, NumberField) or label_item is None:
                    continue
                label = label_item.widget().text() if label_item.widget() else ""
                unit = _unit(field)
                rows.append(Row(step, label, f"{field.edit.text()} {unit}".strip(),
                                field.provenance()))
    return rows


def ordered_pages(owner: object) -> list[StepPage]:
    """The input pages a results page keeps as attributes, in the order of their titles."""
    pages = [v for v in vars(owner).values() if isinstance(v, StepPage)]
    return sorted(pages, key=lambda p: p.title())


def section_html(rows: list[Row]) -> str:
    if not rows:
        return ""
    sources = sorted({r.status for r in rows if r.status not in ("default", "changed")})
    defaults = [r for r in rows if r.status == "default"]
    changed = [r for r in rows if r.status == "changed"]
    parts = ["<h2>Which values to check</h2>",
             f"<p>Of the {len(rows)} numbers in this project, <b>{len(defaults)}</b> are still "
             f"the values proposed by the program, <b>{len(changed)}</b> were changed by you"
             + (f" and {sum(r.status in sources for r in rows)} came from "
                f"{' and '.join(sources)}" if sources else "")
             + ". The program's values are typical or placeholder figures: they make the "
             "calculation run, but nobody has checked them for your case.</p>"]
    if defaults:
        steps: dict[str, list[Row]] = {}
        for r in defaults:
            steps.setdefault(r.step, []).append(r)
        parts.append("<p><b>Still at the program's value</b> (check before relying on the "
                     "result):</p><ul>")
        for step, items in steps.items():
            parts.append("<li><i>" + escape(step) + ":</i> "
                         + "; ".join(f"{escape(r.label)} = {escape(r.text)}" for r in items)
                         + "</li>")
        parts.append("</ul>")
    return "".join(parts)


def insert_before_formulas(html: str, section: str) -> str:
    """Put ``section`` before the formulas; the report itself when it cannot be placed."""
    if not section or MARKER not in html:
        return html
    return html.replace(MARKER, section + MARKER, 1)


def provenance_section(owner: object) -> str:
    try:
        return section_html(collect(ordered_pages(owner)))
    except Exception:  # noqa: BLE001 - a report must never fail because of this extra
        return ""
