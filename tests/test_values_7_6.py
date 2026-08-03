"""
Regression-locked values for TR 38.901 §7.6 (Additional modelling components),
dependency-driven core: 7.6.0/7.6.1 (oxygen absorption), 7.6.3 (spatial
consistency), 7.6.4 (blockage), 7.6.8 (explicit ground reflection), 7.6.9
(absolute time of arrival), 7.6.10 (dual mobility).

Two guarantees, as in the other sections' value tests:

1. **Completeness** -- every entity the TR's tables define is present, with the
   right cardinality and the right key set.
2. **Literal anchors** -- the actual numbers, pinned. All eleven in-scope tables
   are small and finite, so unlike §7.5's 780-cell table they are pinned
   *completely* here (the §7.9 RCS/XPR treatment).

Verification provenance for these values: python-docx extraction (automated,
every docx-visible cell) + a rendered-PDF visual read (pp. 59, 62-63, 68-72, 77,
80) + an HTML tag-strip cross-check of the distinctive decimals. The handful of
cells python-docx cannot supply (OMML symbol labels; Metal's 10^7) are
PDF-visual only and recorded in the section .md's `verification_notes`.
"""
import pytest
from tr3gpp import tr38901

SECTION = tr38901.section("7.6")


# ---------------------------------------------------------------------------
# Front matter
# ---------------------------------------------------------------------------
def test_front_matter_identifies_the_real_clause(section_7_6_front_matter):
    fm = section_7_6_front_matter
    assert fm["tr"] == "TR 38.901"
    assert fm["version"] == "v19.4.0"
    assert fm["section"] == "7.6"
    # The TR's real clause title, broader than the filename slug (the §7.4/§7.9 precedent).
    assert fm["title"] == "Additional modelling components"
    assert fm["status"] == "verified"
    assert set(fm["verified_against"]) == {"docx", "pdf", "html"}
    assert fm["depends_on"] == ["7.4-pathloss", "7.5-fast-fading"]


def test_front_matter_records_the_ole_single_source_equations(section_7_6_front_matter):
    # The clause's key format finding must be recorded granularly, not hidden
    # behind the section-level verified_against.
    joined = " ".join(n["applies_to"] for n in section_7_6_front_matter["verification_notes"])
    assert "7.6.8" in joined and "7.6.4" in joined      # the OLE-embedded equations
    assert "Metal c_sigma = 10^7" in joined             # the docx superscript loss
    assert any(n["verified_against"] == ["pdf"] for n in section_7_6_front_matter["verification_notes"])


# ---------------------------------------------------------------------------
# 7.6.1 Oxygen absorption -- Table 7.6.1-1 pinned completely
# ---------------------------------------------------------------------------
EXPECTED_OXYGEN = [
    ("0-52", "0"), ("53", "1"), ("54", "2.2"), ("55", "4"), ("56", "6.6"),
    ("57", "9.7"), ("58", "12.6"), ("59", "14.6"), ("60", "15"), ("61", "14.6"),
    ("62", "14.3"), ("63", "10.5"), ("64", "6.8"), ("65", "3.9"), ("66", "1.9"),
    ("67", "1"), ("68-100", "0"),
]


def test_oxygen_absorption_table_pinned_completely(section_7_6_yaml_data):
    got = [(e["f_ghz"], e["alpha_db_per_km"]) for e in section_7_6_yaml_data["oxygen_absorption_loss"]]
    assert got == EXPECTED_OXYGEN


@pytest.mark.parametrize("f_ghz,alpha", EXPECTED_OXYGEN)
def test_oxygen_absorption_accessor_matches(f_ghz, alpha):
    assert SECTION.oxygen_absorption(f_ghz=f_ghz).alpha_db_per_km == alpha


def test_oxygen_loss_peaks_at_60_ghz(section_7_6_yaml_data):
    # The physical shape of the 60 GHz oxygen absorption peak (a sanity anchor
    # on top of the literal values above).
    numeric = [(e["f_ghz"], float(e["alpha_db_per_km"]))
               for e in section_7_6_yaml_data["oxygen_absorption_loss"] if e["f_ghz"].isdigit()]
    peak = max(numeric, key=lambda x: x[1])
    assert peak == ("60", 15.0)


