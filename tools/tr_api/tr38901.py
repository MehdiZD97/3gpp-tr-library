"""
Python API for TR 38.901's processed sections.

    from tr_api import tr38901

    entry = tr38901.section("7.4").pathloss(scenario="UMi-StreetCanyon", condition="NLOS")
    entry.shadow_fading_std_db      # a Pydantic model instance, not a raw dict

    los = tr38901.section("7.4").los_probability(scenario="UMa")

    o2i = tr38901.section("7.4").o2i_penetration_loss
    o2i.materials                   # Table 7.4.3-1
    o2i.building_models             # Table 7.4.3-2
    o2i.building_single_frequency_below_6ghz   # Table 7.4.3-3
    o2i.car_penetration_loss        # §7.4.3.2

    autocorr = tr38901.section("7.4").shadow_fading_autocorrelation

    lsp = tr38901.section("7.5").channel_model_parameters(scenario="UMa", condition="NLOS")
    lsp.mu_lgDS                     # carrier-frequency-dependent formula, as a string

    zsd = tr38901.section("7.5").zsd_zod_offset(scenario="UMa", condition="NLOS")

    notations = tr38901.section("7.5").notations   # Table 7.5-1

    isac = tr38901.section("7.9")                     # Channel model(s) for ISAC (Rel-19), full 7.9.0-7.9.6
    isac.rcs_model_2(target="Vehicle with single scattering point", scattering_point="Front")
    isac.xpr(target="UAV").mu_xpr_db                  # "13.75"
    isac.reference_channel_model(case="4").reference_tr
    isac.los_condition(case="9")                      # list of Table 7.9.3-5 rows
    isac.background_channel_params(sensing_mode="TRP monostatic", scenario="UMi")   # Table 7.9.4.2-1
    isac.calibration(table="7.9.6.1-1")               # list of Table 7.9.6.1-1 rows

`section()` is cached per (section_id, version) via the shared TRLoader --
repeated calls don't re-read or re-validate the YAML. Each registered
section id maps to its own data file, Pydantic model, and accessor class:
§7.4 and §7.5 don't share a data shape and future sections won't
necessarily either.

The TR-agnostic load/validate/cache machinery lives in `_loader.py` and is
shared with `tr36777` (and any future TR module); this file is just
TR 38.901's registry, accessor classes, and the `section()` verb.
"""
from typing import Optional

# Re-exported for backwards compatibility: callers import these from here.
from ._loader import ScenarioNotFoundError, SectionNotFoundError, TRLoader
from .models import (
    BackgroundChannelLinkEntry,
    BackgroundChannelParamEntry,
    CalibrationAssumption,
    ChannelModelParameterEntry,
    LosConditionEntry,
    LosProbabilityEntry,
    NotationEntry,
    O2IPenetrationLoss,
    PathlossEntry,
    RayOffsetAngle,
    RcsModel1Entry,
    RcsModel2Entry,
    RcsModel2KParameter,
    ReferenceChannelModelEntry,
    ScalingFactorEntry,
    Section74Data,
    Section75Data,
    Section79Data,
    SensingScenarioParameter,
    ShadowFadingAutocorrelation,
    SpatialConsistencyCorrelationEntry,
    SubClusterInfo,
    TargetChannelLinkEntry,
    XprEntry,
    ZsdZodOffsetEntry,
)

DEFAULT_VERSION = "v19.4.0"

__all__ = [
    "section", "Section74", "Section75", "Section79",
    "ScenarioNotFoundError", "SectionNotFoundError", "DEFAULT_VERSION",
]


class Section74:
    """TR 38.901 §7.4 (Pathloss, LOS probability and penetration modelling)."""

    def __init__(self, section_id: str, version: str, data: Section74Data):
        self.section_id = section_id
        self.version = version
        self._data = data

    def pathloss(self, *, scenario: str, condition: str, variant: Optional[str] = None) -> PathlossEntry:
        for entry in self._data.pathloss:
            if entry.scenario == scenario and entry.condition == condition and entry.variant == variant:
                return entry
        available = [(e.scenario, e.condition, e.variant) for e in self._data.pathloss]
        raise ScenarioNotFoundError(
            f"No pathloss entry for scenario={scenario!r}, condition={condition!r}, variant={variant!r} "
            f"in TR 38.901 §{self.section_id} ({self.version}). Available (scenario, condition, variant): {available}"
        )

    def los_probability(self, *, scenario: str) -> LosProbabilityEntry:
        for entry in self._data.los_probability:
            if entry.scenario == scenario:
                return entry
        available = [e.scenario for e in self._data.los_probability]
        raise ScenarioNotFoundError(
            f"No LOS probability entry for scenario={scenario!r} in TR 38.901 §{self.section_id} "
            f"({self.version}). Available scenarios: {available}"
        )

    @property
    def o2i_penetration_loss(self) -> O2IPenetrationLoss:
        return self._data.o2i_penetration_loss

    @property
    def shadow_fading_autocorrelation(self) -> ShadowFadingAutocorrelation:
        return self._data.shadow_fading_autocorrelation


