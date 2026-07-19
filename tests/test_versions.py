import os

KNOWN_SOURCE_PDF = "https://www.3gpp.org/dynareport/38901.htm"


def test_front_matter_tr_and_version(section_7_4_front_matter):
    assert section_7_4_front_matter["tr"] == "TR 38.901"
    assert section_7_4_front_matter["version"] == "v19.4.0"


def test_file_path_matches_front_matter_version(section_7_4_md_path, section_7_4_front_matter):
    version = section_7_4_front_matter["version"]
    assert f"{os.sep}{version}{os.sep}" in section_7_4_md_path


def test_source_pdf_matches_known_link(section_7_4_front_matter):
    assert section_7_4_front_matter["source_pdf"] == KNOWN_SOURCE_PDF
