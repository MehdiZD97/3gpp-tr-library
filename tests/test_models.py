"""
Tests for tools/tr_api/models.py's Pydantic models: a valid entry validates
and produces the expected typed access; a malformed one (missing required
field, wrong type, invalid enum-like value) is rejected.

Requires tr_api to be installed (`pip install -e tools/tr_api`) -- see
docs/CONTRIBUTING.md's Development setup section.
"""
import pytest
from pydantic import ValidationError
from tr_api.models import ChannelModelParameterEntry, PathlossEntry, ZsdZodOffsetEntry


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