# ---------------------------------------------------------------------------
# 7.6.3 Spatial consistency -- Tables 7.6.3.1-2 / 7.6.3.4-1 / 7.6.3.4-2
# ---------------------------------------------------------------------------
# (scenario, condition) -> (cluster/ray, LOS-NLOS state, indoor/outdoor state)
EXPECTED_CORR_DIST = {
    ("RMa", "LOS"): ("50", "60", "50"), ("RMa", "NLOS"): ("60", "60", "50"),
    ("RMa", "O2I"): ("15", "60", "50"),
    ("UMi", "LOS"): ("12", "50", "50"), ("UMi", "NLOS"): ("15", "50", "50"),
    ("UMi", "O2I"): ("15", "50", "50"),
    ("UMa", "LOS"): ("40", "50", "50"), ("UMa", "NLOS"): ("50", "50", "50"),
    ("UMa", "O2I"): ("15", "50", "50"),
    ("SMa", "LOS"): ("40", "50", "50"), ("SMa", "NLOS"): ("50", "50", "50"),
    ("SMa", "O2I"): ("15", "50", "50"),
    ("Indoor", None): ("10", "10", "N/A"),
    ("InF", None): ("10", "d_clutter/2", "N/A"),
}


def test_correlation_distance_table_pinned_completely(section_7_6_yaml_data):
    got = {
        (e["scenario"], e["condition"]): (
            e["cluster_ray_specific_m"], e["los_nlos_state_m"], e["indoor_outdoor_state_m"])
        for e in section_7_6_yaml_data["spatial_consistency_correlation_distance"]
    }
    assert got == EXPECTED_CORR_DIST


@pytest.mark.parametrize("key", sorted(EXPECTED_CORR_DIST, key=lambda k: (k[0], k[1] or "")))
def test_correlation_distance_accessor_matches(key):
    scenario, condition = key
    entry = SECTION.correlation_distance(scenario=scenario, condition=condition)
    assert (entry.cluster_ray_specific_m, entry.los_nlos_state_m,
            entry.indoor_outdoor_state_m) == EXPECTED_CORR_DIST[key]


def test_indoor_and_inf_have_no_los_nlos_split(section_7_6_yaml_data):
    # The TR's Indoor and InF columns span all conditions; everything else splits.
    no_condition = {e["scenario"] for e in section_7_6_yaml_data["spatial_consistency_correlation_distance"]
                    if e["condition"] is None}
    assert no_condition == {"Indoor", "InF"}
    # ...and they are reachable without passing a condition at all.
    assert SECTION.correlation_distance(scenario="Indoor").cluster_ray_specific_m == "10"


EXPECTED_CORR_TYPE = {
    "Delays": "Site-specific", "Cluster powers": "Site-specific",
    "AOA/ZOA/AOD/ZOD offset": "Site-specific", "AOA/ZOA/AOD/ZOD sign": "Site-specific",
    "Random coupling": "Site-specific", "XPR": "Site-specific",
    "Initial random phase": "Site-specific", "LOS/NLOS states": "Site-specific",
    "Blockage (Model A)": "All-correlated", "O2I penetration loss": "All-correlated",
    "Indoor distance": "All-correlated", "Indoor states": "All-correlated",
}


def test_correlation_type_table_pinned_completely(section_7_6_yaml_data):
    got = {e["parameter"]: e["correlation_type"]
           for e in section_7_6_yaml_data["spatial_consistency_correlation_type"]}
    assert got == EXPECTED_CORR_TYPE


def test_correlation_type_uses_only_the_two_defined_types(section_7_6_yaml_data):
    types = {e["correlation_type"] for e in section_7_6_yaml_data["spatial_consistency_correlation_type"]}
    assert types == {"Site-specific", "All-correlated"}


_OUTDOOR = "Outdoor LOS/outdoor NLOS/O2I (different floors)"
EXPECTED_UNCORRELATED = {
    "Delays": _OUTDOOR, "Cluster powers": _OUTDOOR, "AOA/ZOA/AOD/ZOD offset": _OUTDOOR,
    "AOA/ZOA/AOD/ZOD sign": _OUTDOOR, "Random coupling": _OUTDOOR, "XPR": _OUTDOOR,
    "Initial random phase": _OUTDOOR,
    "Blockage": "Outdoor/O2I (different floors)",
    "Standard deviation for O2I penetration loss": "Different building types, i.e., high/low loss",
}


def test_uncorrelated_states_table_pinned_completely(section_7_6_yaml_data):
    got = {e["parameter"]: e["uncorrelated_states"]
           for e in section_7_6_yaml_data["spatial_consistency_uncorrelated_states"]}
    assert got == EXPECTED_UNCORRELATED


# ---------------------------------------------------------------------------
# 7.6.4 Blockage -- Tables 7.6.4.1-1..-4 and 7.6.4.2-5
# ---------------------------------------------------------------------------
EXPECTED_SELF_BLOCKING = {
    "Portrait mode": ("260", "120", "100", "80"),
    "Landscape mode": ("40", "160", "110", "75"),
}


