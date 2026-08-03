"""
Tests for tools/verify_tables.py's own reusable checking logic -- a
deliberately-broken fixture must be caught, a valid one must pass cleanly.
"""
import csv
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from verify_tables import (  # noqa: E402
    html_region_has_text_formulas,
    identity,
    main,
    verify_flat_param_table,
    verify_table,
)


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


def test_html_region_detects_text_vs_image_formulas(tmp_path):
    # An OMML-bearing region (TR 38.901 style) -> formulas are text.
    omml = tmp_path / "omml.html"
    omml.write_text("<p>START</p><m:oMath><m:r>28.0</m:r></m:oMath><p>END</p>")
    assert html_region_has_text_formulas(str(omml), "START", "END") is True

    # An image-only region (TR 36.777 style) -> not text.
    imaged = tmp_path / "imaged.html"
    imaged.write_text('<p>START</p><img src="image029.png"><p>END</p>')
    assert html_region_has_text_formulas(str(imaged), "START", "END") is False


def test_html_region_check_matches_real_tr36777_when_present():
    # If the (gitignored) TR 36.777 HTML is present locally, confirm the
    # helper agrees that its Annex B region is image-embedded -- the finding
    # that makes verify_annex_b skip (not fail) the formula cross-check.
    html = os.path.join(
        REPO_ROOT, "references", "3gpp-tr36777", "v15.0.0", "36777-f00_1.html"
    )
    if not os.path.isfile(html):
        import pytest

        pytest.skip("TR 36.777 HTML not present locally (gitignored)")
    assert html_region_has_text_formulas(html, "Channel modelling details", "Calibration results and RSRP") is False


def test_section_7_9_html_region_is_omml_text_when_present():
    # The mirror of the TR 36.777 case: §7.9 (Rel-19, 2026) renders equations
    # as OMML *text*, so the RCS/XPR HTML cross-check in verify_section_7_9()
    # *applies* here rather than skipping. Confirm the helper agrees, using the
    # same region markers verify_section_7_9() uses.
    html = os.path.join(REPO_ROOT, "references", "3gpp-tr38901", "v19.4.0", "38901-j40.html")
    if not os.path.isfile(html):
        import pytest

        pytest.skip("TR 38.901 HTML not present locally (gitignored)")
    assert html_region_has_text_formulas(html, "Parameters on RCS for the STs", "Channel model for STX-ST") is True


def test_section_7_6_checker_passes_on_real_data():
    # verify_section_7_6() covers all eleven in-scope tables with the existing
    # verify_table() checker -- no new checker shape was needed.
    from verify_tables import verify_section_7_6
    assert verify_section_7_6() == []


def test_section_7_6_checker_catches_a_yaml_drift(monkeypatch, tmp_path):
    # Point the checker at a deliberately corrupted copy of the YAML and confirm
    # it reports the CSV<->YAML disagreement instead of passing.
    import shutil

    import verify_tables as vt

    corrupted = tmp_path / "7.6-corrupt.yaml"
    shutil.copy(vt.SECTION_7_6_YAML_PATH, corrupted)
    text = corrupted.read_text().replace("alpha_db_per_km: '15'", "alpha_db_per_km: '99'", 1)
    assert "99" in text, "fixture setup failed: the 60 GHz peak value was not substituted"
    corrupted.write_text(text)

    monkeypatch.setattr(vt, "SECTION_7_6_YAML_PATH", str(corrupted))
    errors = vt.verify_section_7_6()
    assert errors, "a drifted YAML value was not caught"
    assert any("table-7.6.1-1.csv" in e for e in errors)


def test_section_7_6_html_region_is_omml_text_when_present():
    # §7.6 is release-stratified: its *equations* are OLE/.wmz images in the
    # older sub-clauses, but the region still carries OMML text (7.6.9 onward),
    # and every table *cell value* renders as text -- which is what
    # verify_section_7_6()'s value cross-check actually re-reads.
    html = os.path.join(REPO_ROOT, "references", "3gpp-tr38901", "v19.4.0", "38901-j40.html")
    if not os.path.isfile(html):
        import pytest

        pytest.skip("TR 38.901 HTML not present locally (gitignored)")
    assert html_region_has_text_formulas(html, "7.6.0", "Clustered Delay Line (CDL) models") is True
