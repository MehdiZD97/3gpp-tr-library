"""
Regression guard for §7.5's parameter values. The expected values below were
manually cross-verified against the rendered PDF (visual read) and, for
Table 7.5-6, an automated numeric cross-check against the HTML export's
tag-stripped text (0 of 826 checked field values missing -- see the
section's `verified_against` front matter field). This test's job is to
catch *future* drift from these already-verified numbers, not to re-derive
them.

Table 7.5-6 has 16 scenario/condition entries x 49 parameter fields --
too much to usefully hardcode in full here (that would just duplicate the
YAML). Instead this locks in: every expected (scenario, condition) pair is
present (nothing silently dropped), plus a representative sample of directly
PDF-confirmed values per scenario group (one from each of the four docx
table parts) as a tripwire for gross corruption.
"""

EXPECTED_CHANNEL_MODEL_PARAMETER_SCENARIOS = {
    ("UMi - Street Canyon", "LOS"), ("UMi - Street Canyon", "NLOS"), ("UMi - Street Canyon", "O2I"),
    ("UMa", "LOS"), ("UMa", "NLOS"), ("UMa", "O2I"),
    ("RMa", "LOS"), ("RMa", "NLOS"), ("RMa", "O2I"),
    ("Indoor-Office", "LOS"), ("Indoor-Office", "NLOS"),
    ("InF", "LOS"), ("InF", "NLOS"),
    ("SMa", "LOS"), ("SMa", "NLOS"), ("SMa", "O2I"),
}

# (scenario, condition) -> {field: expected value}, one spot-check per
# Table 7.5-6 docx part (UMi/UMa, RMa/Indoor-Office, InF, SMa).
EXPECTED_CHANNEL_MODEL_PARAMETER_SAMPLES = {
    ("UMi - Street Canyon", "LOS"): {"mu_K": "9", "sigma_K": "5", "number_of_clusters": "12"},
    ("UMa", "NLOS"): {"mu_lgDS": "-6.47 - 0.134 log10(fc), see note 8", "number_of_clusters": "20"},
    ("RMa", "LOS"): {"mu_lgDS": "-7.49", "number_of_clusters": "11", "delay_scaling_parameter_r_tau": "3.8"},
    ("Indoor-Office", "NLOS"): {"mu_lgDS": "-0.28 log10(1+fc) - 7.173", "number_of_clusters": "19"},
    ("InF", "LOS"): {"mu_lgDS": "log10(26(V/S)+14)-9.35", "number_of_clusters": "25", "mu_K": "7"},
    ("SMa", "O2I"): {"mu_lgDS": "-7.20", "number_of_clusters": "14"},
}

EXPECTED_ZSD_ZOD_SCENARIOS = {"UMa", "UMi-StreetCanyon", "RMa", "Indoor-Office", "InF", "SMa"}


def test_every_expected_channel_model_parameter_scenario_present(section_7_5_yaml_data):
    found = {(e["scenario"], e["condition"]) for e in section_7_5_yaml_data["channel_model_parameters"]}
    assert found == EXPECTED_CHANNEL_MODEL_PARAMETER_SCENARIOS


def test_channel_model_parameter_samples_match_verified_values(section_7_5_yaml_data):
    by_key = {(e["scenario"], e["condition"]): e for e in section_7_5_yaml_data["channel_model_parameters"]}
    for key, expected_fields in EXPECTED_CHANNEL_MODEL_PARAMETER_SAMPLES.items():
        entry = by_key[key]
        for field, expected_value in expected_fields.items():
            assert entry[field] == expected_value, f"{key} {field}: drifted from verified value"


def test_channel_model_parameters_have_all_49_fields(section_7_5_yaml_data):
    from tr_api.models import ChannelModelParameterEntry

    expected_fields = set(ChannelModelParameterEntry.model_fields) - {"scenario", "condition"}
    for entry in section_7_5_yaml_data["channel_model_parameters"]:
        assert set(entry) - {"scenario", "condition"} == expected_fields


def test_every_expected_zsd_zod_scenario_present(section_7_5_yaml_data):
    assert set(section_7_5_yaml_data["zsd_zod_offset_parameters"]) == EXPECTED_ZSD_ZOD_SCENARIOS


def test_zsd_zod_sma_values_match_verified_values(section_7_5_yaml_data):
    # SMa (Table 7.5-12) directly confirmed against the rendered PDF.
    sma = section_7_5_yaml_data["zsd_zod_offset_parameters"]["SMa"]
    assert sma["tr_table"] == "7.5-12"
    by_condition = {e["condition"]: e for e in sma["entries"]}
    assert by_condition["LOS"]["mu_lgZSD"] == "0.14"
    assert by_condition["NLOS"]["mu_offset_ZOD"] == "= 3.5"


def test_notations_table_has_no_duplicate_notations(section_7_5_yaml_data):
    # Table 7.5-1 legitimately repeats "parameter" prose for two pairs of
    # rows (Rx/Tx field patterns differing only by theta/phi) -- confirmed
    # directly against the source and handled in tools/verify_tables.py by
    # keying on "notation" instead. This test locks in that "notation"
    # really is the unique key.
    notations = [n["notation"] for n in section_7_5_yaml_data["notations"]]
    assert len(notations) == len(set(notations)) == 16


def test_ray_offset_angles_cover_all_20_rays(section_7_5_yaml_data):
    all_rays = set()
    for entry in section_7_5_yaml_data["ray_offset_angles"]:
        for n in entry["ray_numbers"].split(","):
            all_rays.add(int(n))
    assert all_rays == set(range(1, 21))


def test_sub_cluster_info_rays_partition_all_20_rays(section_7_5_yaml_data):
    all_rays = set()
    for entry in section_7_5_yaml_data["sub_cluster_info"]:
        rays = {int(n) for n in entry["mapping_to_rays"].split(",")}
        assert not (all_rays & rays), "sub-clusters should not overlap"
        all_rays |= rays
    assert all_rays == set(range(1, 21))
