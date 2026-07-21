"""
Regression guard for TR 38.901 §7.9's values (core sub-clauses 7.9.0-7.9.3:
sensing scenarios, physical-object/RCS model, reference-channel mapping), plus:

- an internal cross-check that §7.9.3's baseline references (Table 7.4.2-1 in
  §7.4, Table B-1 in TR 36.777 Annex B) actually exist in this repo's
  processed data -- the same kind of consistency check Annex B enabled; and
- a *structural* cross-check against references/3gpp-R1-2509126/ (the RAN1 ISAC
  calibration contribution): its spreadsheets are organized by exactly §7.9's
  target-vs-background-channel decomposition and TRP/UE monostatic/bistatic
  sensing modes. Numeric RCS/scenario-size values are calibration *inputs* that
  don't appear in those output-CDF spreadsheets -- that correspondence belongs
  to the deferred §7.9.6 calibration tables -- so this is a coverage/vocabulary
  check, not a numeric value match (which would be forcing a correspondence
  that isn't there).

The RCS/XPR numeric values themselves are three-source verified (docx + PDF +
HTML) and their CSV<->YAML agreement is covered generically by
tools/verify_tables.py's verify_section_7_9(); these tests lock in the
PDF-confirmed baseline and the completeness/partition invariants.
"""
import glob
import os
import re
import sys
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import pytest  # noqa: E402
import yaml  # noqa: E402

RCS2_TARGETS = {
    "UAV with large size", "Human with RCS model 2",
    "Vehicle with single scattering point", "Vehicle with multiple scattering points",
    "AGV with single scattering point", "AGV with multiple scattering points",
}
SCENARIO_FAMILIES = {"UAV", "Automotive", "Human", "AGV", "Objects-creating-hazards"}


# ---------------------------------------------------------------------------
# Completeness
# ---------------------------------------------------------------------------
def test_all_five_scenario_families_present(section_7_9_yaml_data):
    families = {e["scenario_type"] for e in section_7_9_yaml_data["sensing_scenarios"]}
    assert families == SCENARIO_FAMILIES, families


def test_human_scenario_uses_indoor_outdoor_columns(section_7_9_yaml_data):
    human = [e for e in section_7_9_yaml_data["sensing_scenarios"] if e["scenario_type"] == "Human"]
    assert human
    for e in human:
        # Human table has indoor/outdoor values and no single `value`.
        assert e["value"] is None
        assert e["indoor_value"] is not None and e["outdoor_value"] is not None


def test_single_value_scenarios_have_no_indoor_outdoor(section_7_9_yaml_data):
    for e in section_7_9_yaml_data["sensing_scenarios"]:
        if e["scenario_type"] == "Human":
            continue
        assert e["value"] is not None
        assert e["indoor_value"] is None and e["outdoor_value"] is None


def test_rcs_model_1_targets(section_7_9_yaml_data):
    targets = {e["sensing_target"] for e in section_7_9_yaml_data["rcs_model_1"]}
    assert targets == {"UAV with small size", "Human with RCS model 1"}


def test_rcs_model_2_all_six_targets_present(section_7_9_yaml_data):
    targets = {e["target"] for e in section_7_9_yaml_data["rcs_model_2"]}
    assert targets == RCS2_TARGETS


def test_rcs_model_2_scattering_point_counts(section_7_9_yaml_data):
    # UAV-large has 6 aspects (incl. Bottom); human-model2 has 2 (Front/Back);
    # the vehicle/AGV tables have 5 each (4 sides + Roof).
    by_target = {}
    for e in section_7_9_yaml_data["rcs_model_2"]:
        by_target.setdefault(e["target"], []).append(e["scattering_point"])
    assert len(by_target["UAV with large size"]) == 6
    assert set(by_target["Human with RCS model 2"]) == {"Front", "Back"}
    assert len(by_target["Vehicle with single scattering point"]) == 5
    assert len(by_target["AGV with multiple scattering points"]) == 5


