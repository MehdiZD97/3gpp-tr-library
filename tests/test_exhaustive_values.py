"""
Exhaustive value coverage (Phase 9, Part 1 Task 1) for the big finite tables.

Two complementary guarantees, stated honestly:

1. **Structural exhaustiveness (every cell):** the accessor's returned value
   equals the committed YAML for *every* field of *every* row -- combined with
   verify_tables.py (CSV<->YAML, every cell) and test_invariants.py (value cells
   <-> inline .md), this means any single-representation drift, and any
   two-representation coordinated drift, in any cell fails a test.

2. **Literal anchors (independently pinned):** a hand-embedded snapshot of
   selected rows/columns catches the (rare) all-three-coordinated drift at
   anchored points. For §7.5's 780-cell Table 7.5-6 -- too large to pin every
   literal by hand -- the anchors are one full parameter row (number_of_clusters
   across all 16 columns) and one full scenario column (UMa/LOS, all 49 params),
   so every column and every parameter is pinned to a verified value at least
   once. §7.9's RCS/XPR tables are finite and three-source-verified, so those
   are pinned more completely.

These values were verified in each section's own phase (see each .md's
`verified_against`); this file guards against future drift.
"""
import os

import pytest
import yaml
from tr_api import introspect, tr36777, tr38901

_CH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "TR-38.901", "v19.4.0", "07-channel-models",
)
def _load(name):
    with open(os.path.join(_CH, name)) as f:
        return yaml.safe_load(f)


_D75 = _load("7.5-fast-fading.yaml")
_D79 = _load("7.9-isac-channel-model.yaml")

_CMP_FIELDS = [k for k in _D75["channel_model_parameters"][0] if k not in ("scenario", "condition")]
_CMP_KEYS = [(e["scenario"], e["condition"]) for e in _D75["channel_model_parameters"]]
_RCS2_KEYS = [(e["target"], e["scattering_point"]) for e in _D79["rcs_model_2"]]


# ---------------------------------------------------------------------------
# §7.5 Table 7.5-6 -- exhaustive accessor <-> YAML for all 16 x 49 cells.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scenario,condition", _CMP_KEYS, ids=[f"{s}-{c}" for s, c in _CMP_KEYS])
def test_channel_model_parameters_accessor_matches_yaml_for_every_field(scenario, condition):
    entry = tr38901.section("7.5").channel_model_parameters(scenario=scenario, condition=condition)
    yaml_row = next(
        e for e in _D75["channel_model_parameters"] if e["scenario"] == scenario and e["condition"] == condition
    )
    for field in _CMP_FIELDS:
        assert getattr(entry, field) == yaml_row[field], f"{scenario}/{condition} field {field} drifted"


# --- Literal anchors: one full row across 16 columns, one full column across 49 params. ---
NUMBER_OF_CLUSTERS_ROW = {
    ("UMi - Street Canyon", "LOS"): "12", ("UMi - Street Canyon", "NLOS"): "19",
    ("UMi - Street Canyon", "O2I"): "12", ("UMa", "LOS"): "12", ("UMa", "NLOS"): "20",
    ("UMa", "O2I"): "12", ("RMa", "LOS"): "11", ("RMa", "NLOS"): "10", ("RMa", "O2I"): "10",
    ("Indoor-Office", "LOS"): "15", ("Indoor-Office", "NLOS"): "19", ("InF", "LOS"): "25",
    ("InF", "NLOS"): "25", ("SMa", "LOS"): "15", ("SMa", "NLOS"): "14", ("SMa", "O2I"): "14",
}

