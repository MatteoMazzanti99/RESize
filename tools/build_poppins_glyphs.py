"""Writes ``report/_poppins_widths.py``: advance widths and outlines of the glyphs the formulas use.

Latin letters, digits and signs come from Poppins (SIL OFL); Poppins has no Greek, so those
come from DejaVu Sans (free licence), scaled to the same x-height. The formulas are drawn as
outlines, so their spacing no longer depends on which fonts the computer has.

    python tools/build_poppins_glyphs.py [path/to/DejaVuSans.ttf]
"""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1] / "src" / "resize_energy"
CHARS = [chr(c) for c in range(32, 127)] + list("·×…−≤≥°")
GREEK = list("ΔαβγδεηθλμρστφωΣ")


def outline(font: TTFont, ch: str, k: float) -> tuple[int, str]:
    name = font.getBestCmap()[ord(ch)]
    glyphs = font.getGlyphSet()
    scale = 1000.0 / font["head"].unitsPerEm * k
    pen = SVGPathPen(glyphs, ntos=lambda v: str(round(v)))
    glyphs[name].draw(TransformPen(pen, (scale, 0, 0, scale, 0, 0)))
    return round(glyphs[name].width * scale), pen.getCommands()


def main() -> None:
    poppins = TTFont(ROOT / "data" / "fonts" / "Poppins-Regular.ttf")
    dejavu = TTFont(sys.argv[1] if len(sys.argv) > 1 else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

    def xh(f: TTFont) -> float:
        pen = BoundsPen(f.getGlyphSet())
        f.getGlyphSet()[f.getBestCmap()[ord("x")]].draw(pen)
        return pen.bounds[3] / f["head"].unitsPerEm

    k = xh(poppins) / xh(dejavu)
    table = {ch: outline(poppins, ch, 1.0) for ch in CHARS if ord(ch) in poppins.getBestCmap()}
    table.update({ch: outline(dejavu, ch, k) for ch in GREEK})
    table["−"] = (table["+"][0], "M597 327H87V404H597Z")   # a minus as long as the bar of the plus
    lines = ['"""Advance widths and outlines (units per 1000 em, y up) of the formula glyphs.',
             "",
             "Made by tools/build_poppins_glyphs.py: Poppins Regular (SIL OFL) plus Greek letters",
             'from DejaVu Sans, scaled to Poppins\' x-height."""', "",
             "ADVANCE: dict[str, int] = {"]
    lines += [f"    {ch!r}: {w}," for ch, (w, _d) in table.items()]
    lines += ["}", "", "PATHS: dict[str, str] = {"]
    lines += [f"    {ch!r}: {d!r}," for ch, (_w, d) in table.items() if d]
    lines += ["}", ""]
    (ROOT / "report" / "_poppins_widths.py").write_text("\n".join(lines), encoding="utf-8")
    print(len(table), "glyphs")


if __name__ == "__main__":
    main()
