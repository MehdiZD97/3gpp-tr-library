"""
Generalized CSV <-> YAML verification, promoted from the per-table checks
hand-written in tests/test_cross_format_consistency.py during Phase 2.

Two generic checkers cover the real data shapes found in this repo so far:

- `verify_table()` for "list of entities keyed by one or more fields" tables
  (e.g. Table 7.4.1-1: one row per scenario/condition/variant).
- `verify_flat_param_table()` for "parameter, value" tables matched against
  a single YAML dict (e.g. Table 7.4.3-3).

These are deliberately two functions, not one contorted abstraction --
`o2i_penetration_loss` alone has four different sub-shapes (see
`docs/phase-plans/phase-3-tasks.md`), and forcing all of them through one
generic shape would be a worse abstraction than two honest ones.

Also home to `check_formulas_against_html()`, the promoted version of the
HTML-based formula cross-check first proven ad hoc in
`_scratch/extract_full.py` during Phase 2 (see CLAUDE.md's references/
notes on why the HTML export -- not just the docx -- is needed for formula
content).

CLI usage: `python tools/verify_tables.py` discovers every processed
section, validates its YAML against the Pydantic models in
`tools/tr_api/models.py`, cross-checks every table's CSV against its YAML,
and (when `references/` is present locally) cross-checks formulas against
the HTML export. Prints a pass/fail summary and exits non-zero on any
failure.
"""
import os
import re
import sys

import yaml
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from section_utils import REPO_ROOT, discover_section_md_files, read_csv_rows, split_front_matter  # noqa: E402
from tr_api.models import Section74Data  # noqa: E402


# ---------------------------------------------------------------------------
# Generic CSV <-> YAML checkers
# ---------------------------------------------------------------------------
def flatten_std(std_list):
    if len(std_list) == 1 and std_list[0]["condition"] is None:
        return str(std_list[0]["value_db"])
    return "; ".join(f"{s['value_db']} dB ({s['condition']})" for s in std_list)


def join_notes(notes):
    return "; ".join(notes)


def identity(value):
    return value


def verify_table(csv_path, yaml_entries, key_fields, field_map, key_normalizer=None):
    """
    Check a "list of entities, one row per entity" CSV against its YAML list.

    key_fields: CSV column names that together uniquely identify a row/entry.
    field_map: {csv_column: (yaml_field, formatter)}, where formatter(value)
               returns the string the CSV cell is expected to equal.
    key_normalizer: optional fn(tuple) -> tuple, applied to both the CSV-derived
                     and YAML-derived key (e.g. to fold "" and None together).

    Returns a list of human-readable mismatch strings; empty means OK.
    """
    errors = []
    header, *data_rows = read_csv_rows(csv_path)
    key_indices = [header.index(k) for k in key_fields]

    def normalize(raw):
        return key_normalizer(raw) if key_normalizer else raw

    yaml_by_key = {normalize(tuple(e[k] for k in key_fields)): e for e in yaml_entries}

    if len(data_rows) != len(yaml_by_key):
        errors.append(f"{csv_path}: {len(data_rows)} CSV rows vs {len(yaml_by_key)} YAML entries")

    for row in data_rows:
        key = normalize(tuple(row[i] for i in key_indices))
        if key not in yaml_by_key:
            errors.append(f"{csv_path}: row {key} has no matching YAML entry")
            continue
        yentry = yaml_by_key[key]
        for col, (yfield, formatter) in field_map.items():
            if col not in header:
                continue
            csv_value = row[header.index(col)]
            expected = formatter(yentry[yfield])
            if csv_value != expected:
                errors.append(f"{csv_path}: row {key} column {col!r}: CSV={csv_value!r} != YAML-derived={expected!r}")
    return errors


def verify_flat_param_table(csv_path, yaml_entry, field_map):
    """
    Check a "parameter, value" CSV (rows keyed by a parameter name in column
    0) against a single flat YAML dict.

    field_map: {csv_parameter_name: (yaml_field, formatter)}
    """
    errors = []
    _, *data_rows = read_csv_rows(csv_path)
    values = {row[0]: row[1] for row in data_rows}
    for param, (yfield, formatter) in field_map.items():
        expected = formatter(yaml_entry[yfield])
        actual = values.get(param)
        if actual != expected:
            errors.append(f"{csv_path}: parameter {param!r}: CSV={actual!r} != YAML-derived={expected!r}")
    return errors


