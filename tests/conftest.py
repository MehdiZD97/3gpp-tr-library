import os
import sys

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from section_utils import discover_section_md_files, read_csv_rows, split_front_matter  # noqa: E402

SECTION_7_4_MD = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", "7.4-pathloss.md")
SECTION_7_4_YAML = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", "7.4-pathloss.yaml")
SECTION_7_5_MD = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", "7.5-fast-fading.md")
SECTION_7_5_YAML = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", "7.5-fast-fading.yaml")
TABLES_DIR = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", "tables")

ANNEX_B_MD = os.path.join(REPO_ROOT, "TR-36.777", "v15.0.0", "annex-b-channel-modelling", "B-channel-modelling.md")
ANNEX_B_YAML = os.path.join(REPO_ROOT, "TR-36.777", "v15.0.0", "annex-b-channel-modelling", "B-channel-modelling.yaml")
ANNEX_B_TABLES_DIR = os.path.join(REPO_ROOT, "TR-36.777", "v15.0.0", "annex-b-channel-modelling", "tables")


@pytest.fixture(scope="session")
def repo_root():
    return REPO_ROOT


@pytest.fixture(scope="session")
def all_section_md_paths():
    paths = discover_section_md_files()
    assert paths, "no section .md files discovered under TR-*/v*/"
    return paths


@pytest.fixture(scope="session")
def all_section_front_matters(all_section_md_paths):
    result = {}
    for path in all_section_md_paths:
        with open(path) as f:
            text = f.read()
        fm_text, _ = split_front_matter(text)
        result[path] = yaml.safe_load(fm_text)
    return result


@pytest.fixture(scope="session")
def section_7_4_md_path():
    return SECTION_7_4_MD


@pytest.fixture(scope="session")
def section_7_4_raw_text():
    with open(SECTION_7_4_MD) as f:
        return f.read()


@pytest.fixture(scope="session")
def section_7_4_front_matter(section_7_4_raw_text):
    fm_text, _ = split_front_matter(section_7_4_raw_text)
    return yaml.safe_load(fm_text)


@pytest.fixture(scope="session")
def section_7_4_body(section_7_4_raw_text):
    _, body = split_front_matter(section_7_4_raw_text)
    return body


@pytest.fixture(scope="session")
def section_7_4_yaml_path():
    return SECTION_7_4_YAML


@pytest.fixture(scope="session")
def section_7_4_yaml_data():
    with open(SECTION_7_4_YAML) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def tables_dir():
    return TABLES_DIR


@pytest.fixture(scope="session")
def table_7_4_1_1_rows():
    return read_csv_rows(os.path.join(TABLES_DIR, "table-7.4.1-1.csv"))


@pytest.fixture(scope="session")
def table_7_4_2_1_rows():
    return read_csv_rows(os.path.join(TABLES_DIR, "table-7.4.2-1.csv"))


@pytest.fixture(scope="session")
def table_7_4_3_1_rows():
    return read_csv_rows(os.path.join(TABLES_DIR, "table-7.4.3-1.csv"))


@pytest.fixture(scope="session")
def table_7_4_3_2_rows():
    return read_csv_rows(os.path.join(TABLES_DIR, "table-7.4.3-2.csv"))


@pytest.fixture(scope="session")
def table_7_4_3_3_rows():
    return read_csv_rows(os.path.join(TABLES_DIR, "table-7.4.3-3.csv"))


@pytest.fixture(scope="session")
def section_7_5_md_path():
    return SECTION_7_5_MD


@pytest.fixture(scope="session")
def section_7_5_raw_text():
    with open(SECTION_7_5_MD) as f:
        return f.read()


@pytest.fixture(scope="session")
def section_7_5_front_matter(section_7_5_raw_text):
    fm_text, _ = split_front_matter(section_7_5_raw_text)
    return yaml.safe_load(fm_text)


@pytest.fixture(scope="session")
def section_7_5_body(section_7_5_raw_text):
    _, body = split_front_matter(section_7_5_raw_text)
    return body


@pytest.fixture(scope="session")
def section_7_5_yaml_path():
    return SECTION_7_5_YAML


@pytest.fixture(scope="session")
def section_7_5_yaml_data():
    with open(SECTION_7_5_YAML) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def table_7_5_1_rows():
    return read_csv_rows(os.path.join(TABLES_DIR, "table-7.5-1.csv"))


@pytest.fixture(scope="session")
def table_7_5_2_rows():
    return read_csv_rows(os.path.join(TABLES_DIR, "table-7.5-2.csv"))


@pytest.fixture(scope="session")
def table_7_5_3_rows():
    return read_csv_rows(os.path.join(TABLES_DIR, "table-7.5-3.csv"))


@pytest.fixture(scope="session")
def table_7_5_4_rows():
    return read_csv_rows(os.path.join(TABLES_DIR, "table-7.5-4.csv"))


@pytest.fixture(scope="session")
def table_7_5_5_rows():
    return read_csv_rows(os.path.join(TABLES_DIR, "table-7.5-5.csv"))


@pytest.fixture(scope="session")
def table_7_5_6_rows():
    return read_csv_rows(os.path.join(TABLES_DIR, "table-7.5-6.csv"))


@pytest.fixture(scope="session", params=["7.5-7", "7.5-8", "7.5-9", "7.5-10", "7.5-11", "7.5-12"])
def zsd_zod_table_rows(request):
    return request.param, read_csv_rows(os.path.join(TABLES_DIR, f"table-{request.param}.csv"))


# --- TR 36.777 Annex B fixtures (mirror the §7.4/§7.5 ones for a second TR) ---
@pytest.fixture(scope="session")
def annex_b_md_path():
    return ANNEX_B_MD


@pytest.fixture(scope="session")
def annex_b_raw_text():
    with open(ANNEX_B_MD) as f:
        return f.read()


@pytest.fixture(scope="session")
def annex_b_front_matter(annex_b_raw_text):
    fm_text, _ = split_front_matter(annex_b_raw_text)
    return yaml.safe_load(fm_text)


@pytest.fixture(scope="session")
def annex_b_yaml_data():
    with open(ANNEX_B_YAML) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session", params=["B-1", "B-2", "B-3", "B-4", "B.1.1-1", "B.1.1-2", "B.1.2-1", "B.1.2-2"])
def annex_b_table_rows(request):
    return request.param, read_csv_rows(os.path.join(ANNEX_B_TABLES_DIR, f"table-{request.param}.csv"))
