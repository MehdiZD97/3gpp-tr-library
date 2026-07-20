"""
Cross-file consistency checks for §7.5. CSV<->YAML agreement for every
table is already covered generically by tools/verify_tables.py's
verify_section_7_5() (exercised end-to-end via test_verify_tables.py's
test_main_passes_cleanly_against_real_repo_data); this file covers the one
comparison that tool doesn't do: the inline Markdown table for 7.5-6, which
is intentionally *transposed* relative to the CSV (parameter rows x
scenario/condition columns, matching the TR's own presentation, instead of
the CSV's one-row-per-scenario/condition shape -- see 7.5-fast-fading.md's
own note on why). Both are generated from the same source data during
extraction, but this test guards against future hand-edits letting them
drift apart.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from verify_tables import _CHANNEL_MODEL_PARAM_FIELDS, PARAM_LABELS  # noqa: E402,F401


def _parse_markdown_table(md_lines):
    """Parse a pipe-delimited Markdown table's header + body rows (skips the --- separator)."""
    rows = [line.strip().strip("|").split("|") for line in md_lines if line.strip().startswith("|")]
    rows = [[cell.strip() for cell in row] for row in rows]
    rows = [row for row in rows if not all(set(cell) <= {"-"} for cell in row)]
    return rows


def test_inline_table_7_5_6_transposed_matches_csv(section_7_5_body, table_7_5_6_rows):
    # Table 7.5-1's notation glossary also has a "| Parameter | ..." header,
    # so match on a prefix distinctive to Table 7.5-6's own header instead.
    md_lines = [
        line for line in section_7_5_body.splitlines()
        if line.startswith("| Parameter | UMi - Street Canyon LOS |")
    ]
    assert len(md_lines) == 1, "expected exactly one Table 7.5-6 header line"
    header_idx = section_7_5_body.splitlines().index(md_lines[0])
    body_lines = section_7_5_body.splitlines()[header_idx:header_idx + 2 + 49]
    table = _parse_markdown_table(body_lines)
    header, *data_rows = table
    assert len(data_rows) == 49, f"expected 49 parameter rows, found {len(data_rows)}"

    scenario_condition_columns = header[1:]
    csv_header, *csv_rows = table_7_5_6_rows
    csv_by_key = {(row[0], row[1]): dict(zip(csv_header, row)) for row in csv_rows}

    param_labels = list(PARAM_LABELS.values())
    param_keys = list(PARAM_LABELS.keys())
    assert [row[0] for row in data_rows] == param_labels

    for row in data_rows:
        label = row[0]
        param_key = param_keys[param_labels.index(label)]
        for col_name, md_value in zip(scenario_condition_columns, row[1:]):
            scenario, condition = col_name.rsplit(" ", 1)
            csv_value = csv_by_key[(scenario, condition)][param_key]
            assert md_value == csv_value, f"{label} / {col_name}: markdown={md_value!r} != csv={csv_value!r}"


def test_depends_on_entries_are_well_formed_7_5(section_7_5_front_matter):
    import re

    depends_on = section_7_5_front_matter["depends_on"]
    assert isinstance(depends_on, list) and depends_on
    for entry in depends_on:
        assert isinstance(entry, str) and entry.strip()
        assert re.match(r"^\d+(\.\d+)*-[a-z0-9-]+$", entry), f"{entry!r} doesn't look like a well-formed section id"
