"""
Tests for tools/tr_api/models.py's Pydantic models: a valid entry validates
and produces the expected typed access; a malformed one (missing required
field, wrong type, invalid enum-like value) is rejected.

Requires tr_api to be installed (`pip install -e tools/tr_api`) -- see
docs/CONTRIBUTING.md's Development setup section.
"""
import pytest
from pydantic import ValidationError
from tr_api.models import (
    Alternative1DesiredParametersEntry,
    Alternative2ModifiedParameterEntry,
    BackgroundChannelParamEntry,
    CalibrationAssumption,
    ChannelModelParameterEntry,
    LosConditionEntry,
    PathlossDeltaEntry,
    PathlossEntry,
    RcsModel2Entry,
    SensingScenarioParameter,
    SpatialConsistencyCorrelationEntry,
    XprEntry,
    ZsdZodOffsetEntry,
)


def _valid_pathloss_kwargs(**overrides):
    kwargs = dict(
        scenario="RMa",
        condition="LOS",
        variant=None,
        formula="PL = 20\\log_{10}(d)",
        formula_ref=None,
        shadow_fading_std_db=[{"condition": None, "value_db": 4}],
        applicability_range="hBS = 35m",
        notes=["NOTE 1"],
    )
    kwargs.update(overrides)
    return kwargs


def test_valid_pathloss_entry_validates():
    entry = PathlossEntry(**_valid_pathloss_kwargs())
    assert entry.scenario == "RMa"
    assert entry.shadow_fading_std_db[0].value_db == 4
    assert entry.notes == ["NOTE 1"]


def test_pathloss_entry_defaults_variant_and_notes():
    kwargs = _valid_pathloss_kwargs()
    del kwargs["variant"]
    del kwargs["notes"]
    entry = PathlossEntry(**kwargs)
    assert entry.variant is None
    assert entry.notes == []


def test_pathloss_entry_missing_required_field_rejected():
    kwargs = _valid_pathloss_kwargs()
    del kwargs["scenario"]
    with pytest.raises(ValidationError):
        PathlossEntry(**kwargs)


def test_pathloss_entry_invalid_condition_value_rejected():
    with pytest.raises(ValidationError):
        PathlossEntry(**_valid_pathloss_kwargs(condition="SOMETHING_ELSE"))


def test_pathloss_entry_wrong_type_for_std_list_rejected():
    with pytest.raises(ValidationError):
        PathlossEntry(**_valid_pathloss_kwargs(shadow_fading_std_db="not-a-list"))


def test_pathloss_entry_empty_std_list_rejected():
    # schemas/pathloss.yaml documents at least one shadow_fading_std_db entry.
    with pytest.raises(ValidationError):
        PathlossEntry(**_valid_pathloss_kwargs(shadow_fading_std_db=[]))


def _valid_channel_model_parameter_kwargs(**overrides):
    # Table 7.5-6 has 49 parameter fields beyond scenario/condition; fill
    # them all with a placeholder string (every field is str-typed -- see
    # ChannelModelParameterEntry's docstring on why) rather than hand-typing
    # 49 kwargs, then apply the specific overrides a test cares about.
    kwargs = {
        f: "placeholder" for f in ChannelModelParameterEntry.model_fields if f not in ("scenario", "condition")
    }
    kwargs["scenario"] = "UMa"
    kwargs["condition"] = "LOS"
    kwargs.update(overrides)
    return kwargs


def test_valid_channel_model_parameter_entry_validates():
    entry = ChannelModelParameterEntry(**_valid_channel_model_parameter_kwargs(mu_K="9"))
    assert entry.scenario == "UMa"
    assert entry.mu_K == "9"


def test_channel_model_parameter_entry_missing_required_field_rejected():
    kwargs = _valid_channel_model_parameter_kwargs()
    del kwargs["mu_lgDS"]
    with pytest.raises(ValidationError):
        ChannelModelParameterEntry(**kwargs)


def test_channel_model_parameter_entry_invalid_condition_value_rejected():
    with pytest.raises(ValidationError):
        ChannelModelParameterEntry(**_valid_channel_model_parameter_kwargs(condition="SOMETHING_ELSE"))


def test_valid_zsd_zod_offset_entry_validates():
    entry = ZsdZodOffsetEntry(condition="NLOS", mu_lgZSD="0.49", sigma_lgZSD="0.49", mu_offset_ZOD="0")
    assert entry.condition == "NLOS"


def test_zsd_zod_offset_entry_invalid_condition_value_rejected():
    with pytest.raises(ValidationError):
        ZsdZodOffsetEntry(condition="SOMETHING_ELSE", mu_lgZSD="0", sigma_lgZSD="0", mu_offset_ZOD="0")


# --- TR 36.777 Annex B models ---
def test_valid_pathloss_delta_entry_validates():
    entry = PathlossDeltaEntry(
        scenario="RMa-AV", condition="LOS", height_range="10m < hUT <= 300m",
        pathloss=r"PL = 20\log_{10}(d)", notes=["Note 2"],
    )
    assert entry.scenario == "RMa-AV"
    assert entry.notes == ["Note 2"]


def test_pathloss_delta_entry_defaults_notes():
    entry = PathlossDeltaEntry(
        scenario="UMa-AV", condition="NLOS", height_range="x", pathloss="According to Table 7.4.1-1 of [4]",
    )
    assert entry.notes == []


def test_pathloss_delta_entry_invalid_condition_rejected():
    with pytest.raises(ValidationError):
        PathlossDeltaEntry(scenario="RMa-AV", condition="O2I", height_range="x", pathloss="y")


