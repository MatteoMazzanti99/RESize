"""Tutor texts, reports, charts and pictures of the hydropower and geothermal modules."""

import pytest

from resize_energy.core.geothermal_design import GeothermalInputs, size_geothermal_plant
from resize_energy.core.hydro_design import HydroInputs, size_hydro_plant
from resize_energy.report.charts import geothermal_charts, hydro_charts
from resize_energy.report.flow_pictures import geothermal_picture, hydro_picture
from resize_energy.report.html_report import build_geothermal_report, build_hydro_report
from resize_energy.tutor.checker_geothermal import check_geothermal_design
from resize_energy.tutor.checker_hydro import check_hydro_design
from resize_energy.tutor.context_geothermal import build_geothermal_context
from resize_energy.tutor.context_hydro import build_hydro_context
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.explanations_geothermal import topics_for
from resize_energy.tutor.explanations_hydro import HYDRO_TOPIC_ORDER
from resize_energy.tutor.worked_geothermal import geothermal_worked_example
from resize_energy.tutor.worked_hydro import hydro_worked_example


def test_hydro_pieces():
    inp = HydroInputs()
    d = size_hydro_plant(inp)
    findings = check_hydro_design(inp, d)
    assert all(f.explanation_key in EXPLANATIONS for f in findings if f.explanation_key)
    for key in HYDRO_TOPIC_ORDER:
        text = hydro_worked_example(key, inp, d)
        assert text and any(ch.isdigit() for ch in text), key
    assert hydro_worked_example("nope", inp, d) is None
    assert "RESULTS" in build_hydro_context(inp, d, findings)
    for theme in ("light", "screen"):
        html = build_hydro_report(inp, d, findings, theme=theme)
        assert "Method and formulas" in html and "Design checks" in html
    nodes, flows = hydro_picture(inp, d)
    assert nodes and flows
    assert hydro_charts(inp, d)


@pytest.mark.parametrize("pathway, temp", [("heat", 90.0), ("power", 150.0), ("power", 210.0)])
def test_geothermal_pieces(pathway, temp):
    inp = GeothermalInputs(pathway=pathway, reservoir_temp_c=temp)
    d = size_geothermal_plant(inp)
    findings = check_geothermal_design(inp, d)
    assert all(f.explanation_key in EXPLANATIONS for f in findings if f.explanation_key)
    for key in topics_for(pathway):
        text = geothermal_worked_example(key, inp, d)
        assert text and any(ch.isdigit() for ch in text), (pathway, key)
    assert "RESULTS" in build_geothermal_context(inp, d, findings)
    for theme in ("light", "screen"):
        html = build_geothermal_report(inp, d, findings, theme=theme)
        assert "Method and formulas" in html and "Design checks" in html
    nodes, flows = geothermal_picture(inp, d)
    assert nodes and flows
    assert geothermal_charts(inp, d)
