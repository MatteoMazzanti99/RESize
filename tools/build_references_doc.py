"""Writes docs/references.md from the bibliography and the topic-to-source map.

    PYTHONPATH=src python tools/build_references_doc.py
"""

from __future__ import annotations

import re
from pathlib import Path

from resize_energy.tutor.bibliography import REFS, full_citation
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.sources import SOURCES

OUT = Path(__file__).resolve().parents[1] / "docs" / "references.md"


def md(html: str) -> str:
    text = re.sub(r"<a href=\"([^\"]+)\">[^<]*</a>", r"<\1>", html)
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text)
    return text.replace("&#x27;", "'").replace("&amp;", "&")


def main() -> None:
    lines = ["# References", "",
             "Every formula and typical value in RESize points to a publication, a standard or a "
             "dataset. Open the **Why?** panel of any step to see the sources of that step; the PDF "
             "report ends with the references it cites.", "",
             "Standards and reports are revised: use the current edition when you cite them. Where "
             "a choice is RESize's own simplification and has no external source, the panel says so.",
             "", "## Bibliography", ""]
    for key in sorted(REFS, key=lambda k: REFS[k].short.lower()):
        lines.append(f"- {md(full_citation(key))}")
    lines += ["", "## Sources by topic", ""]
    for topic, entry in SOURCES.items():
        title = EXPLANATIONS[topic]["title"]
        lines.append(f"### {title}")
        lines.append("")
        for label, items in (("Formula", entry["formula"]), ("Values and assumptions", entry["values"])):
            if items:
                cites = "; ".join(REFS[k].short + (f", {n}" if n else "") for k, n in items)
                lines.append(f"- **{label}:** {cites}")
        if entry["own"]:
            lines.append(f"- **RESize's own choice:** {entry['own']}")
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