class Section75:
    """TR 38.901 §7.5 (Fast fading model)."""

    def __init__(self, section_id: str, version: str, data: Section75Data):
        self.section_id = section_id
        self.version = version
        self._data = data

    def channel_model_parameters(self, *, scenario: str, condition: str) -> ChannelModelParameterEntry:
        for entry in self._data.channel_model_parameters:
            if entry.scenario == scenario and entry.condition == condition:
                return entry
        available = [(e.scenario, e.condition) for e in self._data.channel_model_parameters]
        raise ScenarioNotFoundError(
            f"No channel model parameter entry for scenario={scenario!r}, condition={condition!r} "
            f"in TR 38.901 §{self.section_id} ({self.version}). Available (scenario, condition): {available}"
        )

    def zsd_zod_offset(self, *, scenario: str, condition: str) -> ZsdZodOffsetEntry:
        table = self._data.zsd_zod_offset_parameters.get(scenario)
        if table is None:
            raise ScenarioNotFoundError(
                f"No ZSD/ZOD offset table for scenario={scenario!r} in TR 38.901 §{self.section_id} "
                f"({self.version}). Available scenarios: {sorted(self._data.zsd_zod_offset_parameters)}"
            )
        for entry in table.entries:
            if entry.condition == condition:
                return entry
        available = [e.condition for e in table.entries]
        raise ScenarioNotFoundError(
            f"No ZSD/ZOD offset entry for scenario={scenario!r}, condition={condition!r} in TR 38.901 "
            f"§{self.section_id} ({self.version}). Available conditions for {scenario!r}: {available}"
        )

    @property
    def notations(self) -> list[NotationEntry]:
        return self._data.notations

    @property
    def scaling_factors_aoa_aod_generation(self) -> list[ScalingFactorEntry]:
        return self._data.scaling_factors_aoa_aod_generation

    @property
    def scaling_factors_zoa_zod_generation(self) -> list[ScalingFactorEntry]:
        return self._data.scaling_factors_zoa_zod_generation

    @property
    def ray_offset_angles(self) -> list[RayOffsetAngle]:
        return self._data.ray_offset_angles

    @property
    def sub_cluster_info(self) -> list[SubClusterInfo]:
        return self._data.sub_cluster_info


