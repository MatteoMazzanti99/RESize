"""Keep a version of a project and compare it with the next one (PySide6 glue).

The calculations are in ``core/versions.py``; this module reads the pages' fields, puts them
back, and asks the results page to compute again.
"""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout

from resize_energy.core import versions as ver
from resize_energy.gui import project_io
from resize_energy.gui.provenance import ordered_pages

MAX_CHANGES = 12


def _states(pages) -> list[dict]:
    return [project_io.capture(p) for p in pages]


def _labels(pages) -> dict[tuple[int, str], str]:
    out: dict[tuple[int, str], str] = {}
    for pi, page in enumerate(pages):
        names = {id(obj): name for name, obj in vars(page).items()}
        for form in page.findChildren(QFormLayout):
            for i in range(form.rowCount()):
                f = form.itemAt(i, QFormLayout.ItemRole.FieldRole)
                lab = form.itemAt(i, QFormLayout.ItemRole.LabelRole)
                if f is None or lab is None or f.widget() is None or lab.widget() is None:
                    continue
                name = names.get(id(f.widget()))
                if name:
                    out[(pi, name)] = lab.widget().text()
        for name, obj in vars(page).items():
            if isinstance(obj, QCheckBox) and obj.text():
                out.setdefault((pi, name), obj.text())
            elif isinstance(obj, QComboBox):
                out.setdefault((pi, name), name.replace("_", " "))
    return out


def _apply(pages, states) -> None:
    for page, state in zip(pages, states, strict=False):
        project_io.restore(page, state)


def keep(owner) -> bool:
    """Remember the current inputs and results as version A (False: not supported here)."""
    kpis = ver.read_kpis(owner._design)
    if not kpis:
        return False
    pages = ordered_pages(owner)
    owner._version_a = {"states": _states(pages), "kpis": kpis}
    return True


def compare_sections(owner) -> tuple[str, str]:
    """HTML of 'Compared with version A' (light, screen); empty without a kept version."""
    a = owner._version_a
    if a is None or owner._design is None:
        return "", ""
    try:
        pages = ordered_pages(owner)
        b = ver.read_kpis(owner._design)
        changes = ver.diff_states(a["states"], _states(pages), _labels(pages))
        html = ver.comparison_html(a["kpis"], b, changes)
    except Exception:  # noqa: BLE001 - never break the report for an extra
        return "", ""
    return html, html


def explain(owner) -> tuple[str, str]:
    """Apply each difference alone to version A and report what it did to the results."""
    a = owner._version_a
    if a is None:
        return "", ""
    pages = ordered_pages(owner)
    now = _states(pages)
    b_kpis = ver.read_kpis(owner._design)
    changes = ver.diff_states(a["states"], now, _labels(pages))
    if not changes or len(b_kpis) != len(a["kpis"]):
        return "", ""
    shown = changes[:MAX_CHANGES]
    a_vals = [k.value for k in a["kpis"]]
    singles: dict[int, list[float] | None] = {}
    try:
        for i, ch in enumerate(shown):
            _apply(pages, a["states"])
            project_io.restore(pages[ch.page], {ch.attr: now[ch.page][ch.attr]})
            try:
                design = owner._compute()[1]
            except ValueError:
                singles[i] = None
                continue
            ks = ver.read_kpis(design)
            singles[i] = [k.value for k in ks] if len(ks) == len(a_vals) else None
    finally:
        _apply(pages, now)     # the user's inputs, exactly as they were
    effects, rest = ver.explain(a_vals, [k.value for k in b_kpis], singles, shown)
    html = ver.comparison_html(a["kpis"], b_kpis, shown, effects, rest)
    # keep only the 'why' part: the table and the list are already in the report
    start = html.find("<h3>Why did it change?</h3>")
    note = ("" if len(changes) <= MAX_CHANGES else
            f"<p>Only the first {MAX_CHANGES} of {len(changes)} changes are explained.</p>")
    text = html[start:] + note if start >= 0 else ""
    return text, text
