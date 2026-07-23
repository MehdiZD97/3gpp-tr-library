"""
Shared low-level helpers for locating and parsing section files: front
matter, CSV tables, and discovery of every section `.md` under `TR-*/v*/`.

Used by both `tests/conftest.py` (fixtures) and `tools/verify_tables.py`
(the standalone verification CLI) so the two don't maintain separate copies
of the same parsing logic.
"""
import csv
import glob
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def split_front_matter(md_text):
    match = FRONT_MATTER_RE.match(md_text)
    assert match, "front matter block (---...---) not found at top of file"
    return match.group(1), match.group(2)


def discover_section_md_files(repo_root=REPO_ROOT):
    """Any .md file under TR-*/v*/ that isn't a TR-level or top-level README."""
    pattern = os.path.join(repo_root, "TR-*", "v*", "**", "*.md")
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
