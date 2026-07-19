"""
Tests for tools/tr_api's public API: a known-good call returns the expected
typed value; a lookup for a scenario/section that doesn't exist fails in a
sensible, informative way rather than returning None or a raw KeyError.

Requires tr_api to be installed (`pip install -e tools/tr_api`) -- see
docs/CONTRIBUTING.md's Development setup section.
"""
import pytest
from tr_api import tr38901
from tr_api.tr38901 import ScenarioNotFoundError, SectionNotFoundError


def test_known_good_pathloss_lookup_returns_expected_typed_value():
    entry = tr38901.section("7.4").pathloss(scenario="InH-Office", condition="LOS")
    assert entry.formula == "PL_{InH-LOS} = 32.4 + 17.3\\log_{10}(d_{3D}) + 20\\log_{10}(f_c)"
    assert entry.shadow_fading_std_db[0].value_db == 3
    assert type(entry).__name__ == "PathlossEntry"


def test_pathloss_lookup_for_missing_scenario_raises_informative_error():
    with pytest.raises(ScenarioNotFoundError) as exc_info:
        tr38901.section("7.4").pathloss(scenario="Mars-Colony", condition="LOS")
    message = str(exc_info.value)
    assert "Mars-Colony" in message
    assert "Available" in message


def test_los_probability_lookup_returns_expected_value():
    entry = tr38901.section("7.4").los_probability(scenario="InF-HH")
    assert entry.formula == "Pr_{LOS} = 1"


def test_los_probability_lookup_for_missing_scenario_raises_informative_error():
    with pytest.raises(ScenarioNotFoundError) as exc_info:
        tr38901.section("7.4").los_probability(scenario="Mars-Colony")
    assert "Mars-Colony" in str(exc_info.value)


def test_o2i_and_autocorrelation_accessors():
    section = tr38901.section("7.4")
    material_names = [m.material for m in section.o2i_penetration_loss.materials]
    assert "Concrete" in material_names
    assert section.shadow_fading_autocorrelation.formula_ref == "7.4-5"


def test_section_lookup_for_unprocessed_section_raises_informative_error():
    with pytest.raises(SectionNotFoundError) as exc_info:
        tr38901.section("7.5")
    message = str(exc_info.value)
    assert "7.5" in message
    assert "7.4" in message  # lists what *is* processed


def test_section_lookup_for_unknown_version_raises_informative_error():
    with pytest.raises(SectionNotFoundError):
        tr38901.section("7.4", version="v0.0.0")