UMA_LOS_COLUMN = {
    "mu_lgDS": "-7.067 - 0.0794 log10(fc), see note 8", "sigma_lgDS": "0.57 + 0.026 log10(fc), see note 8",
    "mu_lgASD": "0.92, see note 8", "sigma_lgASD": "0.31, see note 8", "mu_lgASA": "1.76, see note 8",
    "sigma_lgASA": "0.19, see note 8", "mu_lgZSA": "0.96 see note 8", "sigma_lgZSA": "0.15 see note 8",
    "sigma_SF": "See Table 7.4.1-1", "mu_K": "9", "sigma_K": "3.5", "corr_ASD_DS": "0.4", "corr_ASA_DS": "0.8",
    "corr_ASA_SF": "-0.5", "corr_ASD_SF": "-0.5", "corr_DS_SF": "-0.4", "corr_ASD_ASA": "0", "corr_ASD_K": "0",
    "corr_ASA_K": "-0.2", "corr_DS_K": "-0.4", "corr_SF_K": "0", "corr_ZSD_SF": "0", "corr_ZSA_SF": "-0.8",
    "corr_ZSD_K": "0", "corr_ZSA_K": "0", "corr_ZSD_DS": "-0.2", "corr_ZSA_DS": "0", "corr_ZSD_ASD": "0.5",
    "corr_ZSA_ASD": "0", "corr_ZSD_ASA": "-0.3", "corr_ZSA_ASA": "0.4", "corr_ZSD_ZSA": "0",
    "delay_scaling_parameter_r_tau": "2.5", "mu_XPR": "8", "sigma_XPR": "4", "number_of_clusters": "12",
    "number_of_rays_per_cluster": "20", "cluster_DS_ns": "max(0.25, 6.5622 -3.4084 log10(fc))",
    "cluster_ASD_deg": "3.58, see note 8", "cluster_ASA_deg": "11", "cluster_ZSA_deg": "7",
    "per_cluster_shadowing_std_zeta_db": "3", "corr_distance_DS_m": "30", "corr_distance_ASD_m": "18",
    "corr_distance_ASA_m": "15", "corr_distance_SF_m": "37", "corr_distance_K_m": "12",
    "corr_distance_ZSA_m": "15", "corr_distance_ZSD_m": "15",
}


def test_number_of_clusters_full_row_literal_anchor():
    # Anchors every one of the 16 scenario/condition columns to a verified value.
    entry_by_key = {(e["scenario"], e["condition"]): e for e in _D75["channel_model_parameters"]}
    assert set(entry_by_key) == set(NUMBER_OF_CLUSTERS_ROW)
    for key, expected in NUMBER_OF_CLUSTERS_ROW.items():
        assert entry_by_key[key]["number_of_clusters"] == expected, f"{key}: number_of_clusters drifted"


def test_uma_los_full_column_literal_anchor():
    # Anchors all 49 parameters (for the UMa/LOS column) to verified values.
    entry = tr38901.section("7.5").channel_model_parameters(scenario="UMa", condition="LOS")
    assert set(UMA_LOS_COLUMN) == set(_CMP_FIELDS)
    for field, expected in UMA_LOS_COLUMN.items():
        assert getattr(entry, field) == expected, f"UMa/LOS {field} drifted"


# ---------------------------------------------------------------------------
# §7.9 RCS model 2 -- exhaustive accessor <-> YAML for all 28 rows x 10 fields.
# ---------------------------------------------------------------------------
_RCS2_FIELDS = ["phi_center_deg", "phi_3db_deg", "theta_center_deg", "theta_3db_deg",
                "g_max", "sigma_max", "range_theta_deg", "range_phi_deg", "lg_sigma_m_dbsm", "sigma_sigmaS_db"]


@pytest.mark.parametrize("target,scattering_point", _RCS2_KEYS, ids=[f"{t}-{sp}" for t, sp in _RCS2_KEYS])
def test_rcs_model_2_accessor_matches_yaml_for_every_field(target, scattering_point):
    entry = tr38901.section("7.9").rcs_model_2(target=target, scattering_point=scattering_point)
    yaml_row = next(
        e for e in _D79["rcs_model_2"] if e["target"] == target and e["scattering_point"] == scattering_point
    )
    for field in _RCS2_FIELDS:
        assert getattr(entry, field) == yaml_row[field], f"{target}/{scattering_point} {field} drifted"


# --- §7.9 finite RCS/XPR tables pinned completely (three-source verified). ---
EXPECTED_RCS_MODEL_1 = {
    "UAV with small size": ("-12.81", "3.74"),
    "Human with RCS model 1": ("-1.37", "3.94"),
}
EXPECTED_XPR = {
    "UAV": ("13.75", "7.07"), "Human": ("19.81", "4.25"),
    "Vehicle": ("21.12", "6.88"), "AGV": ("9.60", "6.85"),
}
EXPECTED_K_PARAMS = {
    "UAV with large size": ("6.05", "1.33"), "Human with RCS model 2": ("0.5714", "0.1"),
    "Vehicle with single/multiple SPSTs": ("6", "1.65"), "AGV with single/multiple SPSTs": ("12", "1.45"),
}


