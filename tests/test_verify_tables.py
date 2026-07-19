"""
Tests for tools/verify_tables.py's own reusable checking logic -- a
deliberately-broken fixture must be caught, a valid one must pass cleanly.
"""
import csv
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from verify_tables import identity, main, verify_flat_param_table, verify_table  # noqa: E402


def _write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def test_verify_table_passes_on_matching_fixture(tmp_path):
    csv_path = tmp_path / "table.csv"
    _write_csv(csv_path, ["name", "value"], [["a", "1"], ["b", "2"]])
    yaml_entries = [{"name": "a", "value": "1"}, {"name": "b", "value": "2"}]

    errors = verify_table(
        str(csv_path), yaml_entries,
        key_fields=("name",),
        field_map={"value": ("value", identity)},
    )
    assert errors == []


def test_verify_table_catches_mismatched_value(tmp_path):
    csv_path = tmp_path / "table.csv"
    _write_csv(csv_path, ["name", "value"], [["a", "1"], ["b", "WRONG"]])
    yaml_entries = [{"name": "a", "value": "1"}, {"name": "b", "value": "2"}]

    errors = verify_table(
        str(csv_path), yaml_entries,
        key_fields=("name",),
        field_map={"value": ("value", identity)},
    )
    assert len(errors) == 1
    assert "WRONG" in errors[0]


def test_verify_table_catches_missing_yaml_entry(tmp_path):
    csv_path = tmp_path / "table.csv"
    _write_csv(csv_path, ["name", "value"], [["a", "1"], ["ghost", "1"]])
    yaml_entries = [{"name": "a", "value": "1"}]

    errors = verify_table(
        str(csv_path), yaml_entries,
        key_fields=("name",),
        field_map={"value": ("value", identity)},
    )
    assert any("no matching YAML entry" in e for e in errors)


def test_verify_flat_param_table_passes_on_matching_fixture(tmp_path):
    csv_path = tmp_path / "flat.csv"
    _write_csv(csv_path, ["parameter", "value"], [["x", "5 dB"]])
    entry = {"x_db": 5}

    errors = verify_flat_param_table(str(csv_path), entry, field_map={"x": ("x_db", lambda v: f"{v} dB")})
    assert errors == []


def test_verify_flat_param_table_catches_mismatch(tmp_path):
    csv_path = tmp_path / "flat.csv"
    _write_csv(csv_path, ["parameter", "value"], [["x", "5 dB"]])
    entry = {"x_db": 6}

    errors = verify_flat_param_table(str(csv_path), entry, field_map={"x": ("x_db", lambda v: f"{v} dB")})
    assert len(errors) == 1
    assert "5 dB" in errors[0] and "6 dB" in errors[0]


def test_main_passes_cleanly_against_real_repo_data(capsys):
    exit_code = main()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "PASSED" in captured.out