# ---------------------------------------------------------------------------
# HTML-based formula cross-check (promoted from _scratch/extract_full.py)
# ---------------------------------------------------------------------------
def extract_html_tagstripped_range(html_path, start_text, end_text):
    """
    Tag-strip the HTML between the LAST occurrence of start_text and the
    following occurrence of end_text.

    Word's HTML export can repeat heading text (table of contents entries,
    cross-references elsewhere in the document), so a naive first-occurrence
    search can land in the wrong place -- this is what happened when this
    logic was first written ad hoc for TR 38.901 clause 7.4 in Phase 2. Using
    the LAST occurrence of the (usually more distinctive, full-title) start
    marker and the FIRST occurrence of end_text after it matched the real
    body location for §7.4. This is a heuristic proven for that one section,
    not a general HTML/OMML parser -- verify it against a new section's
    actual HTML before trusting it for §7.5/§7.6.
    """
    with open(html_path, "r", errors="ignore") as f:
        content = f.read()
    start = content.rfind(start_text)
    if start == -1:
        raise ValueError(f"{start_text!r} not found in {html_path}")
    end = content.find(end_text, start + len(start_text))
    if end == -1:
        raise ValueError(f"{end_text!r} not found after the start marker in {html_path}")
    chunk = content[start:end]
    text = re.sub(r"<[^>]+>", " ", chunk)
    text = re.sub(r"&nbsp;|&#\d+;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def check_formulas_against_html(html_path, start_text, end_text, formulas):
    """
    Cross-check that every numeric constant appearing in each formula string
    is present in the tag-stripped HTML text for the given section range.
    This is the automated half of the two-source verification used to mark
    §7.4 `verified` -- it doesn't parse the HTML's math markup into a formula
    tree, just confirms none of the numeric constants have silently drifted.

    Returns a list of (formula, missing_numbers) for any formula with a
    number not found in the HTML text; empty list means a clean cross-check.
    """
    text = extract_html_tagstripped_range(html_path, start_text, end_text)
    compact = re.sub(r"\s+", "", text)
    mismatches = []
    for formula in formulas:
        numbers = re.findall(r"\d+\.?\d*", formula)
        missing = [n for n in numbers if n not in compact]
        if missing:
            mismatches.append((formula, missing))
    return mismatches


# ---------------------------------------------------------------------------
# §7.4-specific table configuration (the only processed section so far)
# ---------------------------------------------------------------------------
def _variant_key_normalizer(key):
    scenario, condition, variant = key
    return (scenario, condition, variant or None)


SECTION_7_4_DIR = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models")
SECTION_7_4_YAML_PATH = os.path.join(SECTION_7_4_DIR, "7.4-pathloss.yaml")
SECTION_7_4_TABLES_DIR = os.path.join(SECTION_7_4_DIR, "tables")
SOURCE_HTML = os.path.join(REPO_ROOT, "references", "3gpp-tr38901", "v19.4.0", "38901-j40.html")


def verify_section_7_4():
    errors = []

    with open(SECTION_7_4_YAML_PATH) as f:
        data = yaml.safe_load(f)

    try:
        validated = Section74Data(**data)
    except ValidationError as exc:
        errors.append(f"{SECTION_7_4_YAML_PATH}: schema validation failed:\n{exc}")
        return errors  # downstream checks assume valid structure

    errors += verify_table(
        os.path.join(SECTION_7_4_TABLES_DIR, "table-7.4.1-1.csv"),
        data["pathloss"],
        key_fields=("scenario", "condition", "variant"),
        key_normalizer=_variant_key_normalizer,
        field_map={
            "formula": ("formula", identity),
            "shadow_fading_std_db": ("shadow_fading_std_db", flatten_std),
            "applicability_range": ("applicability_range", identity),
            "notes": ("notes", join_notes),
        },
    )

    errors += verify_table(
        os.path.join(SECTION_7_4_TABLES_DIR, "table-7.4.2-1.csv"),
        data["los_probability"],
        key_fields=("scenario",),
        field_map={
            "formula": ("formula", identity),
            "notes": ("notes", join_notes),
        },
    )

    errors += verify_table(
        os.path.join(SECTION_7_4_TABLES_DIR, "table-7.4.3-1.csv"),
        data["o2i_penetration_loss"]["materials"],
        key_fields=("material",),
        field_map={
            "formula": ("formula", identity),
            "notes": ("notes", join_notes),
        },
    )

    errors += verify_table(
        os.path.join(SECTION_7_4_TABLES_DIR, "table-7.4.3-2.csv"),
        data["o2i_penetration_loss"]["building_models"],
        key_fields=("model",),
        field_map={
            "pl_tw_formula": ("pl_tw_formula", identity),
            "pl_in_formula": ("pl_in_formula", identity),
            "std_p_db": ("std_p_db", lambda v: str(v)),
        },
    )

    single_freq = data["o2i_penetration_loss"]["building_single_frequency_below_6ghz"]
    errors += verify_flat_param_table(
        os.path.join(SECTION_7_4_TABLES_DIR, "table-7.4.3-3.csv"),
        single_freq,
        field_map={
            "PL_tw": ("pl_tw_db", lambda v: f"{v} dB"),
            "PL_in": ("pl_in_formula", identity),
            "sigma_P": ("sigma_p_db", lambda v: f"{v} dB"),
            "sigma_SF": ("sigma_sf_db", lambda v: f"{v} dB ({single_freq['note']})"),
        },
    )

    if os.path.isfile(SOURCE_HTML):
        # Scoped to `pathloss` (Table 7.4.1-1) only. Direct inspection of the
        # HTML confirmed that table's formulas are uniformly genuine OMML
        # text (0 OLEObject / 324 m:oMath in that region) -- a real
        # independent source. Table 7.4.2-1 (los_probability) is a *mix*:
        # 12 OLEObject-embedded formulas (old-style equation objects
        # rendered as .wmz images, no text fallback in docx, html, OR xml)
        # alongside 58 genuine m:oMath ones. Three of the eight
        # los_probability entries (RMa, Indoor-MixedOffice, Indoor-OpenOffice)
        # are among the image-embedded ones -- confirmed by checking that
        # their numeric constants are absent from all three machine-readable
        # exports, not just this one. Running this check against
        # los_probability would produce misleading passes (a formula's
        # digits coincidentally appearing elsewhere in the region) as often
        # as real signal, so it's intentionally excluded here rather than
        # reported as a blanket pass/fail. See CLAUDE.md's references/ notes
        # and the Phase 3 completion report for the full finding -- those
        # three entries currently have single-source (PDF visual) coverage
        # only, which is a real gap flagged for Mehdi to decide on, not
        # something this tool silently papers over.
        mismatches = check_formulas_against_html(
            SOURCE_HTML,
            start_text="Pathloss, LOS probability and penetration modelling",
            end_text="Fast fading model",
            formulas=[row.formula for row in validated.pathloss],
        )
        for formula, missing in mismatches:
            errors.append(f"formula cross-check: numbers {missing} from {formula!r} not found in HTML export")
    else:
        print(f"  (skipping HTML formula cross-check: {SOURCE_HTML} not present locally)")

    return errors


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    print("Discovering processed sections...")
    sections = discover_section_md_files()
    print(f"  found {len(sections)} section file(s): {[os.path.relpath(s, REPO_ROOT) for s in sections]}")

    total_errors = []

    for path in sections:
        with open(path) as f:
            fm_text, _ = split_front_matter(f.read())
        front_matter = yaml.safe_load(fm_text)
        section = front_matter.get("section")
        print(f"\nVerifying section {section} ({os.path.relpath(path, REPO_ROOT)})...")

        if section == "7.4":
            errors = verify_section_7_4()
        else:
            errors = [f"{path}: no verify_tables.py checker registered for section {section!r} yet"]

        if errors:
            for e in errors:
                print(f"  FAIL: {e}")
        else:
            print("  OK")
        total_errors += errors

    print(f"\n{'=' * 60}")
    if total_errors:
        print(f"FAILED: {len(total_errors)} issue(s) across {len(sections)} section(s).")
        return 1
    print(f"PASSED: all checks clean across {len(sections)} section(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
