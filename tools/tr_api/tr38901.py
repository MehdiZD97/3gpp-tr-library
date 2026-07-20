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

`section()` is cached per (section_id, version) -- repeated calls don't
re-read or re-validate the YAML. It's a genuine dispatcher, not a
single-shape assumption: each registered section id maps to its own data
file, Pydantic model, and accessor class, since §7.4 and §7.5 don't share a
data shape and future sections won't necessarily either.
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from .models import (
    ChannelModelParameterEntry,
    LosProbabilityEntry,
    O2IPenetrationLoss,
    PathlossEntry,
    RayOffsetAngle,
    ScalingFactorEntry,
    Section74Data,
    Section75Data,
    ShadowFadingAutocorrelation,
    SubClusterInfo,
    NotationEntry,
    ZsdZodOffsetEntry,
)

DEFAULT_VERSION = "v19.4.0"

# This file lives at tools/tr_api/tr38901.py; the repo root is two levels up.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class SectionNotFoundError(LookupError):
    """Raised when a section id or version has no processed data available."""


class ScenarioNotFoundError(LookupError):
    """Raised when a lookup's scenario/condition/variant doesn't match any entry."""


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


# Registry: section id -> (YAML path relative to TR-38.901/<version>/, the
# Pydantic model that validates the whole file, the accessor class wrapping
# it). Adding a processed section means adding one line here, not touching
# the dispatch logic in section() below.
_SECTION_REGISTRY = {
    "7.4": ("07-channel-models/7.4-pathloss.yaml", Section74Data, Section74),
    "7.5": ("07-channel-models/7.5-fast-fading.yaml", Section75Data, Section75),
}


@lru_cache(maxsize=None)
def section(section_id: str, version: str = DEFAULT_VERSION):
    """Load and validate a processed TR 38.901 section's data."""
    if section_id not in _SECTION_REGISTRY:
        raise SectionNotFoundError(
            f"No data available for TR 38.901 section {section_id!r}. "
            f"Processed sections: {sorted(_SECTION_REGISTRY)}"
        )
    rel_path, model_cls, accessor_cls = _SECTION_REGISTRY[section_id]
    yaml_path = _REPO_ROOT / "TR-38.901" / version / rel_path
    if not yaml_path.is_file():
        raise SectionNotFoundError(
            f"No data file for TR 38.901 §{section_id} version {version!r} -- expected {yaml_path}"
        )
    with open(yaml_path) as f:
        raw = yaml.safe_load(f)
    data = model_cls(**raw)
    return accessor_cls(section_id, version, data)
