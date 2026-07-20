import os

# TR -> known canonical 3gpp.org link, for the generic cross-TR check below.
KNOWN_SOURCE_PDF_BY_TR = {
    "TR 38.901": "https://www.3gpp.org/dynareport/38901.htm",
    "TR 36.777": "https://www.3gpp.org/dynareport/36777.htm",
}
KNOWN_SOURCE_PDF = KNOWN_SOURCE_PDF_BY_TR["TR 38.901"]


def test_front_matter_tr_and_version(section_7_4_front_matter):
    assert section_7_4_front_matter["tr"] == "TR 38.901"
    assert section_7_4_front_matter["version"] == "v19.4.0"


def test_file_path_matches_front_matter_version(section_7_4_md_path, section_7_4_front_matter):
    version = section_7_4_front_matter["version"]
    assert f"{os.sep}{version}{os.sep}" in section_7_4_md_path


def test_source_pdf_matches_known_link(section_7_4_front_matter):
    assert section_7_4_front_matter["source_pdf"] == KNOWN_SOURCE_PDF


# --- Generic versions: these run over every discovered section file, not
# just §7.4, so Phase 4+ sections get this coverage without hand-adding a
# duplicate per-section test. (Confirmed, not assumed, that these weren't
# already generic before Phase 4 added a second section to check them
# against -- they weren't; test_structure.py's discovery-based tests were
# the only genuinely generic ones. Fixed here rather than routed around.)
def test_all_discovered_sections_file_path_matches_front_matter_version(all_section_front_matters):
    for path, fm in all_section_front_matters.items():
        version = fm["version"]
        assert f"{os.sep}{version}{os.sep}" in path, f"{path}: front matter version {version!r} not found in its own path"


def test_all_discovered_sections_source_pdf_matches_known_link(all_section_front_matters):
    for path, fm in all_section_front_matters.items():
        expected = KNOWN_SOURCE_PDF_BY_TR.get(fm["tr"])
        if expected is None:
            continue  # no known-link table entry yet for this TR; nothing to check against
        assert fm["source_pdf"] == expected, f"{path}: unexpected source_pdf for {fm['tr']}"