class Section79:
    """TR 38.901 §7.9 (Channel model(s) for ISAC) -- the full clause 7.9.0-7.9.6.

    Covers scenarios (7.9.1), the physical-object / RCS model (7.9.2), the
    reference-channel-model mapping (7.9.3), the fast-fading background-channel
    parameters (7.9.4.2), spatial-consistency correlation (7.9.5.1), and the
    calibration "simulation assumptions" tables (7.9.6). The 32 target/background
    fast-fading equations (7.9.4/7.9.5) live as LaTeX in the section .md, not
    here (procedural, per the §7.5 precedent).
    """

    def __init__(self, section_id: str, version: str, data: Section79Data):
        self.section_id = section_id
        self.version = version
        self._data = data

    def rcs_model_1(self, *, target: str) -> RcsModel1Entry:
        for entry in self._data.rcs_model_1:
            if entry.sensing_target == target:
                return entry
        available = [e.sensing_target for e in self._data.rcs_model_1]
        raise ScenarioNotFoundError(
            f"No RCS model 1 entry for target={target!r} in TR 38.901 §{self.section_id} "
            f"({self.version}). Available targets: {available}"
        )

    def rcs_model_2(self, *, target: str, scattering_point: str) -> RcsModel2Entry:
        for entry in self._data.rcs_model_2:
            if entry.target == target and entry.scattering_point == scattering_point:
                return entry
        available = [(e.target, e.scattering_point) for e in self._data.rcs_model_2]
        raise ScenarioNotFoundError(
            f"No RCS model 2 entry for target={target!r}, scattering_point={scattering_point!r} "
            f"in TR 38.901 §{self.section_id} ({self.version}). Available (target, scattering_point): {available}"
        )

    def xpr(self, *, target: str) -> XprEntry:
        for entry in self._data.xpr:
            if entry.target == target:
                return entry
        available = [e.target for e in self._data.xpr]
        raise ScenarioNotFoundError(
            f"No XPR entry for target={target!r} in TR 38.901 §{self.section_id} "
            f"({self.version}). Available targets: {available}"
        )

    def reference_channel_model(self, *, case: str) -> ReferenceChannelModelEntry:
        for entry in self._data.reference_channel_models:
            if entry.case == str(case):
                return entry
        available = [e.case for e in self._data.reference_channel_models]
        raise ScenarioNotFoundError(
            f"No reference channel model for case={case!r} in TR 38.901 §{self.section_id} "
            f"({self.version}). Available cases: {available}"
        )

    def los_condition(self, *, case: str) -> list[LosConditionEntry]:
        matches = [e for e in self._data.los_condition_determination if e.case == str(case)]
        if not matches:
            available = sorted({e.case for e in self._data.los_condition_determination})
            raise ScenarioNotFoundError(
                f"No LOS condition rows for case={case!r} in TR 38.901 §{self.section_id} "
                f"({self.version}). Available cases: {available}"
            )
        return matches

    @property
    def sensing_scenarios(self) -> list[SensingScenarioParameter]:
        return self._data.sensing_scenarios

    @property
    def rcs_model_2_k_parameters(self) -> list[RcsModel2KParameter]:
        return self._data.rcs_model_2_k_parameters

    @property
    def target_channel_links(self) -> list[TargetChannelLinkEntry]:
        return self._data.target_channel_links

    @property
    def background_channel_links(self) -> list[BackgroundChannelLinkEntry]:
        return self._data.background_channel_links

    # --- 7.9.4 / 7.9.5 / 7.9.6 (Phase 7 continued) ---
    def background_channel_params(self, *, sensing_mode: str, scenario: str) -> BackgroundChannelParamEntry:
        """§7.9.4.2 background-channel Gamma-distribution params (Tables 7.9.4.2-1/2)."""
        for entry in self._data.background_channel_params:
            if entry.sensing_mode == sensing_mode and entry.scenario == scenario:
                return entry
        available = [(e.sensing_mode, e.scenario) for e in self._data.background_channel_params]
        raise ScenarioNotFoundError(
            f"No background channel params for sensing_mode={sensing_mode!r}, scenario={scenario!r} "
            f"in TR 38.901 §{self.section_id} ({self.version}). Available (sensing_mode, scenario): {available}"
        )

    def calibration(self, *, table: str) -> list[CalibrationAssumption]:
        """§7.9.6 calibration assumptions for one table id (e.g. '7.9.6.1-1')."""
        matches = [e for e in self._data.calibration_assumptions if e.table == table]
        if not matches:
            available = sorted({e.table for e in self._data.calibration_assumptions})
            raise ScenarioNotFoundError(
                f"No calibration assumptions for table={table!r} in TR 38.901 §{self.section_id} "
                f"({self.version}). Available tables: {available}"
            )
        return matches

    @property
    def spatial_consistency_correlation(self) -> list[SpatialConsistencyCorrelationEntry]:
        return self._data.spatial_consistency_correlation


# Registry: section id -> (YAML path relative to TR-38.901/<version>/, the
# Pydantic model that validates the whole file, the accessor class wrapping
# it). Adding a processed section means adding one line here.
_SECTION_REGISTRY = {
    "7.4": ("07-channel-models/7.4-pathloss.yaml", Section74Data, Section74),
    "7.5": ("07-channel-models/7.5-fast-fading.yaml", Section75Data, Section75),
    "7.9": ("07-channel-models/7.9-isac-channel-model.yaml", Section79Data, Section79),
}

_loader = TRLoader("TR-38.901", "TR 38.901", DEFAULT_VERSION, _SECTION_REGISTRY)


def section(section_id: str, version: str = None):
    """Load and validate a processed TR 38.901 section's data (cached per id+version)."""
    return _loader.load(section_id, version)