def test_valid_alternative_1_entry_validates():
    entry = Alternative1DesiredParametersEntry(
        scenario="RMa-AV", condition="LOS", asa_deg="0.2", asd_deg="0.2",
        zsa_deg="0.1", zsd_deg="0.1", desired_k_db="20", desired_ds_ns="10",
    )
    assert entry.desired_k_db == "20"


def test_alternative_1_entry_missing_field_rejected():
    with pytest.raises(ValidationError):
        Alternative1DesiredParametersEntry(
            scenario="RMa-AV", condition="LOS", asa_deg="0.2", asd_deg="0.2",
            zsa_deg="0.1", zsd_deg="0.1", desired_k_db="20",  # desired_ds_ns missing
        )


def test_valid_alternative_2_entry_validates():
    entry = Alternative2ModifiedParameterEntry(
        scenario="UMa-AV", parameter="DS", condition="NLOS",
        mu=r"0.0965\log_{10}(h_{UT}) - 7.503", sigma=r"0.9745\exp(-0.0045 h_{UT})",
    )
    assert entry.parameter == "DS"


def test_alternative_2_entry_invalid_parameter_rejected():
    with pytest.raises(ValidationError):
        Alternative2ModifiedParameterEntry(
            scenario="UMa-AV", parameter="NOTAPARAM", condition="LOS", mu="x", sigma="y",
        )


# --- TR 38.901 §7.9 (ISAC) models ---
def _valid_rcs2_kwargs(**overrides):
    kwargs = dict(
        target="Vehicle with single scattering point", scattering_point="Front",
        phi_center_deg="0", phi_3db_deg="40.54", theta_center_deg="71.75", theta_3db_deg="29.13",
        g_max="15.52", sigma_max="8.45", range_theta_deg="[30,180]", range_phi_deg="[-45, 45)",
        lg_sigma_m_dbsm="11.25", sigma_sigmaS_db="3.41",
    )
    kwargs.update(overrides)
    return kwargs


def test_valid_rcs_model_2_entry_validates():
    entry = RcsModel2Entry(**_valid_rcs2_kwargs())
    assert entry.scattering_point == "Front"
    assert entry.phi_3db_deg == "40.54"
    assert entry.range_phi_deg == "[-45, 45)"


def test_rcs_model_2_entry_missing_field_rejected():
    kwargs = _valid_rcs2_kwargs()
    del kwargs["g_max"]
    with pytest.raises(ValidationError):
        RcsModel2Entry(**kwargs)


def test_valid_sensing_scenario_single_and_human():
    single = SensingScenarioParameter(scenario_type="UAV", parameter="LOS/NLOS", value="LOS and NLOS")
    assert single.value == "LOS and NLOS" and single.indoor_value is None
    human = SensingScenarioParameter(
        scenario_type="Human", parameter="Outdoor/indoor", indoor_value="Indoor", outdoor_value="Outdoor",
    )
    assert human.value is None and human.indoor_value == "Indoor"


def test_sensing_scenario_invalid_family_rejected():
    with pytest.raises(ValidationError):
        SensingScenarioParameter(scenario_type="Spaceship", parameter="x", value="y")


def test_valid_xpr_entry_validates():
    entry = XprEntry(target="UAV", mu_xpr_db="13.75", sigma_xpr_db="7.07")
    assert entry.mu_xpr_db == "13.75"


def test_los_condition_entry_invalid_case_rejected():
    with pytest.raises(ValidationError):
        LosConditionEntry(case="8", reference_scenario="x", applicability_range="y")


def test_valid_los_condition_entry():
    entry = LosConditionEntry(case="9", reference_scenario="LOS probability is 100%", applicability_range="...")
    assert entry.case == "9"


# --- TR 38.901 §7.9.4/7.9.5/7.9.6 (continuation) models ---
def test_valid_background_channel_param_entry():
    entry = BackgroundChannelParamEntry(
        sensing_mode="TRP monostatic", scenario="UMi",
        alpha_d="6.1996", beta_d="0.1558", c_d="15.2697",
        alpha_h="12.0487", beta_h="2.3261", c_h="0.0157",
    )
    assert entry.alpha_d == "6.1996"
    # AV entries carry height-dependent formulas in the same str fields.
    av = BackgroundChannelParamEntry(
        sensing_mode="UT monostatic (aerial UE)", scenario="UMa-AV",
        alpha_d="0.83 + 0.00015h", beta_d="1/(536.305 + 1.0279h)", c_d="13.824 + 0.03085h",
        alpha_h="0.9054 - 0.0001117h", beta_h="1/(38.672 - 0.04658h)", c_h="25.4898 - 0.02398h",
    )
    assert "h" in av.beta_d


def test_background_channel_param_missing_field_rejected():
    with pytest.raises(ValidationError):
        BackgroundChannelParamEntry(sensing_mode="TRP monostatic", scenario="UMi", alpha_d="1")


def test_valid_spatial_consistency_entry():
    entry = SpatialConsistencyCorrelationEntry(parameter="Delays", correlation_type="Link-correlated")
    assert entry.correlation_type == "Link-correlated"


def test_valid_calibration_assumption_single_and_two_column():
    single = CalibrationAssumption(table="7.9.6.1-1", parameter="Scenario", value="UMa-AV")
    assert single.value == "UMa-AV" and single.indoor_value is None
    two = CalibrationAssumption(table="7.9.6.1-2", parameter="UT height",
                                indoor_value="1m", outdoor_value="1.5m")
    assert two.value is None and two.indoor_value == "1m"


def test_calibration_assumption_missing_table_rejected():
    with pytest.raises(ValidationError):
        CalibrationAssumption(parameter="Scenario", value="UMa-AV")
