import re
import xml.etree.ElementTree as ET

import pytest

from resize_energy.report import formula_art as fa
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.why_html import explanation_html


def _svg_of(text):
    f = fa.typeset(text)
    ET.fromstring(f.svg)                       # well-formed
    return f


@pytest.mark.parametrize("key", sorted(EXPLANATIONS))
def test_every_formula_is_drawn(key):
    f = _svg_of(EXPLANATIONS[key]["formula"])
    assert 20 < f.w < 1000 and f.h > 10
    assert "nan" not in f.svg.lower()


def test_a_fraction_is_vertical_and_a_subscript_is_smaller():
    f = _svg_of("PR = E_ac / (P_dc,kWp * H)")
    assert "<line" in f.svg                    # the fraction bar
    sizes = set(re.findall(r'font-size="([\d.]+)"', f.svg))
    assert len(sizes) == 2                     # normal and subscript size
    assert "dc,kWp" in f.svg and "E_ac" not in f.svg


def test_powers_greek_and_roots():
    f = _svg_of("z = x^2 + eta * sqrt(y)")
    assert "η" in f.svg and "·" in f.svg
    assert f.svg.count("<path") >= 1           # the radical


def test_floor_ceil_and_tall_parentheses_use_drawn_brackets():
    tall = _svg_of("N = floor(V_dc / V_oc)")
    assert "<path" in tall.svg
    flat = _svg_of("y = (a + b)")
    assert "<path" not in flat.svg and "(" in flat.svg


def test_denominator_ends_at_the_next_product_sign():
    # (a / b) * c  ->  one fraction with a and c above, b below
    f = _svg_of("y = a / b * c")
    assert f.svg.count("<line") == 1


def test_long_lines_are_wrapped():
    f = fa.typeset("y = " + " + ".join(f"term_{k}" for k in range(40)), max_width=300)
    assert f.w < 340 and f.h > 40


def test_statements_and_notes_are_stacked():
    one = fa.typeset("a = b")
    three = fa.typeset("a = b;  c = d  [kWh]")
    assert three.h > one.h * 2
    assert "kWh" in three.svg


def test_exponent_notation_and_chemicals():
    assert "10" in _svg_of("p = 2.5e-5 * z").svg
    assert _svg_of("2 H2O -> 2 H2 + O2").svg.count("font-size") > 4


def test_html_uses_a_picture_only_when_asked():
    plain = explanation_html("pv.dc_ac_ratio", "a = 1 m2")
    assert "<code>" in plain and "chart:fx_" not in plain
    pretty = explanation_html("pv.dc_ac_ratio", "H = 1500 kWh/m2 per year\nx -> y", math=True)
    names = re.findall(r'src="chart:(fx_[0-9a-f]+)"', pretty)
    assert len(names) == 1 and names[0] in fa.REGISTRY
    assert "<code>" not in pretty and "m<sup>2</sup>" in pretty and "→" in pretty