def test_xpr_all_four_targets_present(section_7_9_yaml_data):
    assert {e["target"] for e in section_7_9_yaml_data["xpr"]} == {"UAV", "Human", "Vehicle", "AGV"}


def test_reference_channel_models_cover_cases_1_to_13(section_7_9_yaml_data):
    cases = {e["case"] for e in section_7_9_yaml_data["reference_channel_models"]}
    assert cases == {str(i) for i in range(1, 14)}


def test_los_condition_has_case_7_and_9(section_7_9_yaml_data):
    by_case = {}
    for e in section_7_9_yaml_data["los_condition_determination"]:
        by_case.setdefault(e["case"], 0)
        by_case[e["case"]] += 1
    assert by_case == {"7": 2, "9": 4}  # Table 7.9.3-4 has 2 rows, 7.9.3-5 has 4


# ---------------------------------------------------------------------------
# PDF-confirmed sample values (RCS model 2 / model 1 / XPR / k-parameters)
# ---------------------------------------------------------------------------
def test_rcs_model_1_sample_values(section_7_9_yaml_data):
    by_t = {e["sensing_target"]: e for e in section_7_9_yaml_data["rcs_model_1"]}
    assert by_t["UAV with small size"]["lg_sigma_m_dbsm"] == "-12.81"
    assert by_t["UAV with small size"]["sigma_sigmaS_db"] == "3.74"
    assert by_t["Human with RCS model 1"]["lg_sigma_m_dbsm"] == "-1.37"


def test_rcs_model_2_sample_values(section_7_9_yaml_data):
    by_key = {(e["target"], e["scattering_point"]): e for e in section_7_9_yaml_data["rcs_model_2"]}
    # UAV large, Front (Table 7.9.2.1-2)
    front = by_key[("UAV with large size", "Front")]
    assert front["phi_3db_deg"] == "14.19" and front["theta_3db_deg"] == "16.53"
    assert front["lg_sigma_m_dbsm"] == "-5.85" and front["sigma_sigmaS_db"] == "2.50"
    # Human model 2, Front (Table 7.9.2.1-3) -- the large 216.65 value
    assert by_key[("Human with RCS model 2", "Front")]["phi_3db_deg"] == "216.65"
    # Vehicle single, Left (Table 7.9.2.1-4)
    assert by_key[("Vehicle with single scattering point", "Left")]["theta_center_deg"] == "79.70"
    assert by_key[("Vehicle with single scattering point", "Left")]["lg_sigma_m_dbsm"] == "11.25"
    # AGV multiple, Roof (Table 7.9.2.1-7) -- roof has "-" for phi
    roof = by_key[("AGV with multiple scattering points", "Roof")]
    assert roof["phi_center_deg"] == "-" and roof["sigma_max"] == "29.03"


def test_rcs_model_2_roof_and_bottom_have_dash_for_phi(section_7_9_yaml_data):
    # The top-facing scattering points (Roof, Bottom) have no azimuth center/3dB.
    for e in section_7_9_yaml_data["rcs_model_2"]:
        if e["scattering_point"] in ("Roof", "Bottom"):
            assert e["phi_center_deg"] == "-" and e["phi_3db_deg"] == "-"


def test_xpr_sample_values(section_7_9_yaml_data):
    by_t = {e["target"]: e for e in section_7_9_yaml_data["xpr"]}
    assert by_t["UAV"]["mu_xpr_db"] == "13.75" and by_t["UAV"]["sigma_xpr_db"] == "7.07"
    assert by_t["Vehicle"]["mu_xpr_db"] == "21.12"
    assert by_t["AGV"]["sigma_xpr_db"] == "6.85"


def test_rcs_model_2_k_parameters_values(section_7_9_yaml_data):
    by_t = {e["target"]: e for e in section_7_9_yaml_data["rcs_model_2_k_parameters"]}
    assert by_t["UAV with large size"]["k1"] == "6.05" and by_t["UAV with large size"]["k2"] == "1.33"
    assert by_t["Human with RCS model 2"]["k1"] == "0.5714"
    assert by_t["AGV with single/multiple SPSTs"]["k2"] == "1.45"


