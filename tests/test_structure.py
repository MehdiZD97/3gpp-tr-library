import os

import yaml

REQUIRED_FRONT_MATTER_FIELDS = [
    "tr", "version", "section", "title", "parent", "summary",
    "depends_on", "source_pdf", "status", "verified_against",
]


def test_section_7_4_md_exists(section_7_4_md_path):
    assert os.path.isfile(section_7_4_md_path)


def test_all_discovered_sections_have_valid_front_matter(all_section_front_matters):
    for path, fm in all_section_front_matters.items():
        assert isinstance(fm, dict), f"{path}: front matter did not parse to a mapping"


def test_all_discovered_sections_have_required_fields(all_section_front_matters):
    for path, fm in all_section_front_matters.items():
        missing = [field for field in REQUIRED_FRONT_MATTER_FIELDS if field not in fm]
        assert not missing, f"{path}: missing front matter fields {missing}"


def test_section_7_4_section_field_is_string(section_7_4_front_matter):
    assert isinstance(section_7_4_front_matter["section"], str)
    assert section_7_4_front_matter["section"] == "7.4"


def test_section_7_4_status_is_valid(section_7_4_front_matter):
    assert section_7_4_front_matter["status"] in ("planned", "in-progress", "verified")


def test_section_7_4_yaml_exists_and_parses(section_7_4_yaml_path):
    assert os.path.isfile(section_7_4_yaml_path)
    with open(section_7_4_yaml_path) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_section_7_4_yaml_has_expected_top_level_keys(section_7_4_yaml_data):
    for key in ("pathloss", "los_probability", "o2i_penetration_loss", "shadow_fading_autocorrelation"):
        assert key in section_7_4_yaml_data


def test_all_tables_parse_with_consistent_columns(
    table_7_4_1_1_rows, table_7_4_2_1_rows, table_7_4_3_1_rows, table_7_4_3_2_rows, table_7_4_3_3_rows,
):
    # read_csv_rows() (used by each fixture) already asserts consistent column
    # counts per row; reaching this point means every table parsed cleanly.
    assert len(table_7_4_1_1_rows) > 1
    assert len(table_7_4_2_1_rows) > 1
    assert len(table_7_4_3_1_rows) > 1
    assert len(table_7_4_3_2_rows) > 1
    assert len(table_7_4_3_3_rows) > 1


def test_tr_38901_readme_exists(repo_root):
    path = os.path.join(repo_root, "TR-38.901", "README.md")
    assert os.path.isfile(path)


def test_index_md_contains_7_4_row(repo_root):
    path = os.path.join(repo_root, "INDEX.md")
    with open(path) as f:
        content = f.read()
    assert "§7.4" in content
    assert "TR 38.901" in content
