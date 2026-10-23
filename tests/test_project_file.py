import json

import pytest

from resize_energy.core import profiles as prof
from resize_energy.core import project_file as pf


def sample():
    year = prof.HourlyWeather(tuple(float(i % 20) for i in range(prof.HOURS)),
                              tuple(float(i % 900) for i in range(prof.HOURS)), 2020)
    return pf.Project(
        "compare", [{"demand": {"num": "10000000"}, "box": {"on": True}},
                    {"picker": {"idx": 2, "text": "Vestas V90"}}],
        compare_techs=("pv", "hydrogen"), weather={"0": year}, note="x")


def test_roundtrip_keeps_everything():
    p = pf.loads(pf.dumps(sample()))
    assert p.tech == "compare" and p.compare_techs == ("pv", "hydrogen")
    assert p.pages[0]["demand"] == {"num": "10000000"} and p.pages[1]["picker"]["idx"] == 2
    w = p.weather["0"]
    assert w.year == 2020 and len(w.wind50_ms) == prof.HOURS
    assert w.wind50_ms[25] == pytest.approx(5.0) and w.ghi_w_m2[10] == pytest.approx(10.0)


@pytest.mark.parametrize("text,message", [
    ("not json at all", "not a RESize"),
    ("[1, 2]", "not a RESize"),
    (json.dumps({"format": "other"}), "not a RESize"),
    (json.dumps({"format": pf.FORMAT, "version": 99, "tech": "pv", "pages": []}), "newer"),
    (json.dumps({"format": pf.FORMAT, "version": 1, "tech": "solar-thermal", "pages": []}),
     "unknown technology"),
    (json.dumps({"format": pf.FORMAT, "version": 1, "tech": "pv", "pages": "x"}), "damaged"),
    (json.dumps({"format": pf.FORMAT, "version": 1, "tech": "pv", "pages": [],
                 "weather": {"0": {"year": 1, "wind50": [1], "ghi": [1]}}}), "weather"),
])
def test_bad_files_get_a_readable_message(text, message):
    with pytest.raises(pf.ProjectError, match=message):
        pf.loads(text)


def test_unknown_tech_cannot_be_saved():
    with pytest.raises(pf.ProjectError):
        pf.dumps(pf.Project("fusion"))


def test_file_name():
    assert pf.default_name("pv") == "RESize_pv.resize"