def test_reference_channel_and_link_samples(section_7_9_yaml_data):
    by_case = {e["case"]: e for e in section_7_9_yaml_data["reference_channel_models"]}
    assert by_case["4"]["tx"] == "TRP" and by_case["4"]["rx"] == "aerial UE"
    assert by_case["9"]["tx"] == "aerial UE" and by_case["9"]["rx"] == "aerial UE"
    tcl = {(e["stx_srx"], e["target"]): e["case"] for e in section_7_9_yaml_data["target_channel_links"]}
    assert tcl[("TRP", "UAV")].startswith("Case 4")
    assert tcl[("Aerial UE", "UAV")].startswith("Case 9")


# ---------------------------------------------------------------------------
# Internal cross-check: §7.9.3 references §7.4 and TR 36.777 Annex B baselines.
# This repo processed those, so we can confirm the baselines actually exist.
# ---------------------------------------------------------------------------
def _load_yaml(rel):
    with open(os.path.join(REPO_ROOT, rel)) as f:
        return yaml.safe_load(f)


def test_los_condition_references_processed_section_7_4_baseline(section_7_9_yaml_data):
    # Tables 7.9.3-4/5 defer to "UMi in Table 7.4.2-1 in TR 38.901" -- the UMi
    # LOS probability this repo processed as §7.4's UMi-StreetCanyon entry.
    referenced = any(
        "Table 7.4.2-1" in e["reference_scenario"] for e in section_7_9_yaml_data["los_condition_determination"]
    )
    assert referenced, "expected a §7.4.2 baseline reference in the LOS-condition tables"
    pl74 = _load_yaml("TR-38.901/v19.4.0/07-channel-models/7.4-pathloss.yaml")
    los_scenarios = {e["scenario"] for e in pl74["los_probability"]}
    assert "UMi-StreetCanyon" in los_scenarios, "§7.4.2 UMi baseline missing from processed data"


def test_los_condition_references_processed_annex_b_baseline(section_7_9_yaml_data):
    # Tables 7.9.3-4/5 also defer to "Table B-1 in TR 36.777" -- Annex B's
    # aerial-UE LOS probability, processed in this repo.
    referenced = any(
        "Table B-1 in TR 36.777" in e["reference_scenario"] for e in section_7_9_yaml_data["los_condition_determination"]
    )
    assert referenced
    annex_b = _load_yaml("TR-36.777/v15.0.0/annex-b-channel-modelling/B-channel-modelling.yaml")
    av_scenarios = {e["scenario"] for e in annex_b["los_probability"]}
    assert {"UMi-AV", "UMa-AV", "RMa-AV"} <= av_scenarios


def test_reference_channel_models_point_at_known_trs(section_7_9_yaml_data):
    # Every reference_tr cell should name at least one real reference TR.
    known = ("TR 38.901", "TR 37.885", "TR 38.858", "TR 36.777", "TR 38.802", "TR 38.808")
    for e in section_7_9_yaml_data["reference_channel_models"]:
        assert any(tr in e["reference_tr"] for tr in known), f"case {e['case']}: no known TR referenced"


# ---------------------------------------------------------------------------
# depends_on well-formedness (§7.9 has same-TR + cross-TR deps)
# ---------------------------------------------------------------------------
SAME_TR = re.compile(r"^\d+(\.\d+)*-[a-z0-9-]+$")
CROSS_TR = re.compile(r"^TR-\d+\.\d+:[A-Za-z0-9.-]+$")


