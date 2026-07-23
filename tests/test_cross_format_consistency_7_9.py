"""
Cross-file consistency for TR 38.901 §7.9 (core 7.9.0-7.9.3).

CSV<->YAML agreement for every table is covered generically by
tools/verify_tables.py's verify_section_7_9() (exercised end-to-end via
test_verify_tables.py). This file guards the *inline Markdown* tables in the
section .md against drifting from the YAML.

The numeric RCS/XPR tables are in the same orientation as the CSVs, so each
YAML row reconstructs to an exact inline-table row substring. The scenario and
reference/mapping tables carry multi-line cells rendered with <br> in the .md,
so those are checked by label/token presence rather than exact-row match.
"""


def _md_row(cells):
    return "| " + " | ".join(cells) + " |"


# ---------------------------------------------------------------------------
# RCS model 1 / model 2 / XPR / k-parameters: exact inline rows
# ---------------------------------------------------------------------------
def test_rcs_model_1_rows_present_in_markdown(section_7_9_raw_text, section_7_9_yaml_data):
    for e in section_7_9_yaml_data["rcs_model_1"]:
        row = _md_row([e["sensing_target"], e["lg_sigma_m_dbsm"], e["sigma_sigmaS_db"]])
        assert row in section_7_9_raw_text, f"missing RCS model 1 row in .md: {row}"


RCS2_ORDER = ["scattering_point", "phi_center_deg", "phi_3db_deg", "theta_center_deg",
              "theta_3db_deg", "g_max", "sigma_max", "range_theta_deg", "range_phi_deg",
              "lg_sigma_m_dbsm", "sigma_sigmaS_db"]


def test_rcs_model_2_rows_present_in_markdown(section_7_9_raw_text, section_7_9_yaml_data):
    for e in section_7_9_yaml_data["rcs_model_2"]:
        row = _md_row([e[f] for f in RCS2_ORDER])
        assert row in section_7_9_raw_text, f"missing RCS model 2 row in .md ({e['target']}/{e['scattering_point']})"


def test_xpr_rows_present_in_markdown(section_7_9_raw_text, section_7_9_yaml_data):
    for e in section_7_9_yaml_data["xpr"]:
        row = _md_row([e["target"], e["mu_xpr_db"], e["sigma_xpr_db"]])
        assert row in section_7_9_raw_text, f"missing XPR row in .md: {row}"


def test_k_parameters_present_in_markdown(section_7_9_raw_text, section_7_9_yaml_data):
    for e in section_7_9_yaml_data["rcs_model_2_k_parameters"]:
        row = _md_row([e["target"], e["k1"], e["k2"]])
        assert row in section_7_9_raw_text, f"missing k-parameter row in .md: {row}"


# ---------------------------------------------------------------------------
# LOS-condition applicability ranges: exact cell text (same orientation)
# ---------------------------------------------------------------------------
def test_los_condition_cells_present_in_markdown(section_7_9_raw_text, section_7_9_yaml_data):
    for e in section_7_9_yaml_data["los_condition_determination"]:
        assert e["reference_scenario"] in section_7_9_raw_text, f"missing reference_scenario: {e['reference_scenario'][:40]}"
        assert e["applicability_range"] in section_7_9_raw_text, f"missing applicability_range: {e['applicability_range'][:40]}"


# ---------------------------------------------------------------------------
# Reference/mapping tables: case labels present as inline rows
# ---------------------------------------------------------------------------
def test_reference_channel_model_cases_present_in_markdown(section_7_9_raw_text, section_7_9_yaml_data):
    for e in section_7_9_yaml_data["reference_channel_models"]:
        # The Case/Tx/Rx prefix of each inline row must be present.
        prefix = f"| {e['case']} | {e['tx']} | {e['rx']} |"
        assert prefix in section_7_9_raw_text, f"missing reference-channel row prefix: {prefix}"


def test_channel_link_rows_present_in_markdown(section_7_9_raw_text, section_7_9_yaml_data):
    for e in section_7_9_yaml_data["target_channel_links"]:
        assert _md_row([e["stx_srx"], e["target"], e["case"]]) in section_7_9_raw_text
    for e in section_7_9_yaml_data["background_channel_links"]:
        assert _md_row([e["stx_srx"], e["srx_stx"], e["case"]]) in section_7_9_raw_text


# ---------------------------------------------------------------------------
# Scenario tables: every parameter label present (multi-line values use <br>)
# ---------------------------------------------------------------------------
def test_scenario_parameter_labels_present_in_markdown(section_7_9_raw_text, section_7_9_yaml_data):
    for e in section_7_9_yaml_data["sensing_scenarios"]:
        assert f"| {e['parameter']} |" in section_7_9_raw_text, f"missing scenario parameter row: {e['parameter']}"


# ---------------------------------------------------------------------------
# Standalone equations live only in the .md (per convention) -- confirm present
# ---------------------------------------------------------------------------
def test_all_five_equations_present_in_markdown(section_7_9_raw_text):
    for n in range(1, 6):
        assert f"<!-- Eq. 7.9.2-{n} -->" in section_7_9_raw_text, f"missing equation comment 7.9.2-{n}"
    # A couple of distinctive equation fragments to guard against a blanked $$ block.
    assert r"\mu_{\sigma_{S\_dB}}" in section_7_9_raw_text
    assert "CPM_{sp,i}" in section_7_9_raw_text


# ---------------------------------------------------------------------------
# 7.9.4 / 7.9.5 / 7.9.6 (continuation)
# ---------------------------------------------------------------------------
BCP_ORDER = ["scenario", "alpha_d", "beta_d", "c_d", "alpha_h", "beta_h", "c_h"]


def test_background_channel_rows_present_in_markdown(section_7_9_raw_text, section_7_9_yaml_data):
    for e in section_7_9_yaml_data["background_channel_params"]:
        row = _md_row([e[f] for f in BCP_ORDER])
        assert row in section_7_9_raw_text, f"missing background-channel row in .md ({e['sensing_mode']}/{e['scenario']})"


def test_spatial_consistency_rows_present_in_markdown(section_7_9_raw_text, section_7_9_yaml_data):
    for e in section_7_9_yaml_data["spatial_consistency_correlation"]:
        assert _md_row([e["parameter"], e["correlation_type"]]) in section_7_9_raw_text


def test_calibration_parameter_labels_present_in_markdown(section_7_9_raw_text, section_7_9_yaml_data):
    for e in section_7_9_yaml_data["calibration_assumptions"]:
        assert f"| {e['parameter']} |" in section_7_9_raw_text, f"missing calibration parameter row: {e['parameter']}"


def test_continuation_equations_present_in_markdown(section_7_9_raw_text):
    for n in range(1, 17):  # 7.9.4-1 .. 7.9.4-16
        assert f"<!-- Eq. 7.9.4-{n} -->" in section_7_9_raw_text, f"missing equation comment 7.9.4-{n}"
    for n in range(1, 15):  # 7.9.5-1 .. 7.9.5-14
        assert f"<!-- Eq. 7.9.5-{n} -->" in section_7_9_raw_text, f"missing equation comment 7.9.5-{n}"
    # 7.9.5-15 is split into a/b in the source.
    assert "<!-- Eq. 7.9.5-15a -->" in section_7_9_raw_text
    assert "<!-- Eq. 7.9.5-15b -->" in section_7_9_raw_text
    # Distinctive fragments guarding against blanked $$ blocks.
    assert "H_{u,s}^{ISAC}" in section_7_9_raw_text     # Eq. 7.9.4-16
    assert "CPM_{EO}" in section_7_9_raw_text            # Eq. 7.9.5-10
