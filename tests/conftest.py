import csv
import glob
import os
import re

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECTION_7_4_MD = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", "7.4-pathloss.md")
SECTION_7_4_YAML = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", "7.4-pathloss.yaml")
TABLES_DIR = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", "tables")

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def split_front_matter(md_text):
    match = FRONT_MATTER_RE.match(md_text)
    assert match, "front matter block (---...---) not found at top of file"
    return match.group(1), match.group(2)


def discover_section_md_files():
    """Any .md file under TR-*/v*/ that isn't a TR-level or top-level README."""
    pattern = os.path.join(REPO_ROOT, "TR-*", "v*", "**", "*.md")
    files = glob.glob(pattern, recursive=True)
    return sorted(f for f in files if os.path.basename(f) != "README.md")


def read_csv_rows(path):
    with open(path, newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert rows, f"{path} is empty"
    header = rows[0]
    ncols = len(header)
    for i, row in enumerate(rows[1:], start=2):
        assert len(row) == ncols, f"{path}: row {i} has {len(row)} columns, expected {ncols}"
    return rows


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
