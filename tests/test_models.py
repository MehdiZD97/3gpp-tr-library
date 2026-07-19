"""
Tests for tools/tr_api/models.py's Pydantic models: a valid entry validates
and produces the expected typed access; a malformed one (missing required
field, wrong type, invalid enum-like value) is rejected.

Requires tr_api to be installed (`pip install -e tools/tr_api`) -- see
docs/CONTRIBUTING.md's Development setup section.
"""
import pytest
from pydantic import ValidationError
from tr_api.models import PathlossEntry


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
