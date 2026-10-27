"""Checks the bibliography against Crossref (needs internet; run it on your own computer).

For every reference with a DOI it fetches the record and compares the title, year and journal.
References without a DOI are listed so you can check them by hand.

    python tools/check_references.py

Run it from the project folder, in a terminal (PowerShell, cmd or bash), with the same Python
where RESize is installed. Double-clicking the file closes the window at once.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))   # no PYTHONPATH needed

from resize_energy.tutor.bibliography import REFS


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def fetch(doi: str) -> dict | None:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    request = urllib.request.Request(url, headers={"User-Agent": "RESize-reference-check"})
    try:
        with urllib.request.urlopen(request, timeout=20) as reply:
            return json.load(reply)["message"]
    except (urllib.error.URLError, OSError, KeyError, ValueError):
        return None


def main() -> int:
    problems = 0
    for key, ref in REFS.items():
        if not ref.doi:
            if ref.kind == "article":
                print(f"?  {key}: no DOI, check by hand: {ref.short}, {ref.container} {ref.detail}")
            continue
        record = fetch(ref.doi)
        if record is None:
            print(f"!! {key}: DOI {ref.doi} not found or Crossref unreachable")
            problems += 1
            continue
        title = " ".join(record.get("title", [""]))
        year = str((record.get("issued", {}).get("date-parts") or [[""]])[0][0])
        ok_title = len(words(ref.title) & words(title)) >= 0.7 * len(words(ref.title))
        ok_year = not ref.year or year == ref.year
        if ok_title and ok_year:
            print(f"ok {key}")
        else:
            print(f"!! {key}: ours '{ref.title}' ({ref.year}); Crossref '{title}' ({year})")
            problems += 1
    print("\nAll DOI records match." if not problems else f"\n{problems} problem(s).")
    return 1 if problems else 0


class _Tee:
    """Print on the screen and keep a copy for the report file."""

    def __init__(self, stream, lines: list[str]) -> None:
        self.stream, self.lines = stream, lines

    def write(self, text: str) -> int:
        self.lines.append(text)
        return self.stream.write(text)

    def flush(self) -> None:
        self.stream.flush()


if __name__ == "__main__":
    captured: list[str] = []
    real = sys.stdout
    sys.stdout = _Tee(real, captured)
    try:
        code = main()
    finally:
        sys.stdout = real
    report = Path(__file__).resolve().parent.parent / "reference_check.txt"
    try:
        report.write_text("".join(captured), encoding="utf-8")
        print(f"\nThe same list is saved in {report}")
    except OSError:
        pass
    if sys.stdin is not None and sys.stdin.isatty() and "--no-pause" not in sys.argv:
        input("\nPress Enter to close this window... ")   # a double-click would close it at once
    sys.exit(code)
