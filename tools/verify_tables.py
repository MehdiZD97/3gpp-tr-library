"""
Generalized CSV <-> YAML verification, promoted from the per-table checks
hand-written in tests/test_cross_format_consistency.py during Phase 2.

Two generic checkers cover the real data shapes found in this repo so far:

- `verify_table()` for "list of entities keyed by one or more fields" tables
  (e.g. Table 7.4.1-1: one row per scenario/condition/variant).
- `verify_flat_param_table()` for "parameter, value" tables matched against
  a single YAML dict (e.g. Table 7.4.3-3).

These are deliberately two functions, not one contorted abstraction --
`o2i_penetration_loss` alone has four different sub-shapes, and forcing all
of them through one generic shape would be a worse abstraction than two
honest ones.

Also home to `check_formulas_against_html()`, the HTML-based formula
cross-check. For TR 38.901 the docx's formula-bearing table cells return
empty text (they're embedded equation objects), but the HTML export carries
the same equations as recoverable OMML text -- so the HTML is a genuine
second source for formula content, not just a structural tiebreaker.

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
from tr_api.models import AnnexBData, ChannelModelParameterEntry, Section74Data, Section75Data  # noqa: E402


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


def html_region_has_text_formulas(html_path, start_text, end_text):
    """
    Return True if the HTML region between start_text and end_text carries
    equations as recoverable OMML *text* (Word's `<m:oMath>` markup), False
    if they're image-embedded (old-style OLE objects rendered as .png/.wmz).

    This is what makes the formula cross-check meaningful for one TR and not
    another: TR 38.901 (2026) exports OMML text, so `check_formulas_against_html`
    genuinely re-reads every formula constant. TR 36.777 (2017) renders every
    equation as an image (0 OMML, hundreds of image refs, confirmed on-disk),
    so running the numeric cross-check there would report every formula digit
    as "missing" -- a false failure. Callers use this to *skip* the cross-check
    for an image-embedded region rather than fail it or fake a pass.
    """
    with open(html_path, "r", errors="ignore") as f:
        content = f.read()
    start = content.rfind(start_text)
    end = content.find(end_text, start + len(start_text)) if start != -1 else -1
    region = content[start:end] if (start != -1 and end != -1) else content
    return "m:oMath" in region


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
        # reported as a blanket pass/fail -- those three entries currently
        # have single-source (PDF visual) coverage only, a real gap this
        # tool doesn't silently paper over.
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
# §7.5-specific table configuration
#
# Every §7.5 CSV/YAML shape turned out to fit the existing verify_table()
# checker -- including Table 7.5-6, the master large-scale-parameter table
# that looked at first like a "cross-correlation matrix" shape needing a
# third checker. It didn't, because the
# YAML/CSV represent it as one row per (scenario, condition) with 49 named
# fields -- a list-of-entities shape, same as Table 7.4.1-1 -- rather than
# as a literal 2D matrix. That's a deliberate design choice (it's also the
# more useful shape for tr_api: one call returns every parameter for a given
# scenario/condition), not an accident that happened to dodge the need for
# new tooling. The only place the "matrix" shape actually shows up is the
# *inline Markdown* table, which transposes to parameter-rows x
# scenario-columns to stay readable -- that comparison is bespoke (see
# tests/test_cross_format_consistency.py), not a verify_tables.py checker.
# ---------------------------------------------------------------------------
SECTION_7_5_DIR = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models")
SECTION_7_5_YAML_PATH = os.path.join(SECTION_7_5_DIR, "7.5-fast-fading.yaml")
SECTION_7_5_TABLES_DIR = os.path.join(SECTION_7_5_DIR, "tables")

# Human-readable row labels for Table 7.5-6's 49 parameter fields, in the
# TR's own row order -- the source of truth for the *transposed* inline
# Markdown table in 7.5-fast-fading.md (parameter rows x scenario/condition
# columns; see that file's own note on why it's transposed relative to the
# CSV). Lives here, not just in the extraction script that generated the
# committed files, so tests/test_cross_format_consistency_7_5.py can
# reproduce the mapping without depending on gitignored _scratch/ content.
PARAM_LABELS = {
    "mu_lgDS": "Delay spread (DS): mean of log10(DS/1s)",
    "sigma_lgDS": "Delay spread (DS): std of log10(DS/1s)",
    "mu_lgASD": "AOD spread (ASD): mean of log10(ASD/1deg)",
    "sigma_lgASD": "AOD spread (ASD): std of log10(ASD/1deg)",
    "mu_lgASA": "AOA spread (ASA): mean of log10(ASA/1deg)",
    "sigma_lgASA": "AOA spread (ASA): std of log10(ASA/1deg)",
    "mu_lgZSA": "ZOA spread (ZSA): mean of log10(ZSA/1deg)",
    "sigma_lgZSA": "ZOA spread (ZSA): std of log10(ZSA/1deg)",
    "sigma_SF": "Shadow fading (SF) std [dB]",
    "mu_K": "K-factor (K) mean [dB]",
    "sigma_K": "K-factor (K) std [dB]",
    "corr_ASD_DS": "Cross-correlation: ASD vs DS",
    "corr_ASA_DS": "Cross-correlation: ASA vs DS",
    "corr_ASA_SF": "Cross-correlation: ASA vs SF",
    "corr_ASD_SF": "Cross-correlation: ASD vs SF",
    "corr_DS_SF": "Cross-correlation: DS vs SF",
    "corr_ASD_ASA": "Cross-correlation: ASD vs ASA",
    "corr_ASD_K": "Cross-correlation: ASD vs K",
    "corr_ASA_K": "Cross-correlation: ASA vs K",
    "corr_DS_K": "Cross-correlation: DS vs K",
    "corr_SF_K": "Cross-correlation: SF vs K",
    "corr_ZSD_SF": "Cross-correlation: ZSD vs SF",
    "corr_ZSA_SF": "Cross-correlation: ZSA vs SF",
    "corr_ZSD_K": "Cross-correlation: ZSD vs K",
    "corr_ZSA_K": "Cross-correlation: ZSA vs K",
    "corr_ZSD_DS": "Cross-correlation: ZSD vs DS",
    "corr_ZSA_DS": "Cross-correlation: ZSA vs DS",
    "corr_ZSD_ASD": "Cross-correlation: ZSD vs ASD",
    "corr_ZSA_ASD": "Cross-correlation: ZSA vs ASD",
    "corr_ZSD_ASA": "Cross-correlation: ZSD vs ASA",
    "corr_ZSA_ASA": "Cross-correlation: ZSA vs ASA",
    "corr_ZSD_ZSA": "Cross-correlation: ZSD vs ZSA",
    "delay_scaling_parameter_r_tau": "Delay scaling parameter r_tau",
    "mu_XPR": "XPR mean [dB]",
    "sigma_XPR": "XPR std [dB]",
    "number_of_clusters": "Number of clusters N",
    "number_of_rays_per_cluster": "Number of rays per cluster M",
    "cluster_DS_ns": "Cluster DS (c_DS) [ns]",
    "cluster_ASD_deg": "Cluster ASD (c_ASD) [deg]",
    "cluster_ASA_deg": "Cluster ASA (c_ASA) [deg]",
    "cluster_ZSA_deg": "Cluster ZSA (c_ZSA) [deg]",
    "per_cluster_shadowing_std_zeta_db": "Per-cluster shadowing std zeta [dB]",
    "corr_distance_DS_m": "Correlation distance (horizontal plane): DS [m]",
    "corr_distance_ASD_m": "Correlation distance (horizontal plane): ASD [m]",
    "corr_distance_ASA_m": "Correlation distance (horizontal plane): ASA [m]",
    "corr_distance_SF_m": "Correlation distance (horizontal plane): SF [m]",
    "corr_distance_K_m": "Correlation distance (horizontal plane): K [m]",
    "corr_distance_ZSA_m": "Correlation distance (horizontal plane): ZSA [m]",
    "corr_distance_ZSD_m": "Correlation distance (horizontal plane): ZSD [m]",
}

_CHANNEL_MODEL_PARAM_FIELDS = [
    f for f in ChannelModelParameterEntry.model_fields if f not in ("scenario", "condition")
]
assert set(_CHANNEL_MODEL_PARAM_FIELDS) == set(PARAM_LABELS), "PARAM_LABELS drifted from ChannelModelParameterEntry"

_ZSD_ZOD_SCENARIO_TABLES = {
    "UMa": "7.5-7", "UMi-StreetCanyon": "7.5-8", "RMa": "7.5-9",
    "Indoor-Office": "7.5-10", "InF": "7.5-11", "SMa": "7.5-12",
}


def verify_section_7_5():
    errors = []

    with open(SECTION_7_5_YAML_PATH) as f:
        data = yaml.safe_load(f)

    try:
        validated = Section75Data(**data)
    except ValidationError as exc:
        errors.append(f"{SECTION_7_5_YAML_PATH}: schema validation failed:\n{exc}")
        return errors

    errors += verify_table(
        # Keyed on "notation", not "parameter": Table 7.5-1 legitimately
        # repeats the same prose label for two pairs of rows (the Rx/Tx
        # field-pattern entries differ only by their theta/phi notation,
        # e.g. two rows both labelled "Receive antenna element u field
        # pattern..." for F_rx,u,theta and F_rx,u,phi) -- "parameter" alone
        # isn't a unique key here, confirmed directly against the source.
        os.path.join(SECTION_7_5_TABLES_DIR, "table-7.5-1.csv"),
        data["notations"], key_fields=("notation",),
        field_map={"parameter": ("parameter", identity)},
    )
    errors += verify_table(
        os.path.join(SECTION_7_5_TABLES_DIR, "table-7.5-2.csv"),
        data["scaling_factors_aoa_aod_generation"], key_fields=("num_clusters",),
        field_map={"c_phi_nlos": ("c_phi_nlos", lambda v: str(v))},
        key_normalizer=lambda k: (int(k[0]),),
    )
    errors += verify_table(
        os.path.join(SECTION_7_5_TABLES_DIR, "table-7.5-3.csv"),
        data["ray_offset_angles"], key_fields=("ray_numbers",),
        field_map={"offset_angle": ("offset_angle", lambda v: str(v))},
    )
    errors += verify_table(
        os.path.join(SECTION_7_5_TABLES_DIR, "table-7.5-4.csv"),
        data["scaling_factors_zoa_zod_generation"], key_fields=("num_clusters",),
        field_map={"c_theta_nlos": ("c_theta_nlos", lambda v: str(v))},
        key_normalizer=lambda k: (int(k[0]),),
    )
    errors += verify_table(
        os.path.join(SECTION_7_5_TABLES_DIR, "table-7.5-5.csv"),
        data["sub_cluster_info"], key_fields=("sub_cluster",),
        field_map={
            "mapping_to_rays": ("mapping_to_rays", identity),
            "power_fraction": ("power_fraction", identity),
            "delay_offset": ("delay_offset", identity),
        },
        key_normalizer=lambda k: (int(k[0]),),
    )
    errors += verify_table(
        os.path.join(SECTION_7_5_TABLES_DIR, "table-7.5-6.csv"),
        data["channel_model_parameters"], key_fields=("scenario", "condition"),
        field_map={f: (f, identity) for f in _CHANNEL_MODEL_PARAM_FIELDS},
    )
    for scenario, tr_number in _ZSD_ZOD_SCENARIO_TABLES.items():
        errors += verify_table(
            os.path.join(SECTION_7_5_TABLES_DIR, f"table-{tr_number}.csv"),
            data["zsd_zod_offset_parameters"][scenario]["entries"], key_fields=("condition",),
            field_map={
                "mu_lgZSD": ("mu_lgZSD", identity),
                "sigma_lgZSD": ("sigma_lgZSD", identity),
                "mu_offset_ZOD": ("mu_offset_ZOD", identity),
            },
        )

    if os.path.isfile(SOURCE_HTML):
        # Every field on every channel_model_parameters entry, cross-checked
        # against the tag-stripped HTML the same way §7.4's pathloss table
        # is -- confirmed clean (0/826 missing) during Phase 4's extraction.
        # Unlike §7.4.2, direct inspection of this region found no
        # OLE/.wmz-only cells among the *table* data (a handful exist in the
        # 12-step procedure's standalone equations, which aren't YAML data
        # and so aren't cross-checked here), so nothing is excluded.
        formulas = [
            getattr(entry, f) for entry in validated.channel_model_parameters for f in _CHANNEL_MODEL_PARAM_FIELDS
        ]
        mismatches = check_formulas_against_html(
            SOURCE_HTML,
            start_text="The radio channel realizations are created",
            end_text="7.6.0",
            formulas=formulas,
        )
        for formula, missing in mismatches:
            errors.append(f"formula cross-check: numbers {missing} from {formula!r} not found in HTML export")
    else:
        print(f"  (skipping HTML formula cross-check: {SOURCE_HTML} not present locally)")

    return errors


# ---------------------------------------------------------------------------
# TR 36.777 Annex B configuration
#
# Every Annex B CSV/YAML pair fits the existing verify_table() list-of-
# entities checker, so no new checker shape is needed here (same outcome as
# §7.5). The two-part split tables (B.1.1-1/-2, B.1.2-1/-2) share a flat YAML
# list distinguished by scenario -- filtered per CSV below, the same way
# §7.5's per-scenario ZSD/ZOD tables are handled.
#
# The HTML formula cross-check does NOT apply to this TR: TR 36.777 (2017)
# renders every equation as an image (0 OMML), so it's skipped via
# html_region_has_text_formulas() rather than run and false-failed. Formula
# content here is PDF-visual single-source (see the section .md).
# ---------------------------------------------------------------------------
ANNEX_B_DIR = os.path.join(REPO_ROOT, "TR-36.777", "v15.0.0", "annex-b-channel-modelling")
ANNEX_B_YAML_PATH = os.path.join(ANNEX_B_DIR, "B-channel-modelling.yaml")
ANNEX_B_TABLES_DIR = os.path.join(ANNEX_B_DIR, "tables")
ANNEX_B_SOURCE_HTML = os.path.join(REPO_ROOT, "references", "3gpp-tr36777", "v15.0.0", "36777-f00_1.html")

_ALT1_SCENARIO_TABLES = {"RMa-AV": "B.1.1-1", "UMa-AV": "B.1.1-2"}
_ALT2_SCENARIO_TABLES = {"RMa-AV": "B.1.2-1", "UMa-AV": "B.1.2-2"}


def verify_annex_b():
    errors = []

    with open(ANNEX_B_YAML_PATH) as f:
        data = yaml.safe_load(f)

    try:
        AnnexBData(**data)
    except ValidationError as exc:
        errors.append(f"{ANNEX_B_YAML_PATH}: schema validation failed:\n{exc}")
        return errors

    errors += verify_table(
        os.path.join(ANNEX_B_TABLES_DIR, "table-B-1.csv"),
        data["los_probability"], key_fields=("scenario", "height_range"),
        field_map={"los_probability": ("los_probability", identity), "notes": ("notes", join_notes)},
    )
    errors += verify_table(
        os.path.join(ANNEX_B_TABLES_DIR, "table-B-2.csv"),
        data["pathloss"], key_fields=("scenario", "condition", "height_range"),
        field_map={"pathloss": ("pathloss", identity), "notes": ("notes", join_notes)},
    )
    errors += verify_table(
        os.path.join(ANNEX_B_TABLES_DIR, "table-B-3.csv"),
        data["shadow_fading_std"], key_fields=("scenario", "condition", "height_range"),
        field_map={"sf_std": ("sf_std", identity)},
    )
    errors += verify_table(
        os.path.join(ANNEX_B_TABLES_DIR, "table-B-4.csv"),
        data["fast_fading_model_selection"], key_fields=("scenario", "height_range"),
        field_map={"model": ("model", identity)},
    )
    for scenario, tr_number in _ALT1_SCENARIO_TABLES.items():
        rows = [e for e in data["alternative_1_desired_parameters"] if e["scenario"] == scenario]
        errors += verify_table(
            os.path.join(ANNEX_B_TABLES_DIR, f"table-{tr_number}.csv"),
            rows, key_fields=("scenario", "condition"),
            field_map={f: (f, identity) for f in ("asa_deg", "asd_deg", "zsa_deg", "zsd_deg", "desired_k_db", "desired_ds_ns")},
        )
    for scenario, tr_number in _ALT2_SCENARIO_TABLES.items():
        rows = [e for e in data["alternative_2_modified_parameters"] if e["scenario"] == scenario]
        errors += verify_table(
            os.path.join(ANNEX_B_TABLES_DIR, f"table-{tr_number}.csv"),
            rows, key_fields=("scenario", "parameter", "condition"),
            field_map={"mu": ("mu", identity), "sigma": ("sigma", identity)},
        )

    if os.path.isfile(ANNEX_B_SOURCE_HTML):
        if html_region_has_text_formulas(ANNEX_B_SOURCE_HTML, "Channel modelling details", "Calibration results and RSRP"):
            print("  (unexpected: TR 36.777 Annex B HTML has OMML text formulas -- formula cross-check would apply)")
        else:
            print("  (skipping HTML formula cross-check: TR 36.777 renders equations as images, "
                  "no text formula source -- formula content is PDF-visual single-source)")
    else:
        print(f"  (skipping HTML formula cross-check: {ANNEX_B_SOURCE_HTML} not present locally)")

    return errors


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    print("Discovering processed sections...")
    sections = discover_section_md_files()
    print(f"  found {len(sections)} section file(s): {[os.path.relpath(s, REPO_ROOT) for s in sections]}")

    total_errors = []

    # Keyed on (tr, section), not section alone: a second TR could reuse a
    # clause number (e.g. TR 36.777 also has a §7.x), so dispatching on the
    # section string by itself wouldn't stay unambiguous as more TRs land.
    checkers = {
        ("TR 38.901", "7.4"): verify_section_7_4,
        ("TR 38.901", "7.5"): verify_section_7_5,
        ("TR 36.777", "Annex B"): verify_annex_b,
    }

    for path in sections:
        with open(path) as f:
            fm_text, _ = split_front_matter(f.read())
        front_matter = yaml.safe_load(fm_text)
        tr = front_matter.get("tr")
        section = front_matter.get("section")
        print(f"\nVerifying {tr} {section} ({os.path.relpath(path, REPO_ROOT)})...")

        checker = checkers.get((tr, section))
        if checker is not None:
            errors = checker()
        else:
            errors = [f"{path}: no verify_tables.py checker registered for {tr} {section!r} yet"]

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
