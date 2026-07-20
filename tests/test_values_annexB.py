"""
Regression guard for TR 36.777 Annex B's values, plus the internal
cross-check that its baseline references actually match this repo's
processed TR 38.901 data.

Verification reality (see the section .md's verification note): TR 36.777 is
a 2017 document whose equations are image-embedded in every format, so
formula content is PDF-visual single-source (no automated text cross-check
is possible, unlike TR 38.901). These tests therefore lock in the
PDF-visual-read baseline against future drift and check completeness /
structural invariants, plus the genuinely-automatable cross-TR consistency.
"""
import os
import re
import sys

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

EXPECTED_SCENARIOS = {"RMa-AV", "UMa-AV", "UMi-AV"}


def test_all_three_aerial_scenarios_present_in_delta_tables(annex_b_yaml_data):
    for key in ("los_probability", "pathloss", "shadow_fading_std", "fast_fading_model_selection"):
        scenarios = {e["scenario"] for e in annex_b_yaml_data[key]}
        assert scenarios == EXPECTED_SCENARIOS, f"{key}: {scenarios}"


def test_alternative_1_desired_parameter_samples(annex_b_yaml_data):
    # PDF-visual-confirmed sample values from Tables B.1.1-1 / B.1.1-2.
    by_key = {(e["scenario"], e["condition"]): e for e in annex_b_yaml_data["alternative_1_desired_parameters"]}
    assert by_key[("RMa-AV", "LOS")]["desired_k_db"] == "20"
    assert by_key[("RMa-AV", "LOS")]["desired_ds_ns"] == "10"
    assert by_key[("RMa-AV", "NLOS")]["asa_deg"] == "0.5"
    assert by_key[("UMa-AV", "NLOS")]["asa_deg"] == "1"
    assert by_key[("UMa-AV", "LOS")]["zsa_deg"] == "0.1"


def test_alternative_2_covers_all_six_parameters(annex_b_yaml_data):
    # DS/ASA/ASD/ZSA/ZSD for both LOS+NLOS, K for LOS only -> 11 rows per scenario.
    for scenario in ("RMa-AV", "UMa-AV"):
        rows = [e for e in annex_b_yaml_data["alternative_2_modified_parameters"] if e["scenario"] == scenario]
        params = {e["parameter"] for e in rows}
        assert params == {"DS", "ASA", "ASD", "ZSA", "ZSD", "K"}
        assert len(rows) == 11, f"{scenario}: {len(rows)} rows"
        # K is LOS-only in the source table.
        k_conditions = {e["condition"] for e in rows if e["parameter"] == "K"}
        assert k_conditions == {"LOS"}


def test_alternative_2_sample_formulas(annex_b_yaml_data):
    by_key = {(e["scenario"], e["parameter"], e["condition"]): e for e in annex_b_yaml_data["alternative_2_modified_parameters"]}
    assert by_key[("RMa-AV", "DS", "LOS")]["mu"] == r"0.0549\log_{10}(h_{UT}) - 8.0945"
    assert by_key[("UMa-AV", "K", "LOS")]["sigma"] == r"8.158\exp(0.0046 h_{UT})"


def test_delta_tables_have_terrestrial_baseline_and_aerial_rows(annex_b_yaml_data):
    # Each scenario should have at least one "According to ... of [4]"
    # baseline row (low height) and at least one aerial-specific row.
    for e_list, field in [
        (annex_b_yaml_data["los_probability"], "los_probability"),
        (annex_b_yaml_data["pathloss"], "pathloss"),
        (annex_b_yaml_data["shadow_fading_std"], "sf_std"),
    ]:
        for scenario in EXPECTED_SCENARIOS:
            rows = [e for e in e_list if e["scenario"] == scenario]
            values = [r[field] for r in rows]
            assert any("According to" in v for v in values), f"{scenario}: no baseline reference row"
            assert any("According to" not in v and v != "100%" for v in values) or any(v == "100%" for v in values), \
                f"{scenario}: no aerial-specific row"