def test_depends_on_is_well_formed_and_targets_exist(section_7_9_front_matter):
    deps = section_7_9_front_matter["depends_on"]
    assert "7.4-pathloss" in deps and "7.5-fast-fading" in deps
    assert "TR-36.777:B-channel-modelling" in deps
    for entry in deps:
        assert SAME_TR.match(entry) or CROSS_TR.match(entry), f"malformed depends_on {entry!r}"
        if ":" in entry:
            tr_dir, stem = entry.split(":")
            matches = []
            for _root, _dirs, files in os.walk(os.path.join(REPO_ROOT, tr_dir)):
                matches += [f for f in files if f == f"{stem}.md"]
            assert matches, f"cross-TR depends_on {entry!r} points at a missing section file"
        else:
            assert os.path.isfile(
                os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", f"{entry}.md")
            ), f"same-TR depends_on {entry!r} points at a missing section file"


# ---------------------------------------------------------------------------
# Structural cross-check against R1-2509126 (references-gated: skips cleanly on
# a fresh clone / CI where references/ isn't present). The calibration
# spreadsheets are organized by §7.9's target/background channel decomposition
# and sensing modes -- a real correspondence the repo is positioned to confirm.
# ---------------------------------------------------------------------------
R1_DIR = os.path.join(REPO_ROOT, "references", "3gpp-R1-2509126")


def _xlsx_shared_strings(path):
    try:
        z = zipfile.ZipFile(path)
        if "xl/sharedStrings.xml" not in z.namelist():
            return []
        xml = z.read("xl/sharedStrings.xml").decode("utf-8", "ignore")
        return [re.sub("<[^>]+>", "", m) for m in re.findall(r"<t[^>]*>.*?</t>", xml)]
    except Exception:
        return []


@pytest.mark.skipif(not os.path.isdir(R1_DIR), reason="references/3gpp-R1-2509126 not present (fresh clone/CI)")
def test_r1_calibration_folders_cover_section_7_9_target_families():
    # The R1-2509126 subfolders enumerate exactly the sensing target families
    # §7.9.1 defines (UAV, Automotive/vehicle, Human, AGV) plus EO and spatial
    # consistency -- a scenario/target-coverage correspondence.
    folders = {os.path.basename(p).lower() for p in glob.glob(os.path.join(R1_DIR, "*")) if os.path.isdir(p)}
    joined = " ".join(folders)
    for token in ("uav", "auto", "human", "agv"):
        assert token in joined, f"expected an R1-2509126 folder for §7.9 target family {token!r}"


@pytest.mark.skipif(not os.path.isdir(R1_DIR), reason="references/3gpp-R1-2509126 not present (fresh clone/CI)")
def test_r1_calibration_uses_section_7_9_target_background_channel_decomposition():
    # §7.9.0/7.9.3/7.9.4.3 decompose the ISAC channel into a *target channel*
    # and a *background channel*, with TRP/UE monostatic/bistatic sensing
    # modes (the Cases in Tables 7.9.3-1/2/3). Confirm at least one calibration
    # spreadsheet is labelled with that exact vocabulary -- the structural
    # correspondence (the numeric RCS/scenario inputs live in the deferred
    # §7.9.6 calibration tables, not these output-CDF sheets).
    files = glob.glob(os.path.join(R1_DIR, "**", "*.xlsx"), recursive=True) + \
        glob.glob(os.path.join(R1_DIR, "**", "*.XLSX"), recursive=True)
    assert files, "expected calibration spreadsheets under references/3gpp-R1-2509126"
    found_target = found_background = found_mode = False
    for f in files:
        strings = " ".join(_xlsx_shared_strings(f)).lower()
        if "target channel" in strings:
            found_target = True
        if "background channel" in strings:
            found_background = True
        if "monostatic" in strings or "bistatic" in strings:
            found_mode = True
        if found_target and found_background and found_mode:
            break
    assert found_target, "no 'target channel' label found in any R1-2509126 spreadsheet"
    assert found_background, "no 'background channel' label found in any R1-2509126 spreadsheet"
    assert found_mode, "no monostatic/bistatic sensing-mode label found in any R1-2509126 spreadsheet"
