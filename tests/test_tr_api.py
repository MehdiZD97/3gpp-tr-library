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
        tr38901.section("7.6")
    message = str(exc_info.value)
    assert "7.6" in message
    assert "7.4" in message and "7.5" in message and "7.9" in message  # lists what *is* processed


def test_section_lookup_for_unknown_version_raises_informative_error():
    with pytest.raises(SectionNotFoundError):
        tr38901.section("7.4", version="v0.0.0")


def test_known_good_channel_model_parameters_lookup_returns_expected_typed_value():
    entry = tr38901.section("7.5").channel_model_parameters(scenario="UMi - Street Canyon", condition="LOS")
    assert entry.mu_K == "9"
    assert entry.number_of_clusters == "12"
    assert type(entry).__name__ == "ChannelModelParameterEntry"


def test_channel_model_parameters_lookup_for_missing_scenario_raises_informative_error():
    with pytest.raises(ScenarioNotFoundError) as exc_info:
        tr38901.section("7.5").channel_model_parameters(scenario="Mars-Colony", condition="LOS")
    message = str(exc_info.value)
    assert "Mars-Colony" in message
    assert "Available" in message


def test_zsd_zod_offset_lookup_returns_expected_value():
    entry = tr38901.section("7.5").zsd_zod_offset(scenario="SMa", condition="LOS")
    assert entry.mu_lgZSD == "0.14"


def test_zsd_zod_offset_lookup_for_missing_scenario_raises_informative_error():
    with pytest.raises(ScenarioNotFoundError) as exc_info:
        tr38901.section("7.5").zsd_zod_offset(scenario="Mars-Colony", condition="LOS")
    assert "Mars-Colony" in str(exc_info.value)


def test_7_5_small_table_accessors():
    section = tr38901.section("7.5")
    assert len(section.notations) == 16
    assert len(section.sub_cluster_info) == 3
    assert any(e.num_clusters == 12 for e in section.scaling_factors_aoa_aod_generation)


def test_both_sections_usable_from_same_import():
    # The dispatcher refactor's actual risk: §7.4's surface must survive
    # unchanged now that section() resolves to different accessor classes.
    pathloss = tr38901.section("7.4").pathloss(scenario="RMa", condition="LOS")
    lsp = tr38901.section("7.5").channel_model_parameters(scenario="RMa", condition="LOS")
    assert type(pathloss).__name__ == "PathlossEntry"
    assert type(lsp).__name__ == "ChannelModelParameterEntry"


# ---------------------------------------------------------------------------
# TR 38.901 §7.9 (Channel model(s) for ISAC) -- the third §-section, registered
# via the same one-line _SECTION_REGISTRY + shared TRLoader (no loader change).
# ---------------------------------------------------------------------------
def test_known_good_rcs_model_2_lookup_returns_expected_typed_value():
    entry = tr38901.section("7.9").rcs_model_2(
        target="Vehicle with single scattering point", scattering_point="Front"
    )
    assert entry.phi_3db_deg == "40.54"
    assert entry.lg_sigma_m_dbsm == "11.25"
    assert type(entry).__name__ == "RcsModel2Entry"


def test_rcs_model_1_and_xpr_lookups():
    assert tr38901.section("7.9").rcs_model_1(target="UAV with small size").lg_sigma_m_dbsm == "-12.81"
    assert tr38901.section("7.9").xpr(target="Vehicle").mu_xpr_db == "21.12"


def test_reference_channel_model_and_los_condition_lookups():
    assert tr38901.section("7.9").reference_channel_model(case="4").rx == "aerial UE"
    rows = tr38901.section("7.9").los_condition(case="9")
    assert isinstance(rows, list) and len(rows) == 4


def test_section_7_9_small_table_accessors():
    section = tr38901.section("7.9")
    assert len(section.sensing_scenarios) == 53
    assert len(section.rcs_model_2_k_parameters) == 4
    assert len(section.target_channel_links) == 18
    assert len(section.background_channel_links) == 16