# ---------------------------------------------------------------------------
# Internal cross-check: Annex B expresses its model as deltas to TR 38.901,
# referencing baseline formulas by name. This repo has processed those very
# TR 38.901 sections (§7.4, §7.5), so we can verify the baselines Annex B
# names actually exist in the committed TR-38.901 data -- a consistency
# check the repo is uniquely positioned to do (finding 2 in the phase plan).
# ---------------------------------------------------------------------------
def _load_tr38901(section_file):
    path = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", section_file)
    with open(path) as f:
        return yaml.safe_load(f)


def test_annex_b_pathloss_baselines_exist_in_processed_tr38901():
    pl74 = _load_tr38901("7.4-pathloss.yaml")
    # Annex B's baseline scenarios map to TR 38.901's RMa/UMa/UMi-StreetCanyon.
    baseline_map = {"RMa-AV": "RMa", "UMa-AV": "UMa", "UMi-AV": "UMi-StreetCanyon"}
    processed = {(e["scenario"], e["condition"]) for e in pl74["pathloss"]}
    for av_scenario, base_scenario in baseline_map.items():
        for condition in ("LOS", "NLOS"):
            assert (base_scenario, condition) in processed, (
                f"Annex B {av_scenario} {condition} references Table 7.4.1-1's {base_scenario} {condition} "
                f"pathloss, but that isn't in the processed §7.4 data"
            )


def test_annex_b_los_probability_baselines_exist_in_processed_tr38901():
    pl74 = _load_tr38901("7.4-pathloss.yaml")
    processed = {e["scenario"] for e in pl74["los_probability"]}
    for base_scenario in ("RMa", "UMa", "UMi-StreetCanyon"):
        assert base_scenario in processed, f"§7.4.2 baseline {base_scenario} missing from processed data"


def test_annex_b_fast_fading_references_processed_section_7_5():
    # Table B-4 and the B.1.x alternatives all defer to "Section 7.5 of [4]"
    # for the baseline fast fading model, which this repo processed as §7.5.
    section_75 = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", "7.5-fast-fading.yaml")
    assert os.path.isfile(section_75), "Annex B defers to §7.5 but §7.5 isn't processed"


# ---------------------------------------------------------------------------
# Cross-TR depends_on: this is the first section depending on a *different*
# TR's section. Annex B introduces the TR-qualified form "TR-38.901:7.4-...".
# ---------------------------------------------------------------------------
SAME_TR_DEPENDS_ON = re.compile(r"^\d+(\.\d+)*-[a-z0-9-]+$")
CROSS_TR_DEPENDS_ON = re.compile(r"^TR-\d+\.\d+:\d+(\.\d+)*-[a-z0-9-]+$")


def test_annex_b_depends_on_uses_well_formed_cross_tr_ids(annex_b_front_matter):
    depends_on = annex_b_front_matter["depends_on"]
    assert isinstance(depends_on, list) and depends_on
    for entry in depends_on:
        assert SAME_TR_DEPENDS_ON.match(entry) or CROSS_TR_DEPENDS_ON.match(entry), (
            f"depends_on entry {entry!r} is neither a same-TR section id nor a well-formed "
            "cross-TR 'TR-<number>:<section-id>' reference"
        )
    # Annex B specifically depends on the two processed TR 38.901 sections.
    assert "TR-38.901:7.4-pathloss" in depends_on
    assert "TR-38.901:7.5-fast-fading" in depends_on


def test_cross_tr_depends_on_targets_are_processed_sections(annex_b_front_matter):
    # A cross-TR depends_on should point at a section file that actually
    # exists in the repo (catches a typo'd TR dir or section stem).
    for entry in annex_b_front_matter["depends_on"]:
        m = CROSS_TR_DEPENDS_ON.match(entry)
        if not m:
            continue
        tr_dir, section_stem = entry.split(":")
        matches = []
        for root, _dirs, files in os.walk(os.path.join(REPO_ROOT, tr_dir)):
            matches += [f for f in files if f == f"{section_stem}.md"]
        assert matches, f"cross-TR depends_on {entry!r} points at a section file that doesn't exist"
