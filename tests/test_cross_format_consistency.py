"""
Cross-file consistency checks: CSV <-> YAML <-> inline Markdown table must
all agree. The CSV <-> YAML comparisons below call `tools/verify_tables.py`'s
generalized `verify_table()` / `verify_flat_param_table()` -- promoted in
Phase 3 from five near-identical hand-written functions that lived here in
Phase 2.
"""
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from verify_tables import (  # noqa: E402
    _variant_key_normalizer,
    flatten_std,
    identity,
    join_notes,
    verify_flat_param_table,
    verify_table,
)


def test_table_7_4_1_1_csv_matches_yaml(tables_dir, section_7_4_yaml_data):
    errors = verify_table(
        os.path.join(tables_dir, "table-7.4.1-1.csv"),
        section_7_4_yaml_data["pathloss"],
        key_fields=("scenario", "condition", "variant"),
        key_normalizer=_variant_key_normalizer,
        field_map={
            "formula": ("formula", identity),
            "shadow_fading_std_db": ("shadow_fading_std_db", flatten_std),
            "applicability_range": ("applicability_range", identity),
            "notes": ("notes", join_notes),
        },
    )
    assert not errors, "\n".join(errors)


def test_table_7_4_2_1_csv_matches_yaml(tables_dir, section_7_4_yaml_data):
    errors = verify_table(
        os.path.join(tables_dir, "table-7.4.2-1.csv"),
        section_7_4_yaml_data["los_probability"],
        key_fields=("scenario",),
        field_map={
            "formula": ("formula", identity),
            "notes": ("notes", join_notes),
        },
    )
    assert not errors, "\n".join(errors)


def test_table_7_4_3_1_csv_matches_yaml(tables_dir, section_7_4_yaml_data):
    errors = verify_table(
        os.path.join(tables_dir, "table-7.4.3-1.csv"),
        section_7_4_yaml_data["o2i_penetration_loss"]["materials"],
        key_fields=("material",),
        field_map={
            "formula": ("formula", identity),
            "notes": ("notes", join_notes),
        },
    )
    assert not errors, "\n".join(errors)


def test_table_7_4_3_2_csv_matches_yaml(tables_dir, section_7_4_yaml_data):
    errors = verify_table(
        os.path.join(tables_dir, "table-7.4.3-2.csv"),
        section_7_4_yaml_data["o2i_penetration_loss"]["building_models"],
        key_fields=("model",),
        field_map={
            "pl_tw_formula": ("pl_tw_formula", identity),
            "pl_in_formula": ("pl_in_formula", identity),
            "std_p_db": ("std_p_db", lambda v: str(v)),
        },
    )
    assert not errors, "\n".join(errors)


def test_table_7_4_3_3_csv_matches_yaml(tables_dir, section_7_4_yaml_data):
    entry = section_7_4_yaml_data["o2i_penetration_loss"]["building_single_frequency_below_6ghz"]
    errors = verify_flat_param_table(
        os.path.join(tables_dir, "table-7.4.3-3.csv"),
        entry,
        field_map={
            "PL_tw": ("pl_tw_db", lambda v: f"{v} dB"),
            "PL_in": ("pl_in_formula", identity),
            "sigma_P": ("sigma_p_db", lambda v: f"{v} dB"),
            "sigma_SF": ("sigma_sf_db", lambda v: f"{v} dB ({entry['note']})"),
        },
    )
    assert not errors, "\n".join(errors)


def test_inline_markdown_table_7_4_1_1_matches_csv(section_7_4_body, table_7_4_1_1_rows):
    header, *data_rows = table_7_4_1_1_rows
    md_rows = [
        line for line in section_7_4_body.splitlines()
        if line.startswith("| ") and "Scenario" not in line and "---" not in line
    ]
    # Only the first pathloss-style table has this exact column shape; scope
    # to lines that plausibly belong to Table 7.4.1-1 by matching row count.
    pathloss_md_rows = md_rows[: len(data_rows)]
    assert len(pathloss_md_rows) == len(data_rows)

    for csv_row, md_line in zip(data_rows, pathloss_md_rows):
        scenario, condition, variant, formula, std, applicability, notes = csv_row
        assert f"| {scenario} | {condition} | {variant or '—'} |" in md_line
        # The formula appears wrapped in $...$ math delimiters in the markdown.
        assert formula in md_line


def test_depends_on_entries_are_well_formed(section_7_4_front_matter):
    depends_on = section_7_4_front_matter["depends_on"]
    assert isinstance(depends_on, list)
    assert depends_on, "depends_on should not be empty for a section with a real dependency"
    for entry in depends_on:
        assert isinstance(entry, str) and entry.strip(), "depends_on entry must be a non-empty string"
        assert re.match(r"^\d+(\.\d+)*-[a-z0-9-]+$", entry), (
            f"depends_on entry {entry!r} doesn't look like a well-formed section id "
            "(e.g. '7.2-coordinate-system')"
        )