def test_rcs_model_1_pinned_completely():
    got = {e["sensing_target"]: (e["lg_sigma_m_dbsm"], e["sigma_sigmaS_db"]) for e in _D79["rcs_model_1"]}
    assert got == EXPECTED_RCS_MODEL_1


def test_xpr_pinned_completely():
    got = {e["target"]: (e["mu_xpr_db"], e["sigma_xpr_db"]) for e in _D79["xpr"]}
    assert got == EXPECTED_XPR


def test_rcs_model_2_k_parameters_pinned_completely():
    got = {e["target"]: (e["k1"], e["k2"]) for e in _D79["rcs_model_2_k_parameters"]}
    assert got == EXPECTED_K_PARAMS


# ---------------------------------------------------------------------------
# TR 36.777 Annex B -- every delta-table row's band structure + both Alternatives.
# ---------------------------------------------------------------------------
_ANNEX_B = tr36777.annex("B")


@pytest.mark.parametrize("scenario", ["RMa-AV", "UMa-AV", "UMi-AV"])
def test_annex_b_los_probability_band_structure(scenario):
    bands = _ANNEX_B.los_probability(scenario=scenario)
    # A terrestrial-baseline "According to ..." band plus at least one aerial band.
    assert any("According to" in b.los_probability for b in bands)
    assert any("According to" not in b.los_probability for b in bands)
    # bands are ordered by ascending height threshold (all reference the same scenario)
    assert all(b.scenario == scenario for b in bands)


@pytest.mark.parametrize("scenario,condition", [
    ("RMa-AV", "LOS"), ("RMa-AV", "NLOS"), ("UMa-AV", "LOS"),
    ("UMa-AV", "NLOS"), ("UMi-AV", "LOS"), ("UMi-AV", "NLOS"),
])
def test_annex_b_pathloss_band_structure(scenario, condition):
    bands = _ANNEX_B.pathloss(scenario=scenario, condition=condition)
    assert len(bands) >= 2  # terrestrial baseline + aerial-specific
    assert any("According to" in b.pathloss for b in bands)
    assert any(f"PL_{{{scenario}" in b.pathloss for b in bands)


# ---------------------------------------------------------------------------
# Generic exhaustive accessor coverage: EVERY row of EVERY list-based lookup,
# across all four sections, must be retrievable via its accessor and match the
# committed data. This anchors the remaining tables per-row (§7.9's calibration
# 97 rows, the case/link tables, Annex B's alternatives, §7.4 pathloss/LOS,
# etc.) without hand-writing a test per section. Dict-based lookups (§7.5's
# zsd_zod_offset) are covered in test_tr_api.py.
# ---------------------------------------------------------------------------
def _accessor_row_cases():
    cases = []
    for unit in introspect.all_units(detail=True, with_values=False):
        accessor = introspect.load_accessor(unit.tr_module, unit.key)
        for member in unit.members:
            if member.kind != "method":
                continue
            data = getattr(accessor._data, member.data_attribute)
            if not isinstance(data, list):
                continue  # dict-based (zsd_zod_offset) handled elsewhere
            for i in range(len(data)):
                cases.append(pytest.param(
                    unit.tr_module, unit.key, member.name, i,
                    id=f"{unit.tr_module}-{unit.key}-{member.name}-{i}",
                ))
    return cases


_ACCESSOR_ROW_CASES = _accessor_row_cases()


@pytest.mark.parametrize("tr_module,key,member_name,idx", _ACCESSOR_ROW_CASES)
def test_every_data_row_is_retrievable_and_matches(tr_module, key, member_name, idx):
    accessor = introspect.load_accessor(tr_module, key)
    member = next(m for m in introspect.describe(tr_module, key, with_values=False).members if m.name == member_name)
    row = getattr(accessor._data, member.data_attribute)[idx]
    # Build the lookup key from this row; drop optional args that are None here.
    kwargs = {a.name: getattr(row, a.field) for a in member.args}
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    result = getattr(accessor, member_name)(**kwargs)
    if member.returns_list:
        assert row.model_dump() in [r.model_dump() for r in result]
    else:
        assert result.model_dump() == row.model_dump()
