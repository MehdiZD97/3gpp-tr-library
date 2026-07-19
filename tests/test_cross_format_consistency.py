"""
Cross-file consistency checks: CSV <-> YAML <-> inline Markdown table must
all agree. This is a hand-written preview of what `tools/verify_tables.py`
(Phase 3) will do generically -- written so the comparison logic here could
plausibly be lifted into that tool later rather than thrown away.
"""
import re


def _flatten_std(std_list):
    if len(std_list) == 1 and std_list[0]["condition"] is None:
        return str(std_list[0]["value_db"])
    return "; ".join(f"{s['value_db']} dB ({s['condition']})" for s in std_list)


def test_table_7_4_1_1_csv_matches_yaml(table_7_4_1_1_rows, section_7_4_yaml_data):
    header, *data_rows = table_7_4_1_1_rows
    assert header == ["scenario", "condition", "variant", "formula", "shadow_fading_std_db", "applicability_range", "notes"]

    yaml_by_key = {
        (row["scenario"], row["condition"], row["variant"] or ""): row
        for row in section_7_4_yaml_data["pathloss"]
    }
    assert len(data_rows) == len(yaml_by_key)

    for scenario, condition, variant, formula, std, applicability, notes in data_rows:
        key = (scenario, condition, variant)
        assert key in yaml_by_key, f"CSV row {key} has no matching YAML entry"
        yrow = yaml_by_key[key]
        assert formula == yrow["formula"]
        assert std == _flatten_std(yrow["shadow_fading_std_db"])
        assert applicability == yrow["applicability_range"]
        assert notes == "; ".join(yrow["notes"])


def test_table_7_4_2_1_csv_matches_yaml(table_7_4_2_1_rows, section_7_4_yaml_data):
    header, *data_rows = table_7_4_2_1_rows
    assert header == ["scenario", "formula", "notes"]

    yaml_by_scenario = {row["scenario"]: row for row in section_7_4_yaml_data["los_probability"]}
    assert len(data_rows) == len(yaml_by_scenario)

    for scenario, formula, notes in data_rows:
        yrow = yaml_by_scenario[scenario]
        assert formula == yrow["formula"]
        assert notes == "; ".join(yrow["notes"])


def test_table_7_4_3_1_csv_matches_yaml(table_7_4_3_1_rows, section_7_4_yaml_data):
    header, *data_rows = table_7_4_3_1_rows
    assert header == ["material", "formula", "notes"]

    yaml_by_material = {m["material"]: m for m in section_7_4_yaml_data["o2i_penetration_loss"]["materials"]}
    assert len(data_rows) == len(yaml_by_material)

    for material, formula, notes in data_rows:
        yrow = yaml_by_material[material]
        assert formula == yrow["formula"]
        assert notes == "; ".join(yrow["notes"])


def test_table_7_4_3_2_csv_matches_yaml(table_7_4_3_2_rows, section_7_4_yaml_data):
    header, *data_rows = table_7_4_3_2_rows
    assert header == ["model", "pl_tw_formula", "pl_in_formula", "std_p_db"]

    yaml_by_model = {m["model"]: m for m in section_7_4_yaml_data["o2i_penetration_loss"]["building_models"]}
    assert len(data_rows) == len(yaml_by_model)

    for model, pl_tw, pl_in, std in data_rows:
        yrow = yaml_by_model[model]
        assert pl_tw == yrow["pl_tw_formula"]
        assert pl_in == yrow["pl_in_formula"]
        assert float(std) == yrow["std_p_db"]


def test_table_7_4_3_3_csv_matches_yaml(table_7_4_3_3_rows, section_7_4_yaml_data):
    header, *data_rows = table_7_4_3_3_rows
    assert header == ["parameter", "value"]

    entry = section_7_4_yaml_data["o2i_penetration_loss"]["building_single_frequency_below_6ghz"]
    values = {row[0]: row[1] for row in data_rows}
    assert values["PL_tw"] == f"{entry['pl_tw_db']} dB"
    assert values["PL_in"] == entry["pl_in_formula"]
    assert values["sigma_P"] == f"{entry['sigma_p_db']} dB"
    assert values["sigma_SF"] == f"{entry['sigma_sf_db']} dB ({entry['note']})"


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
