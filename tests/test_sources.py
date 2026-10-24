"""Every topic has its sources, and every source is a complete reference."""

import re

from resize_energy.tutor.bibliography import REFS, full_citation
from resize_energy.tutor.explanations import EXPLANATIONS
from resize_energy.tutor.sources import SOURCES, cited_keys, references_html, sources_html


def test_every_topic_has_a_sources_entry():
    assert set(EXPLANATIONS) == set(SOURCES)


def test_every_cited_reference_exists():
    for topic, entry in SOURCES.items():
        for key, _note in entry["formula"] + entry["values"]:
            assert key in REFS, (topic, key)


def test_every_topic_says_where_it_comes_from():
    for topic, entry in SOURCES.items():
        assert entry["formula"] or entry["own"], f"{topic}: no source for the formula"


def test_references_are_complete():
    for key, ref in REFS.items():
        assert ref.short and ref.authors and ref.title, key
        assert ref.year or ref.url or ref.kind in ("standard", "dataset"), key
        if ref.kind == "article":
            assert ref.container and ref.detail, key
        if ref.doi:
            assert re.fullmatch(r"10\.\d{4,9}/\S+", ref.doi), key
        assert full_citation(key)


def test_unused_references_are_not_left_in_the_bibliography():
    used = {k for t in SOURCES for k in cited_keys(t)}
    assert set(REFS) <= used, sorted(set(REFS) - used)


def test_the_block_and_the_report_section():
    html = sources_html("wind.wake", full=True)
    assert "Jensen (1983)" in html and "Risø-M-2411" in html
    section = references_html(html + sources_html("pv.irradiation"))
    assert section.startswith("<h2>References</h2>")
    assert section.index("Huld") < section.index("Jensen")      # alphabetical
    assert references_html("<p>nothing cited</p>") == ""
