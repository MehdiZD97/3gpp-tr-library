"""
Genuine automated drift detection: re-parse the .docx source and check that
its structural facts (headings, scenario labels, table count under §7.4)
still match what's committed. This complements, but does not replace,
test_values.py's regression-locked numbers -- python-docx cannot recover the
pathloss formulas themselves (they're embedded Word equation objects with no
extractable .text), so formula content is not re-checked here. That's the
one piece of verification that stays manual: a PDF visual read, whose result
is what's locked into test_values.py.

Skips cleanly if the (gitignored, not-committed) reference source isn't
present, since references/ is never available in a fresh clone or CI.
"""
import os

import pytest

docx = pytest.importorskip("docx")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DOCX = os.path.join(REPO_ROOT, "references", "3gpp-tr38901", "v19.4.0", "38901-j40.docx")

pytestmark = pytest.mark.skipif(
    not os.path.isfile(SOURCE_DOCX),
    reason="references/ source document not present (gitignored, local-only)",
)

EXPECTED_HEADINGS = [
    "7.4\tPathloss, LOS probability and penetration modelling",
    "7.4.1\tPathloss",
    "7.4.2\tLOS probability",
    "7.4.3\tO2I penetration loss",
    "7.4.3.1\tO2I building penetration loss",
    "7.4.3.2\tO2I car penetration loss",
    "7.4.4\tAutocorrelation of shadow fading",
]


def _iter_block_items(parent):
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in parent.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


@pytest.fixture(scope="module")
def section_7_4_recon():
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(SOURCE_DOCX)
    capture = False
    headings = []
    table_count = 0
    first_table_first_column = []

    for block in _iter_block_items(document):
        if isinstance(block, Paragraph):
            style = block.style.name if block.style else ""
            text = block.text.strip()
            tok = text.split()[0] if text else ""
            if style.startswith("Heading") and text:
                if tok.startswith("7.4"):
                    capture = True
                    headings.append(text)
                elif tok.startswith("7.5"):
                    capture = False
        elif isinstance(block, Table) and capture:
            table_count += 1
            if table_count == 2:  # Table 7.4.1-1, the master pathloss table
                first_table_first_column = [row.cells[0].text.strip() for row in block.rows[1:]]

    return {
        "headings": headings,
        "table_count": table_count,
        "pathloss_table_scenarios": first_table_first_column,
    }


def test_section_7_4_headings_unchanged(section_7_4_recon):
    assert section_7_4_recon["headings"] == EXPECTED_HEADINGS


def test_section_7_4_table_count_unchanged(section_7_4_recon):
    assert section_7_4_recon["table_count"] == 6


def _normalize_scenario_label(label):
    # The source table spells some labels with spaces around a hyphen
    # ("UMi - Street Canyon", "InH - Office"); the YAML uses a compact,
    # space-free form ("UMi-StreetCanyon", "InH-Office"). Same scenario,
    # different formatting -- normalize before comparing.
    return label.replace(" - ", "-").replace(" ", "")


def test_pathloss_table_scenario_labels_unchanged(section_7_4_recon, section_7_4_yaml_data):
    docx_scenarios = {
        _normalize_scenario_label(s)
        for s in section_7_4_recon["pathloss_table_scenarios"]
        if s and not s.startswith("NOTE")
    }
    yaml_scenarios = {row["scenario"] for row in section_7_4_yaml_data["pathloss"]}
    # The docx repeats a scenario label across its LOS/NLOS/optional rows for
    # RMa/UMa/UMi/InH/SMa but leaves it blank for the continuation rows -- so
    # compare the set of non-empty labels found, not a positional list.
    assert docx_scenarios <= yaml_scenarios
