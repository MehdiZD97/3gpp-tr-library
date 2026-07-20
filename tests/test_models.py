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
    ChannelModelParameterEntry,
    PathlossDeltaEntry,
    PathlossEntry,
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
