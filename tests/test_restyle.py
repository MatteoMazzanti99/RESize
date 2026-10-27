"""Pure parts of the restyle: key-number formatting and the colour themes."""

from resize_energy.gui import theme
from resize_energy.gui.kpi_format import ease_out, format_value


def test_ease_out_runs_from_zero_to_one():
    assert ease_out(-1) == 0.0 and ease_out(2) == 1.0
    assert 0.0 < ease_out(0.3) < 1.0
    assert ease_out(0.5) > 0.5


def test_format_value_never_shows_negative_zero():
    assert format_value(12345.6, 0) == "12,346"
    assert format_value(0.056, 3) == "0.056"
    assert format_value(-0.0001, 2) == "0.00"


def _luminance(hex_color: str) -> float:
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_both_themes_are_readable():
    try:
        for name in theme.THEMES:
            theme.use_theme(name)
            c = theme.COLORS
            assert _contrast(c["text"], c["bg"]) >= 7
            assert _contrast(c["muted"], c["surface"]) >= 4.5
            assert _contrast(c["accent_text"], c["accent"]) >= 4.5
    finally:
        theme.use_theme("light")


def test_pv_preview_has_headline_months_and_checks():
    from resize_energy.core.pv_design import InverterSpec, ModuleSpec, PVInputs, size_pv_system
    from resize_energy.gui.preview_data import design_preview
    from resize_energy.tutor.checker import check_pv_design

    module = ModuleSpec(name="m", p_stc_w=550, voc_v=49.5, vmp_v=41.5, isc_a=14.0, imp_a=13.2,
                        temp_coeff_voc_pct_per_c=-0.27, temp_coeff_vmp_pct_per_c=-0.34,
                        area_m2=2.6)
    inverter = InverterSpec(name="i", p_ac_kw=50, vdc_max_v=1000, mppt_vmin_v=200,
                            mppt_vmax_v=800, imax_per_mppt_a=30, n_mppt=2)
    inputs = PVInputs(annual_demand_kwh=60000, annual_irradiation_kwh_m2=1500, coverage=1.0,
                      performance_ratio=0.8, t_min_c=-10, t_cell_max_c=70, module=module,
                      inverter=inverter, latitude_deg=45.0)
    design = size_pv_system(inputs)
    preview = design_preview(design, check_pv_design(inputs, design))
    assert preview.unit in ("kWh", "MWh", "GWh") and preview.value
    assert preview.notes and all(kind in ("ok", "warning", "error") for kind, _ in preview.notes)
    assert len(preview.bars) in (0, 12)


def test_every_technology_has_a_preview_with_default_inputs():
    import importlib

    from resize_energy.gui.preview_data import design_preview

    cases = [
        ("biomass_design", "BiomassInputs", "size_biomass_plant", "checker_biomass",
         "check_biomass_design"),
        ("hydro_design", "HydroInputs", "size_hydro_plant", "checker_hydro",
         "check_hydro_design"),
        ("geothermal_design", "GeothermalInputs", "size_geothermal_plant",
         "checker_geothermal", "check_geothermal_design"),
        ("bhe_design", "BheInputs", "size_bhe_field", "checker_bhe", "check_bhe_design"),
    ]
    for core, inputs_name, size_name, checker, check_name in cases:
        module = importlib.import_module(f"resize_energy.core.{core}")
        inputs = getattr(module, inputs_name)()
        design = getattr(module, size_name)(inputs)
        check = getattr(importlib.import_module(f"resize_energy.tutor.{checker}"), check_name)
        preview = design_preview(design, check(inputs, design))
        assert preview.value and preview.label and preview.notes, core
