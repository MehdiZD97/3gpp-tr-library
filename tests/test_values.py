"""
Regression guard for §7.4's parameter values. The expected values below were
manually cross-verified against the rendered PDF (visual read) and the HTML
export (OMML text extraction) during Phase 2 -- see the section's
`verified_against` front matter field. This test's job is to catch *future*
drift from these already-verified numbers, not to re-derive them.
"""

EXPECTED_PATHLOSS_SCENARIOS = {
    # (scenario, condition, variant) -> expected shadow_fading_std_db value(s)
    ("RMa", "LOS", None): [4, 6],
    ("RMa", "NLOS", None): [8],
    ("UMa", "LOS", None): [4],
    ("UMa", "NLOS", None): [6],
    ("UMa", "NLOS", "optional"): [7.8],
    ("UMi-StreetCanyon", "LOS", None): [4],
    ("UMi-StreetCanyon", "NLOS", None): [7.82],
    ("UMi-StreetCanyon", "NLOS", "optional"): [8.2],
    ("InH-Office", "LOS", None): [3],
    ("InH-Office", "NLOS", None): [8.03],
    ("InH-Office", "NLOS", "optional"): [8.29],
    ("InF", "LOS", None): [4.3],
    ("InF-SL", "NLOS", None): [5.7],
    ("InF-DL", "NLOS", None): [7.2],
    ("InF-SH", "NLOS", None): [5.9],
    ("InF-DH", "NLOS", None): [4.0],
    ("SMa", "LOS", None): [4, 6],
    ("SMa", "NLOS", None): [8],
}

EXPECTED_LOS_PROBABILITY_SCENARIOS = {
    "RMa", "UMi-StreetCanyon", "UMa", "Indoor-MixedOffice", "Indoor-OpenOffice",
    "InF-SL, InF-DL, InF-SH, InF-DH", "InF-HH", "SMa",
}

EXPECTED_MATERIALS = {
    "Standard multi-pane glass": r"L_{glass} = 2 + 0.2f",
    "IRR glass": r"L_{IRRglass} = 25.4 + 0.11f",
    "Concrete": r"L_{concrete} = 5 + 4f",
    "Plywood": r"L_{plywood} = 1.03 + 0.17f",
    "Wood": r"L_{wood} = 4.85 + 0.12f",
}

EXPECTED_O2I_BUILDING_MODEL_STD_DB = {
    "Low-loss model": 4.4,
    "High-loss model": 6.5,
    "Low-loss A model": 4.4,
}


def _std_values(entry):
    return [s["value_db"] for s in entry["shadow_fading_std_db"]]


def test_every_expected_pathloss_scenario_present_with_correct_std(section_7_4_yaml_data):
    by_key = {
        (row["scenario"], row["condition"], row["variant"]): row
        for row in section_7_4_yaml_data["pathloss"]
    }
    assert set(by_key.keys()) == set(EXPECTED_PATHLOSS_SCENARIOS.keys()), (
        "pathloss scenario set drifted from what Task 0's reconnaissance found"
    )
    for key, expected_std in EXPECTED_PATHLOSS_SCENARIOS.items():
        assert _std_values(by_key[key]) == expected_std, f"{key}: shadow fading std drifted"


def test_shadow_fading_std_within_plausible_bounds(section_7_4_yaml_data):
    for row in section_7_4_yaml_data["pathloss"]:
        for std in row["shadow_fading_std_db"]:
            value = std["value_db"]
            assert 0 < value <= 15, f"{row['scenario']}/{row['condition']}: std {value} dB outside plausible 0-15 dB range"


def test_every_expected_los_probability_scenario_present(section_7_4_yaml_data):
    scenarios = {row["scenario"] for row in section_7_4_yaml_data["los_probability"]}
    assert scenarios == EXPECTED_LOS_PROBABILITY_SCENARIOS


def test_material_penetration_loss_formulas(section_7_4_yaml_data):
    materials = section_7_4_yaml_data["o2i_penetration_loss"]["materials"]
    by_name = {m["material"]: m["formula"] for m in materials}
    assert by_name == EXPECTED_MATERIALS


def test_o2i_building_model_std_values(section_7_4_yaml_data):
    models = section_7_4_yaml_data["o2i_penetration_loss"]["building_models"]
    by_name = {m["model"]: m["std_p_db"] for m in models}
    assert by_name == EXPECTED_O2I_BUILDING_MODEL_STD_DB


def test_o2i_car_penetration_loss_values(section_7_4_yaml_data):
    car = section_7_4_yaml_data["o2i_penetration_loss"]["car_penetration_loss"]
    assert car["mu_db"] == 9
    assert car["mu_metallized_windows_db"] == 20
    assert car["sigma_p_db"] == 5


def test_o2i_single_frequency_below_6ghz_values(section_7_4_yaml_data):
    entry = section_7_4_yaml_data["o2i_penetration_loss"]["building_single_frequency_below_6ghz"]
    assert entry["pl_tw_db"] == 20
    assert entry["sigma_p_db"] == 0
    assert entry["sigma_sf_db"] == 7


def test_shadow_fading_autocorrelation_formula_ref(section_7_4_yaml_data):
    assert section_7_4_yaml_data["shadow_fading_autocorrelation"]["formula_ref"] == "7.4-5"
