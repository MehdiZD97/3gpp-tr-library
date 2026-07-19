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

`section()` is cached per (section_id, version) -- repeated calls don't
re-read or re-validate the YAML.
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from .models import (
    LosProbabilityEntry,
    O2IPenetrationLoss,
    PathlossEntry,
    Section74Data,
    ShadowFadingAutocorrelation,
)

DEFAULT_VERSION = "v19.4.0"

# This file lives at tools/tr_api/tr38901.py; the repo root is two levels up.
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Maps a processed section id to its data file, relative to TR-38.901/<version>/.
_SECTION_DATA_PATHS = {
    "7.4": "07-channel-models/7.4-pathloss.yaml",
}


class SectionNotFoundError(LookupError):
    """Raised when a section id or version has no processed data available."""


class ScenarioNotFoundError(LookupError):
    """Raised when a lookup's scenario/condition/variant doesn't match any entry."""


class Section:
    """A single processed TR 38.901 section's structured data (e.g. clause "7.4")."""

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


@lru_cache(maxsize=None)
def section(section_id: str, version: str = DEFAULT_VERSION) -> Section:
    """Load and validate a processed TR 38.901 section's data."""
    if section_id not in _SECTION_DATA_PATHS:
        raise SectionNotFoundError(
            f"No data available for TR 38.901 section {section_id!r}. "
            f"Processed sections: {sorted(_SECTION_DATA_PATHS)}"
        )
    yaml_path = _REPO_ROOT / "TR-38.901" / version / _SECTION_DATA_PATHS[section_id]
    if not yaml_path.is_file():
        raise SectionNotFoundError(
            f"No data file for TR 38.901 §{section_id} version {version!r} -- expected {yaml_path}"
        )
    with open(yaml_path) as f:
        raw = yaml.safe_load(f)
    data = Section74Data(**raw)
    return Section(section_id, version, data)
