"""Typeset the plain-text formulas of the 'Why?' topics as small pictures (SVG).

The formulas are written as text, for example ``PR = E_ac / (P_dc,kWp * H)``. This module reads
that notation and draws it the way a textbook would: subscripts (``E_ac``) and superscripts
(``x^2``), fractions with the numerator above the denominator, a centred dot for ``*``, Greek
letters for ``eta``, ``beta`` and so on, large parentheses around tall content, floor/ceiling
brackets and square roots. The text is set in Poppins like the rest of the app.

Reading the notation:

* ``a / b`` divides: the factors after a ``/`` go below the bar until the next ``*``;
  factors that follow without an operator ("sum of the shape") stay together.
* ``X_abc,def`` is X with the subscript "abc,def"; ``x^n`` and ``x^(a/b)`` are powers.
* Text in ``[square brackets]`` and statements without any maths are shown as grey notes.
* Statements are separated by ``;`` or by two or more spaces; each gets its own line, and a
  line that is too wide is wrapped after an operator.

Only the standard library is used (the widths of the letters come from the font file), so the
module works without Qt; the GUI turns the SVG into an image.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html import escape

from resize_energy.report._poppins_widths import ADVANCE

INK = "#0F1B2D"
MUTED = "#556377"
SIZE = 15.0                 # font size of the main line, in pixels
MAX_WIDTH = 500.0           # wider lines are wrapped after an operator
PAD = 3.0

GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "Delta": "Δ", "epsilon": "ε",
         "eta": "η", "theta": "θ", "lambda": "λ", "mu": "μ", "rho": "ρ", "sigma": "σ",
         "tau": "τ", "phi": "φ", "omega": "ω"}
CHEMICALS = {"CO2", "CH4", "H2", "O2", "N2", "N2O", "NH3", "H2O", "NOx", "SO2"}
UNIT_SUP = {"m2": ("m", "2"), "m3": ("m", "3"), "km2": ("km", "2"), "Nm3": ("Nm", "3")}
ADDITIVE = {"+", "-", "=", "<", ">", "≤", "≥", "→", ",", ":"}

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9&']*(?:_[A-Za-z0-9&]+(?:[,\-][A-Za-z0-9&]+)*)?"
                   r"(?:-[A-Za-z]+)*")
_NUM = re.compile(r"\d+(?:[.,]\d+)*(?:e-?\d+)?")


# ---------------------------------------------------------------- boxes


@dataclass
class Box:
    """A piece of typeset maths: its size and the SVG that draws it (baseline at y = 0)."""

    w: float
    asc: float
    desc: float
    svg: str

    @property
    def h(self) -> float:
        return self.asc + self.desc


def text_width(s: str, size: float, bold: bool = False) -> float:
    total = sum(ADVANCE.get(c, 640) for c in s)
    return total / 1000.0 * size * (1.05 if bold else 1.0)


def _at(box: Box, dx: float, dy: float = 0.0) -> str:
    if dx == 0 and dy == 0:
        return box.svg
    return f'<g transform="translate({dx:.2f},{dy:.2f})">{box.svg}</g>'


def T(s: str, size: float, fill: str = INK) -> Box:
    """A run of text."""
    svg = (f'<text x="0" y="0" font-size="{size:.2f}" fill="{fill}">{escape(s)}</text>')
    return Box(text_width(s, size), 0.72 * size, 0.2 * size, svg)


def GAP(w: float) -> Box:
    return Box(w, 0.0, 0.0, "")


def H(parts: list[Box]) -> Box:
    """Boxes side by side on one baseline."""
    x = 0.0
    out = []
    asc = desc = 0.0
    for b in parts:
        out.append(_at(b, x))
        x += b.w
        asc, desc = max(asc, b.asc), max(desc, b.desc)
    return Box(x, asc, desc, "".join(out))


def script(base: Box, sub: Box | None, sup: Box | None, size: float) -> Box:
    """Base with a subscript and/or a superscript."""
    parts = [_at(base, 0)]
    w = base.w
    asc, desc = base.asc, base.desc
    extra = 0.04 * size
    if sup is not None:
        dy = -(0.36 * size + 0.0)
        parts.append(_at(sup, base.w + extra, dy))
        w = max(w, base.w + extra + sup.w)
        asc = max(asc, sup.asc - dy)
    if sub is not None:
        dy = 0.2 * size
        parts.append(_at(sub, base.w + extra, dy))
        w = max(w, base.w + extra + sub.w)
        desc = max(desc, sub.desc + dy)
    return Box(w + extra, asc, desc, "".join(parts))


def frac(num: Box, den: Box, size: float) -> Box:
    pad = 0.2 * size
    axis = 0.3 * size
    bar = max(1.0, 0.075 * size)
    w = max(num.w, den.w) + 0.35 * size
    ny = -axis - pad - num.desc
    dy = -axis + pad + den.asc + bar
    svg = (f'<line x1="0" y1="{-axis:.2f}" x2="{w:.2f}" y2="{-axis:.2f}" stroke="{INK}" '
           f'stroke-width="{bar:.2f}"/>'
           + _at(num, (w - num.w) / 2, ny) + _at(den, (w - den.w) / 2, dy))
    return Box(w, axis + pad + num.h + 0.0, max(0.0, den.h + pad + bar - axis), svg)


def _stroke(d: str, size: float) -> str:
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{max(1.1, 0.085 * size):.2f}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def fence(kind: str, content: Box, size: float) -> Box:
    """Brackets that grow with the content: ``(``, ``floor``, ``ceil``; ``sqrt`` for a root."""
    top = -(max(content.asc, 0.72 * size) + 0.06 * size)
    bot = max(content.desc, 0.2 * size) + 0.06 * size
    mid = (top + bot) / 2
    tall = content.h > 1.2 * size
    wp = 0.3 * size if tall else 0.33 * size
    if kind == "(":
        if not tall:
            left, right = T("(", size), T(")", size)
            return H([left, content, right])
        left = _stroke(f"M{wp * 0.85:.2f},{top:.2f} Q{-wp * 0.15:.2f},{mid:.2f} {wp * 0.85:.2f},{bot:.2f}", size)
        right = _stroke(f"M{0.15 * wp:.2f},{top:.2f} Q{wp * 1.15:.2f},{mid:.2f} {0.15 * wp:.2f},{bot:.2f}", size)
    elif kind == "floor":
        left = _stroke(f"M{0.2 * wp:.2f},{top:.2f} V{bot:.2f} H{wp * 0.9:.2f}", size)
        right = _stroke(f"M{0.8 * wp:.2f},{top:.2f} V{bot:.2f} H{0.1 * wp:.2f}", size)
    elif kind == "ceil":
        left = _stroke(f"M{0.2 * wp:.2f},{bot:.2f} V{top:.2f} H{wp * 0.9:.2f}", size)
        right = _stroke(f"M{0.8 * wp:.2f},{bot:.2f} V{top:.2f} H{0.1 * wp:.2f}", size)
    else:                                             # square root
        wr = 0.62 * size
        total = wr + content.w + 0.2 * size
        svg = (_stroke(f"M0,{mid + 0.1 * size:.2f} L{0.14 * size:.2f},{mid + 0.02 * size:.2f} "
                       f"L{0.3 * size:.2f},{bot:.2f} L{0.55 * size:.2f},{top:.2f} H{total:.2f}", size)
               + _at(content, wr + 0.05 * size))
        return Box(total, -top, bot, svg)
    inner = 0.08 * size
    svg = (left + _at(content, wp + inner) + f'<g transform="translate({wp + inner * 2 + content.w:.2f},0)">{right}</g>')
    return Box(content.w + 2 * wp + 2 * inner, -top, bot, svg)


def arrow(size: float) -> Box:
    w = 1.15 * size
    y = -0.3 * size
    d = (f"M0,{y:.2f} H{w:.2f} M{w - 0.28 * size:.2f},{y - 0.22 * size:.2f} L{w:.2f},{y:.2f} "
         f"L{w - 0.28 * size:.2f},{y + 0.22 * size:.2f}")
    return Box(w, 0.55 * size, 0.0, _stroke(d, size))


# ---------------------------------------------------------------- reading the notation


@dataclass
class Tok:
    kind: str     # num word op lp rp note
    val: str
    sp: bool      # whitespace before


def tokenize(s: str) -> list[Tok]:
    toks: list[Tok] = []
    i, sp = 0, False
    while i < len(s):
        c = s[i]
        if c.isspace():
            sp = True
            i += 1
            continue
        if c == "[":
            j = s.find("]", i)
            j = len(s) - 1 if j < 0 else j
            toks.append(Tok("note", s[i:j + 1], sp))
            i, sp = j + 1, False
            continue
        if s.startswith("->", i):
            toks.append(Tok("op", "→", sp))
            i, sp = i + 2, False
            continue
        if s.startswith("<=", i) or s.startswith(">=", i):
            toks.append(Tok("op", "≤" if c == "<" else "≥", sp))
            i, sp = i + 2, False
            continue
        m = _NUM.match(s, i) if c.isdigit() else None
        if m is None and c.isalpha():
            m = _WORD.match(s, i)
            if m:
                toks.append(Tok("word", m.group(0), sp))
                i, sp = m.end(), False
                continue
        if m is not None:
            toks.append(Tok("num", m.group(0), sp))
            i, sp = m.end(), False
            continue
        kind = "lp" if c == "(" else "rp" if c == ")" else "op"
        toks.append(Tok(kind, c, sp))
        i, sp = i + 1, False
    return toks


class Parser:
    """Turns tokens into a small tree of tuples (see ``Render``)."""

    def __init__(self, toks: list[Tok]) -> None:
        self.t = toks
        self.i = 0

    def peek(self) -> Tok | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def row(self) -> list:
        """terms and operators: [("term", node), ("op", "="), ...]"""
        items: list = []
        while True:
            tk = self.peek()
            if tk is None or tk.kind == "rp":
                break
            if tk.kind == "op" and tk.val in ADDITIVE and items and items[-1][0] == "term":
                items.append(("op", tk.val))
                self.i += 1
                continue
            before = self.i
            term = self.term()
            if term is not None:
                items.append(("term", term))
            if self.i == before:           # no progress: skip the token
                self.i += 1
        return items

    def term(self):
        factors: list[tuple[str, tuple, bool]] = []     # join, node, in denominator
        den = False
        join = ""
        while True:
            tk = self.peek()
            if tk is None or tk.kind == "rp":
                break
            if tk.kind == "op" and tk.val == "*":
                self.i += 1
                den, join = False, "·"
                continue
            if tk.kind == "op" and tk.val == "/":
                self.i += 1
                den, join = True, ""
                continue
            if tk.kind == "op" and tk.val == "-" and not factors and join == "":
                self.i += 1
                join = "−"
                continue
            if tk.kind == "op" and tk.val in ADDITIVE:
                break
            node = self.power()
            if node is None:
                break
            factors.append((join, node, den))
            join = " "
        if not factors:
            return None
        return ("term", factors)

    def power(self):
        atom = self.atom()
        if atom is None:
            return None
        tk = self.peek()
        if tk is not None and tk.kind == "op" and tk.val == "^":
            self.i += 1
            neg = False
            nxt = self.peek()
            if nxt is not None and nxt.kind == "op" and nxt.val == "-":
                neg = True
                self.i += 1
            exp = self.atom()
            if exp is None:
                return atom
            return ("sup", atom, ("neg", exp) if neg else exp)
        return atom

    def atom(self):
        tk = self.peek()
        if tk is None:
            return None
        if tk.kind == "num":
            self.i += 1
            return ("num", tk.val)
        if tk.kind == "note":
            self.i += 1
            return ("note", tk.val)
        if tk.kind == "word":
            self.i += 1
            nxt = self.peek()
            if nxt is not None and nxt.kind == "lp" and not nxt.sp:
                return ("call", tk.val, self.group())
            return ("word", tk.val)
        if tk.kind == "lp":
            return self.group()
        if tk.kind == "op" and tk.val not in ("^", "*", "/") and tk.val not in ADDITIVE:
            self.i += 1
            return ("sym", tk.val)
        return None

    def group(self):
        self.i += 1                         # the opening parenthesis
        inner = self.row()
        tk = self.peek()
        if tk is not None and tk.kind == "rp":
            self.i += 1
        return ("group", inner)


# ---------------------------------------------------------------- drawing the tree


class Render:
    def __init__(self, fill: str = INK) -> None:
        self.fill = fill

    def text(self, s: str, size: float) -> Box:
        return T(s, size, self.fill)

    def word(self, name: str, size: float) -> Box:
        base, _, sub = name.partition("_")
        if base in GREEK:
            b = self.text(GREEK[base], size)
        elif base in CHEMICALS and not sub:
            parts = []
            for chunk in re.findall(r"[A-Za-z]+|\d+", base):
                small = chunk.isdigit()
                box = self.text(chunk, size * 0.72 if small else size)
                parts.append(script(GAP(0), box, None, size) if small else box)
            return H(parts)
        elif base in UNIT_SUP and not sub:
            head, tail = UNIT_SUP[base]
            return script(self.text(head, size), None, self.text(tail, size * 0.72), size)
        else:
            b = self.text(base, size)
        if sub:
            return script(b, self.text(sub, size * 0.72), None, size)
        return b

    def node(self, n: tuple, size: float, unwrap: bool = False) -> Box:
        kind = n[0]
        if kind == "num":
            m = re.fullmatch(r"([\d.,]+)e(-?\d+)", n[1])
            if m:                                        # 2.5e-5 is drawn as 2.5 · 10^-5
                ten = script(self.text("10", size), None, self.text(m.group(2).replace("-", "−"), size * 0.72), size)
                return H([self.text(m.group(1), size), GAP(0.18 * size), self.text("·", size), GAP(0.18 * size), ten])
            return self.text(n[1], size)
        if kind == "word":
            return self.word(n[1], size)
        if kind == "sym":
            return self.text(n[1], size)
        if kind == "note":
            return T(n[1].replace(" * ", " · "), size * 0.86, MUTED)
        if kind == "neg":
            return H([self.text("−", size), self.node(n[1], size)])
        if kind == "sup":
            small = max(size * 0.72, 8.0)
            exp = n[2]
            return script(self.node(n[1], size), None, self.node(exp, small, unwrap=True), size)
        if kind == "group":
            content = self.row(n[1], size)
            return content if unwrap else fence("(", content, size)
        if kind == "call":
            name, arg = n[1], n[2]
            inner = self.row(arg[1], size)
            if name in ("floor", "ceil"):
                return fence(name, inner, size)
            if name == "sqrt":
                return fence("sqrt", inner, size)
            return H([self.word(name, size), fence("(", inner, size)])
        raise ValueError(kind)

    def seq(self, factors: list, size: float) -> Box:
        parts: list[Box] = []
        for k, (join, node, _den) in enumerate(factors):
            if k == 0 and join == "−":
                parts.append(self.text("−", size))
            elif k > 0:
                if join == "·":
                    parts += [GAP(0.18 * size), self.text("·", size), GAP(0.18 * size)]
                else:
                    parts.append(GAP(0.22 * size))
            parts.append(self.node(node, size))
        return H(parts)

    def term(self, t: tuple, size: float) -> Box:
        factors = t[1]
        top = [(j, n, d) for j, n, d in factors if not d]
        bottom = [(j, n, d) for j, n, d in factors if d]
        if not bottom:
            return self.seq(top, size)
        if not top:
            num = self.text("1", size)
        else:
            top = [("" if k == 0 and j != "−" else j, n, d) for k, (j, n, d) in enumerate(top)]
            num = self.unwrapped(top, size)
        bottom = [("" if k == 0 else j, n, d) for k, (j, n, d) in enumerate(bottom)]
        return frac(num, self.unwrapped(bottom, size), size)

    def unwrapped(self, factors: list, size: float) -> Box:
        """A numerator or denominator; a lone parenthesised group loses its parentheses."""
        if len(factors) == 1 and factors[0][1][0] == "group":
            return self.row(factors[0][1][1], size)
        return self.seq(factors, size)

    def op(self, o: str, size: float) -> Box:
        if o == "→":
            return H([GAP(0.3 * size), arrow(size), GAP(0.3 * size)])
        if o in (",", ":"):
            return H([self.text(o, size), GAP(0.3 * size)])
        sign = "−" if o == "-" else o
        return H([GAP(0.3 * size), self.text(sign, size), GAP(0.3 * size)])

    def row(self, items: list, size: float) -> Box:
        parts = []
        for kind, value in items:
            parts.append(self.term(value, size) if kind == "term" else self.op(value, size))
        return H(parts)

    def flow(self, items: list, size: float) -> list[tuple[Box, bool]]:
        """The top-level pieces of a line with 'may break before' flags, for wrapping."""
        out: list[tuple[Box, bool]] = []
        for kind, value in items:
            if kind == "op":
                out.append((self.op(value, size), value in ("=", "→", "+", "-")))
                continue
            factors = value[1]
            if any(d for _j, _n, d in factors):
                out.append((self.term(value, size), False))
                continue
            for k, (join, node, _d) in enumerate(factors):
                pieces = []
                if k == 0 and join == "−":
                    pieces.append(self.text("−", size))
                elif k > 0:
                    pieces += ([GAP(0.18 * size), self.text("·", size), GAP(0.18 * size)]
                               if join == "·" else [GAP(0.22 * size)])
                pieces.append(self.node(node, size))
                out.append((H(pieces), k > 0 and join == " "))
        return out


def wrap(pieces: list[tuple[Box, bool]], max_width: float, indent: float) -> list[Box]:
    """Break a line into lines no wider than ``max_width`` (before the allowed pieces)."""
    lines: list[list[Box]] = [[]]
    width = 0.0
    for k, (box, can_break) in enumerate(pieces):
        # an operator travels with the term that follows it
        needed = box.w + (pieces[k + 1][0].w if can_break and k + 1 < len(pieces) else 0.0)
        if lines[-1] and can_break and width + needed > max_width:
            lines.append([GAP(indent)])
            width = indent
        lines[-1].append(box)
        width += box.w
    return [H(line) for line in lines]


# ---------------------------------------------------------------- statements and pictures


def _clean(statement: str) -> str:
    return statement.strip().strip(",.").strip()


def split_statements(text: str) -> list[str]:
    text = re.sub(r"\s*->\s*", " -> ", text)
    parts = re.split(r";\s*|\n|\s{2,}", text)
    return [p for p in (_clean(x) for x in parts) if p]


def _is_note(s: str) -> bool:
    if s.startswith("[") or (s.startswith("(") and s.endswith(")") and ":" in s):
        return True
    return "=" not in s and "->" not in s


@dataclass
class Formula:
    key: str
    svg: str
    w: float
    h: float


REGISTRY: dict[str, Formula] = {}


def formula_key(text: str) -> str:
    return "fx_" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def typeset(text: str, size: float = SIZE, max_width: float = MAX_WIDTH) -> Formula:
    """The picture of a formula (several statements are stacked)."""
    lines: list[Box] = []
    gaps: list[float] = []
    for statement in split_statements(text):
        if _is_note(statement):
            lines.append(T(statement.replace(" * ", " · "), size * 0.86, MUTED))
            gaps.append(0.55 * size)
            continue
        render = Render()
        items = Parser(tokenize(statement)).row()
        wrapped = wrap(render.flow(items, size), max_width, 1.2 * size)
        for k, box in enumerate(wrapped):
            lines.append(box)
            gaps.append(0.45 * size if k < len(wrapped) - 1 else 0.7 * size)
    if not lines:
        lines, gaps = [T(text, size)], [0.0]
    width = max(b.w for b in lines) + 2 * PAD
    y = PAD
    parts: list[str] = []
    for box, gap in zip(lines, gaps, strict=True):
        y += box.asc
        parts.append(f'<g transform="translate({PAD:.2f},{y:.2f})">{box.svg}</g>')
        y += box.desc + gap
    height = y - gaps[-1] + PAD
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.1f}" height="{height:.1f}" '
           f'viewBox="0 0 {width:.1f} {height:.1f}" font-family="Poppins, \'Segoe UI\', Arial, '
           f'sans-serif">{"".join(parts)}</svg>')
    return Formula(formula_key(text), svg, round(width), round(height))


def register(text: str) -> Formula:
    """Typeset a formula and remember it, so the window can answer ``chart:fx_...``."""
    f = typeset(text)
    REGISTRY[f.key] = f
    return f


def worked_html(worked: str) -> str:
    """The user's numbers as HTML paragraphs: Poppins text with exponents and subscripts."""
    lines = []
    for line in worked.split("\n"):
        h = escape(line).replace("-&gt;", "→")
        h = re.sub(r"\b(m|km)([23])\b", r"\1<sup>\2</sup>", h)
        h = re.sub(r"\b(CO|CH|NH|N)(\d)\b", r"\1<sub>\2</sub>", h)
        h = re.sub(r"\bH2\b", "H<sub>2</sub>", h)
        h = h.replace(" x ", " × ")
        lines.append(h)
    return "<br>".join(lines)


__all__ = ["Formula", "REGISTRY", "register", "typeset", "worked_html"]