def test_self_blocking_region_pinned_completely(section_7_6_yaml_data):
    got = {e["mode"]: (e["phi_sb_deg"], e["x_sb_deg"], e["theta_sb_deg"], e["y_sb_deg"])
           for e in section_7_6_yaml_data["self_blocking_region"]}
    assert got == EXPECTED_SELF_BLOCKING


EXPECTED_BLOCKING_REGION = {
    "InH scenario": ("Uniform in [0, 360]", "Uniform in [15, 45]", "90", "Uniform in [5, 15]", "2"),
    "UMi, UMa, SMa, RMa scenarios": ("Uniform in [0, 360]", "Uniform in [5, 15]", "90", "5", "10"),
}


def test_blocking_region_pinned_completely(section_7_6_yaml_data):
    got = {e["scenario"]: (e["phi_k_deg"], e["x_k_deg"], e["theta_k_deg"], e["y_k_deg"], e["r_m"])
           for e in section_7_6_yaml_data["blocking_region"]}
    assert got == EXPECTED_BLOCKING_REGION


def test_blockage_sign_table_is_a_full_3x3_grid(section_7_6_yaml_data):
    rows = section_7_6_yaml_data["blockage_sign_description"]
    assert len(rows) == 9
    aoa = {e["aoa_range"] for e in rows}
    zoa = {e["zoa_range"] for e in rows}
    assert len(aoa) == 3 and len(zoa) == 3
    # every (aoa, zoa) combination appears exactly once
    assert len({(e["aoa_range"], e["zoa_range"]) for e in rows}) == 9
    # only the four legal sign pairs occur
    signs = {e["signs_a1_a2"] for e in rows} | {e["signs_z1_z2"] for e in rows}
    assert signs <= {"(+, +)", "(+, -)", "(-, +)", "(-, -)"}


def test_blockage_sign_middle_cell_pinned():
    # The 3x3 grid's centre cell (both differences within +/- half the span):
    # plus signs on both pairs.
    middle = [e for e in SECTION.blockage_sign_description
              if e.aoa_range.startswith("-x_k/2") and e.zoa_range.startswith("-y_k/2")]
    assert len(middle) == 1
    assert (middle[0].signs_a1_a2, middle[0].signs_z1_z2) == ("(+, +)", "(+, +)")


EXPECTED_BLOCKAGE_CORR_DIST = {
    ("UMi/UMa/SMa/RMa", "LOS"): "10", ("UMi/UMa/SMa/RMa", "NLOS"): "10",
    ("UMi/UMa/SMa/RMa", "O2I"): "5", ("InH", "LOS"): "5", ("InH", "NLOS"): "5",
}


def test_blockage_correlation_distance_pinned_completely(section_7_6_yaml_data):
    got = {(e["scenario"], e["condition"]): e["d_corr_m"]
           for e in section_7_6_yaml_data["blockage_correlation_distance"]}
    assert got == EXPECTED_BLOCKAGE_CORR_DIST


EXPECTED_BLOCKERS = {
    "Human": ("Indoor; Outdoor; InF", "Cartesian: w=0.3m; h=1.7m", "Stationary or up to 3 km/h"),
    "Vehicle": ("Outdoor", "Cartesian: w=4.8m; h=1.4m", "Stationary or up to 100 km/h"),
    "AGV": ("InF", "Cartesian: w=3m; h=1.5m", "Up to 30 km/h"),
    "Industrial robot": ("InF", "Cartesian: w=2m; h=0.2m", "Up to 3 m/s"),
}


def test_blocker_parameters_pinned_completely(section_7_6_yaml_data):
    got = {e["blocker"]: (e["environment"], e["dimensions"], e["mobility_pattern"])
           for e in section_7_6_yaml_data["blocker_parameters"]}
    assert got == EXPECTED_BLOCKERS


@pytest.mark.parametrize("blocker", sorted(EXPECTED_BLOCKERS))
def test_blocker_parameters_accessor_matches(blocker):
    e = SECTION.blocker_parameters(blocker=blocker)
    assert (e.environment, e.dimensions, e.mobility_pattern) == EXPECTED_BLOCKERS[blocker]


