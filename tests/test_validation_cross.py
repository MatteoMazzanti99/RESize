import importlib.util
from pathlib import Path


def test_offline_cross_checks_all_match(tmp_path):
    path = Path(__file__).resolve().parents[1] / "validation" / "validate_cross.py"
    spec = importlib.util.spec_from_file_location("validate_cross", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sections = [module.section_wind(True), module.section_biogas(), module.section_hydrogen(),
                module.section_battery()]
    assert all(s.hard_ok for s in sections)
    assert len(sections[0].rows) >= 3 and "match" in sections[2].rows[0]
