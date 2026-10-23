import xml.etree.ElementTree as ET

import pytest

from resize_energy.report.step_art import ARTS, H, W, step_svg


@pytest.mark.parametrize("key", sorted(ARTS))
@pytest.mark.parametrize("phase", [0.0, 0.3, 0.99])
def test_every_illustration_is_valid_svg(key, phase):
    svg = step_svg(key, phase)
    root = ET.fromstring(svg)
    assert (root.get("width"), root.get("height")) == (str(W), str(H))
    assert "nan" not in svg.lower()


@pytest.mark.parametrize("key", sorted(ARTS))
def test_they_move(key):
    assert step_svg(key, 0.1) != step_svg(key, 0.6)


def test_phase_wraps():
    assert step_svg("wind", 0.25) == step_svg("wind", 1.25)
