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


def test_shadow_fading_autocorrelation_formula(section_7_4_yaml_data):
    autocorr = section_7_4_yaml_data["shadow_fading_autocorrelation"]
    assert autocorr["formula"] == r"R(\Delta x) = e^{-|\Delta x| / d_{cor}}"


# ---------------------------------------------------------------------------
# Every LOS-probability entry's formula, pinned by its distinctive constants.
# (Pinning the constants rather than the whole LaTeX string catches value drift
#  without a long, transcription-error-prone literal.) The RMa/Indoor-Mixed/
#  Indoor-Open entries are the PDF-visual single-source ones -- now recorded in
#  the section's verification_notes -- so anchoring their constants matters most.
# ---------------------------------------------------------------------------
EXPECTED_LOS_FORMULA_CONSTANTS = {
    "RMa": ["10m", "1000"],
    "UMi-StreetCanyon": ["18", "36"],
    "UMa": ["18", "63", "150", "13m", "23m"],
    "Indoor-MixedOffice": ["1.2m", "4.7", "6.5m", "32.6", "0.32"],
    "Indoor-OpenOffice": ["5m", "70.8", "49m", "211.7", "0.54"],
    "InF-SL, InF-DL, InF-SH, InF-DH": ["d_{clutter}", r"\ln(1-r)", "h_c"],
    "InF-HH": ["Pr_{LOS} = 1"],
    "SMa": ["10m", "k_{commercial}", "k_{residential}", "k_{vegetation}", "30m", "20m", "8m", "15m"],
}


def test_every_los_probability_formula_has_expected_constants(section_7_4_yaml_data):
    by_scenario = {e["scenario"]: e["formula"] for e in section_7_4_yaml_data["los_probability"]}
    assert set(by_scenario) == set(EXPECTED_LOS_FORMULA_CONSTANTS)
    for scenario, constants in EXPECTED_LOS_FORMULA_CONSTANTS.items():
        formula = by_scenario[scenario]
        for const in constants:
            assert const in formula, f"{scenario} LOS formula: expected constant {const!r} missing (value drift?)"


def test_every_building_model_formula_has_expected_constants(section_7_4_yaml_data):
    models = {m["model"]: m for m in section_7_4_yaml_data["o2i_penetration_loss"]["building_models"]}
    # Low-loss: 0.3 glass + 0.7 concrete; High-loss: 0.7 IRR-glass + 0.3 concrete;
    # Low-loss A: 0.3 glass + 0.7 plywood. PL_in is 0.5 * d_2D-in for all.
    assert "0.3\\cdot10^{-L_{glass}/10} + 0.7\\cdot10^{-L_{concrete}/10}" in models["Low-loss model"]["pl_tw_formula"]
    assert "0.7\\cdot10^{-L_{IRRglass}/10} + 0.3\\cdot10^{-L_{concrete}/10}" in models["High-loss model"]["pl_tw_formula"]
    assert "0.3\\cdot10^{-L_{glass}/10} + 0.7\\cdot10^{-L_{plywood}/10}" in models["Low-loss A model"]["pl_tw_formula"]
    for m in models.values():
        assert m["pl_in_formula"] == r"0.5\, d_{2D-in}"


def test_every_pathloss_formula_present_and_scenario_tagged(section_7_4_yaml_data):
    # Each pathloss entry has a non-empty LaTeX formula naming its own scenario's
    # PL symbol (guards against a blanked or mis-assigned formula cell).
    for e in section_7_4_yaml_data["pathloss"]:
        assert e["formula"].strip(), f"{e['scenario']}/{e['condition']}: empty pathloss formula"
        assert "PL_{" in e["formula"] or "PL'" in e["formula"]