def test_rcs_model_2_lookup_for_missing_target_raises_informative_error():
    with pytest.raises(ScenarioNotFoundError) as exc_info:
        tr38901.section("7.9").rcs_model_2(target="Spaceship", scattering_point="Front")
    message = str(exc_info.value)
    assert "Spaceship" in message and "Available" in message


def test_los_condition_for_missing_case_raises_informative_error():
    with pytest.raises(ScenarioNotFoundError) as exc_info:
        tr38901.section("7.9").los_condition(case="42")
    assert "42" in str(exc_info.value)


def test_all_three_sections_usable_from_same_import():
    # §7.4/§7.5's surfaces must survive §7.9's registry addition unchanged.
    assert type(tr38901.section("7.4").pathloss(scenario="RMa", condition="LOS")).__name__ == "PathlossEntry"
    assert type(tr38901.section("7.5").channel_model_parameters(scenario="RMa", condition="LOS")).__name__ == "ChannelModelParameterEntry"
    assert type(tr38901.section("7.9").xpr(target="UAV")).__name__ == "XprEntry"


# ---------------------------------------------------------------------------
# TR 36.777 Annex B -- the second TR, accessed via annex() rather than
# section(). Exercises the shared-loader generalization from a caller's view.
# ---------------------------------------------------------------------------
from tr_api import tr36777  # noqa: E402


def test_annex_b_pathloss_returns_list_of_height_bands():
    bands = tr36777.annex("B").pathloss(scenario="RMa-AV", condition="LOS")
    assert isinstance(bands, list) and len(bands) == 2
    assert type(bands[0]).__name__ == "PathlossDeltaEntry"
    # One terrestrial-baseline row, one aerial-specific formula row.
    assert any("According to" in b.pathloss for b in bands)
    assert any("PL_{RMa-AV-LOS}" in b.pathloss for b in bands)


def test_annex_b_alternative_1_returns_single_typed_entry():
    entry = tr36777.annex("B").alternative_1(scenario="UMa-AV", condition="NLOS")
    assert entry.asa_deg == "1"
    assert entry.desired_ds_ns == "30"
    assert type(entry).__name__ == "Alternative1DesiredParametersEntry"


def test_annex_b_alternative_2_returns_single_typed_entry():
    entry = tr36777.annex("B").alternative_2(scenario="RMa-AV", parameter="K", condition="LOS")
    assert entry.mu == r"22.55\log_{10}(h_{UT}) - 4.72"


def test_annex_b_lookup_for_missing_scenario_raises_informative_error():
    with pytest.raises(tr36777.ScenarioNotFoundError) as exc_info:
        tr36777.annex("B").alternative_1(scenario="Mars-AV", condition="LOS")
    assert "Mars-AV" in str(exc_info.value)


def test_annex_lookup_for_unprocessed_annex_raises_informative_error():
    with pytest.raises(tr36777.SectionNotFoundError) as exc_info:
        tr36777.annex("Z")
    message = str(exc_info.value)
    assert "Z" in message and "'B'" in message  # lists what *is* processed


def test_annex_caching_returns_same_instance():
    assert tr36777.annex("B") is tr36777.annex("B")


def test_shared_loader_errors_are_the_same_type_across_trs():
    # The dispatcher generalization moved SectionNotFoundError/ScenarioNotFoundError
    # into the shared _loader; both TR modules must raise the *same* classes,
    # so a caller can catch one regardless of which TR raised it.
    from tr_api._loader import ScenarioNotFoundError as BaseScenario
    from tr_api._loader import SectionNotFoundError as BaseSection

    assert tr38901.SectionNotFoundError is BaseSection
    assert tr36777.SectionNotFoundError is BaseSection
    assert tr38901.ScenarioNotFoundError is BaseScenario
    assert tr36777.ScenarioNotFoundError is BaseScenario


def test_both_trs_usable_from_same_import():
    from tr_api import tr36777 as t36, tr38901 as t38
    pathloss = t38.section("7.4").pathloss(scenario="RMa", condition="LOS")
    aerial = t36.annex("B").pathloss(scenario="RMa-AV", condition="LOS")
    assert type(pathloss).__name__ == "PathlossEntry"
    assert isinstance(aerial, list)
