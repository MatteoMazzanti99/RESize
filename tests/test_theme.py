import re

from resize_energy.core.pv_design import PVInputs, size_pv_system
from resize_energy.gui import theme
from resize_energy.report.html_report import build_pv_report
from resize_energy.tutor.checker import check_pv_design

C = theme.COLORS


def test_contrast_ratio_known_values():
    assert abs(theme.contrast_ratio("#000000", "#FFFFFF") - 21.0) < 1e-6
    assert abs(theme.contrast_ratio("#777777", "#777777") - 1.0) < 1e-9


def test_text_colours_are_readable_on_every_surface():
    # WCAG AA asks for 4.5:1 for normal text; the main text aims higher.
    assert theme.contrast_ratio(C["text"], C["bg"]) >= 7
    for surface in ("bg", "surface", "surface2", "sidebar", "accent_tint"):
        assert theme.contrast_ratio(C["muted"], C[surface]) >= 4.5, surface
        assert theme.contrast_ratio(C["accent"], C[surface]) >= 4.5, surface
    for status in ("warning", "error", "info"):
        assert theme.contrast_ratio(C[status], C["bg"]) >= 4.5, status
        assert theme.contrast_ratio(C[status], C["surface"]) >= 4.5, status


def test_primary_button_text_is_readable():
    assert theme.contrast_ratio(C["accent_text"], C["accent"]) >= 4.5
    assert theme.contrast_ratio(C["accent_text"], C["accent_hover"]) >= 4.5


def test_borders_are_visible_against_the_background():
    assert theme.contrast_ratio(C["border"], C["bg"]) >= 1.4


def test_all_colours_are_valid_hex():
    for name, value in C.items():
        assert re.fullmatch(r"#[0-9A-Fa-f]{6}", value), name


def test_stylesheet_is_complete_and_balanced():
    qss = theme.build_stylesheet()
    assert qss.count("{") == qss.count("}")
    assert not re.findall(r"\{[a-z_0-9]+\}", qss), "unreplaced colour placeholder"
    assert "__FONT__" not in qss
    for selector in ("QPushButton[variant=\"primary\"]", "QFrame#cardActive", "QWidget#sidebar",
                     "QPushButton#whyButton", "QLabel#headline"):
        assert selector in qss, selector
    assert C["accent"] in qss and C["bg"] in qss


def test_screen_report_matches_the_light_window_and_pdf_stays_printable():
    inp = PVInputs(annual_demand_kwh=4500, annual_irradiation_kwh_m2=1500, performance_ratio=0.8)
    design = size_pv_system(inp)
    findings = check_pv_design(inp, design)
    dark = build_pv_report(inp, design, findings, theme="screen")
    light = build_pv_report(inp, design, findings, theme="light")
    assert C["accent"].upper() in dark.upper() and C["surface2"].upper() in dark.upper()
    assert "background: #eee" in light and C["surface2"].upper() not in light.upper()
    # same content in both looks; only the style differs
    assert "With your numbers" in dark and "With your numbers" in light
    assert "Design checks" in dark and "Design checks" in light
    # unknown theme falls back to the printable one
    assert "background: #eee" in build_pv_report(inp, design, findings, theme="nope")