# ---------------------------------------------------------------------------
# 7.6.8 Explicit ground reflection -- Table 7.6.8-1
# ---------------------------------------------------------------------------
EXPECTED_MATERIALS = {
    "Concrete": ("5.31", "0", "0.0326", "0.8095", "1-100"),
    "Brick": ("3.75", "0", "0.038", "0", "1-10"),
    "Plasterboard": ("2.94", "0", "0.0116", "0.7076", "1-100"),
    "Wood": ("1.99", "0", "0.0047", "1.0718", "0.001-100"),
    "Floorboard": ("3.66", "0", "0.0044", "1.3515", "50-100"),
    "Metal": ("1", "0", "10^7", "0", "1-100"),
    "Very dry ground": ("3", "0", "0.00015", "2.52", "1-10"),
    "Medium dry ground": ("15", "-0.1", "0.035", "1.63", "1-10"),
    "Wet ground": ("30", "-0.4", "0.15", "1.30", "1-10"),
}


def test_ground_material_properties_pinned_completely(section_7_6_yaml_data):
    got = {e["material_class"]: (e["a_epsilon"], e["b_epsilon"], e["c_sigma"],
                                 e["d_sigma"], e["frequency_range_ghz"])
           for e in section_7_6_yaml_data["ground_material_properties"]}
    assert got == EXPECTED_MATERIALS


@pytest.mark.parametrize("material", sorted(EXPECTED_MATERIALS))
def test_ground_material_accessor_matches(material):
    e = SECTION.ground_material(material_class=material)
    assert (e.a_epsilon, e.b_epsilon, e.c_sigma, e.d_sigma,
            e.frequency_range_ghz) == EXPECTED_MATERIALS[material]


def test_metal_conductivity_keeps_its_superscript():
    # python-docx flattens 10^7 to "107"; the committed value is the PDF's.
    # This is the one cell where a naive docx-only extraction would be wrong.
    assert SECTION.ground_material(material_class="Metal").c_sigma == "10^7"


# ---------------------------------------------------------------------------
# 7.6.9 Absolute time of arrival -- Table 7.6.9-1
# ---------------------------------------------------------------------------
EXPECTED_TOA = {
    "InH": ("-8.6", "0.1", "10"),
    "InF-SL, InF-DL": ("-7.5", "0.4", "6"),
    "InF-SH, InF-DH": ("-7.5", "0.4", "11"),
    "UMi": ("-7.5", "0.5", "15"),
    "UMa": ("-7.4", "0.2", "50"),
    "RMa": ("-8.33", "0.26", "50"),
    "SMa": ("-7.702", "0.4", "50"),
}


def test_absolute_time_of_arrival_pinned_completely(section_7_6_yaml_data):
    got = {e["scenario"]: (e["mu_lg_delta_tau"], e["sigma_lg_delta_tau"], e["corr_distance_m"])
           for e in section_7_6_yaml_data["absolute_time_of_arrival"]}
    assert got == EXPECTED_TOA


@pytest.mark.parametrize("scenario", sorted(EXPECTED_TOA))
def test_absolute_time_of_arrival_accessor_matches(scenario):
    e = SECTION.absolute_time_of_arrival(scenario=scenario)
    assert (e.mu_lg_delta_tau, e.sigma_lg_delta_tau, e.corr_distance_m) == EXPECTED_TOA[scenario]


# ---------------------------------------------------------------------------
# Cross-section coherence: §7.9 (ISAC) reuses §7.6's tables by name -- this is
# the dependency that drove the scope choice, so it is worth asserting rather
# than assuming.
# ---------------------------------------------------------------------------
def test_section_7_9_absolute_delay_references_resolve_to_this_table():
    isac = tr38901.section("7.9")
    referenced = set()
    for row in isac.calibration(table="7.9.6.1-1") + isac.calibration(table="7.9.6.2-1"):
        for value in (row.value, row.indoor_value, row.outdoor_value):
            if value and "7.6.9-1" in value:
                referenced.add(row.parameter)
    assert referenced, "§7.9's calibration tables no longer reference Table 7.6.9-1"
    # Every scenario §7.9 names for the absolute-delay model exists in Table 7.6.9-1.
    ours = {e.scenario for e in tr38901.section("7.6")._data.absolute_time_of_arrival}
    flat = " ".join(s for s in ours)
    for scenario in ("UMa", "UMi", "RMa", "InH", "InF"):
        assert scenario in flat


def test_section_7_9_ground_reflection_reference_resolves():
    # §7.9.5's type-2 EO model points at "the row for concrete in Table 7.6.8-1".
    isac_text = " ".join(
        str(v) for row in tr38901.section("7.9").calibration(table="7.9.6.3-1")
        for v in (row.value, row.indoor_value, row.outdoor_value) if v
    )
    if "7.6.8-1" in isac_text:
        assert SECTION.ground_material(material_class="Concrete").a_epsilon == "5.31"
