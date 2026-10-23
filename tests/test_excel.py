"""The Excel export: formulas recalculated by LibreOffice must agree with RESize."""

import shutil
import subprocess
from dataclasses import replace

import pytest

openpyxl = pytest.importorskip("openpyxl")

from resize_energy.core.plant_economics import EconomicInputs  # noqa: E402
from resize_energy.core.pv_design import PVInputs, size_pv_system  # noqa: E402
from resize_energy.core.turbine_library import load_library  # noqa: E402
from resize_energy.core.wind_design import WindInputs, size_wind_plant  # noqa: E402
from resize_energy.report.excel import (  # noqa: E402
    build_pv_workbook,
    build_wind_workbook,
    save_workbook,
)

ECON = EconomicInputs()
SOFFICE = shutil.which("soffice")


def _recalculated(wb, tmp_path):
    src = tmp_path / "in.xlsx"
    save_workbook(wb, src)
    out = tmp_path / "out"
    subprocess.run([SOFFICE, "--headless", "--convert-to", "xlsx", "--outdir", str(out),
                    str(src)], check=True, capture_output=True, timeout=180)
    return openpyxl.load_workbook(out / "in.xlsx", data_only=True)


def _all_ok(wb):
    rows = list(wb["Check"].iter_rows(min_row=2, max_col=4, values_only=True))
    checked = [r for r in rows if r[3] in ("OK", "DIFFERENT")]
    assert len(checked) > 15
    assert [r[0] for r in checked if r[3] != "OK"] == []


def test_pv_workbook_has_formulas_and_named_inputs():
    inp = PVInputs(9000, 1500, economics=ECON)
    wb = build_pv_workbook(inp, size_pv_system(inp))
    assert {"About", "Inputs", "Calculation", "Layout", "Economics", "Cash flow", "Check"} <= set(
        wb.sheetnames)
    assert "target_kwp" in wb.defined_names
    formulas = [c.value for row in wb["Calculation"].iter_rows() for c in row
                if isinstance(c.value, str) and c.value.startswith("=")]
    assert len(formulas) > 15 and "=coverage*demand_kwh/(irradiation*pr_effective)" in formulas


def test_pv_without_costs_has_no_economics_sheet():
    inp = PVInputs(9000, 1500)
    wb = build_pv_workbook(inp, size_pv_system(inp))
    assert "Economics" not in wb.sheetnames


@pytest.mark.skipif(SOFFICE is None, reason="LibreOffice is not installed")
@pytest.mark.parametrize("demand,shading", [(9000, 0.0), (25000, 0.1), (3000, 0.0)])
def test_pv_excel_matches_the_app(tmp_path, demand, shading):
    inp = PVInputs(demand, 1500, shading_loss=shading, economics=ECON)
    _all_ok(_recalculated(build_pv_workbook(inp, size_pv_system(inp)), tmp_path))


@pytest.mark.skipif(SOFFICE is None, reason="LibreOffice is not installed")
def test_wind_excel_matches_the_app_generic_curve(tmp_path):
    inp = WindInputs(900000, 6.5, economics=ECON)
    _all_ok(_recalculated(build_wind_workbook(inp, size_wind_plant(inp)), tmp_path))


@pytest.mark.skipif(SOFFICE is None, reason="LibreOffice is not installed")
def test_wind_excel_matches_the_app_library_curve_and_wake(tmp_path):
    turbine = next(t for t in load_library() if t.group == "onshore").to_spec()
    inp = WindInputs(5_000_000, 7.0, turbine=turbine, wake_model=True, economics=ECON)
    inp = replace(inp)
    _all_ok(_recalculated(build_wind_workbook(inp, size_wind_plant(inp)), tmp_path))
