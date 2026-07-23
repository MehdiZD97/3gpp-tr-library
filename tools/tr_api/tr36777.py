"""
Python API for TR 36.777's processed annexes.

    from tr_api import tr36777

    b = tr36777.annex("B")

    b.pathloss(scenario="RMa-AV", condition="LOS")            # list of height-band rows (Table B-2)
    b.los_probability(scenario="UMa-AV")                       # list of height-band rows (Table B-1)
    b.shadow_fading_std(scenario="UMi-AV", condition="NLOS")   # list (Table B-3)
    b.fast_fading_model_selection(scenario="RMa-AV")           # list (Table B-4)

    b.alternative_1(scenario="RMa-AV", condition="LOS")        # single row (Table B.1.1-1)
    b.alternative_2(scenario="UMa-AV", parameter="DS", condition="NLOS")  # single row (Table B.1.2-2)

`annex()` is the access verb (parallel to TR 38.901's `section()`) since
TR 36.777's processed content is a lettered annex, not a numbered clause. It
uses the same shared TRLoader as `tr38901`, so results are cached per
(annex_id, version) and unknown ids/versions raise the same
`SectionNotFoundError`.

The delta tables (B-1..B-4) are inherently multi-band per scenario/condition
(a terrestrial-baseline row below a height threshold, an aerial-specific row
above it), so those lookups return a *list* of matching entries. The
Alternative 1/2 parameter tables are uniquely keyed, so those return a
single entry. All are aerial-UE modifications to TR 38.901 -- see this
annex's `depends_on` and its section .md.
"""
from typing import List

# Re-exported for symmetry with tr38901 (callers may import from either).
from ._loader import ScenarioNotFoundError, SectionNotFoundError, TRLoader
from .models import (
    Alternative1DesiredParametersEntry,
    Alternative2ModifiedParameterEntry,
    AnnexBData,
    FastFadingModelSelectionEntry,
    LosProbabilityDeltaEntry,
    PathlossDeltaEntry,
    ShadowFadingDeltaEntry,
)

DEFAULT_VERSION = "v15.0.0"

# The access verb / unit noun for this TR (a lettered annex, not a numbered
# clause), read by tr_api.introspect so it's described as first-class as
# TR 38.901's sections.
UNIT_KIND = "annex"

__all__ = [
    "annex", "AnnexB", "list_annexes", "describe", "UNIT_KIND",
    "ScenarioNotFoundError", "SectionNotFoundError", "DEFAULT_VERSION",
]


class AnnexB:
    """TR 36.777 Annex B (Channel modelling details) -- the aerial-UE channel model."""

    # Minimal explicit metadata for the introspection layer (see
    # Section74._QUERYABLE in tr38901.py): per lookup method, the data
    # attribute queried and each keyword arg's underlying entry field.
    _QUERYABLE = {
        "los_probability": ("los_probability", {"scenario": "scenario"}),
        "pathloss": ("pathloss", {"scenario": "scenario", "condition": "condition"}),
        "shadow_fading_std": ("shadow_fading_std", {"scenario": "scenario", "condition": "condition"}),
        "fast_fading_model_selection": ("fast_fading_model_selection", {"scenario": "scenario"}),
        "alternative_1": ("alternative_1_desired_parameters", {"scenario": "scenario", "condition": "condition"}),
        "alternative_2": ("alternative_2_modified_parameters",
                          {"scenario": "scenario", "parameter": "parameter", "condition": "condition"}),
    }

    def __init__(self, annex_id: str, version: str, data: AnnexBData):
        self.annex_id = annex_id
        self.version = version
        self._data = data

    def _require(self, matches, description):
        if not matches:
            raise ScenarioNotFoundError(
                f"No {description} in TR 36.777 Annex {self.annex_id} ({self.version})."
            )
        return matches

    def los_probability(self, *, scenario: str) -> List[LosProbabilityDeltaEntry]:
        matches = [e for e in self._data.los_probability if e.scenario == scenario]
        available = sorted({e.scenario for e in self._data.los_probability})
        return self._require(matches, f"LOS probability rows for scenario={scenario!r}; available scenarios: {available}")

    def pathloss(self, *, scenario: str, condition: str) -> List[PathlossDeltaEntry]:
        matches = [e for e in self._data.pathloss if e.scenario == scenario and e.condition == condition]
        available = sorted({(e.scenario, e.condition) for e in self._data.pathloss})
        return self._require(matches, f"pathloss rows for scenario={scenario!r}, condition={condition!r}; available: {available}")

    def shadow_fading_std(self, *, scenario: str, condition: str) -> List[ShadowFadingDeltaEntry]:
        matches = [e for e in self._data.shadow_fading_std if e.scenario == scenario and e.condition == condition]
        available = sorted({(e.scenario, e.condition) for e in self._data.shadow_fading_std})
        return self._require(matches, f"shadow-fading rows for scenario={scenario!r}, condition={condition!r}; available: {available}")

    def fast_fading_model_selection(self, *, scenario: str) -> List[FastFadingModelSelectionEntry]:
        matches = [e for e in self._data.fast_fading_model_selection if e.scenario == scenario]
        available = sorted({e.scenario for e in self._data.fast_fading_model_selection})
        return self._require(matches, f"fast-fading-selection rows for scenario={scenario!r}; available scenarios: {available}")

    def alternative_1(self, *, scenario: str, condition: str) -> Alternative1DesiredParametersEntry:
        for entry in self._data.alternative_1_desired_parameters:
            if entry.scenario == scenario and entry.condition == condition:
                return entry
        available = [(e.scenario, e.condition) for e in self._data.alternative_1_desired_parameters]
        raise ScenarioNotFoundError(
            f"No Alternative 1 desired-parameter entry for scenario={scenario!r}, condition={condition!r} "
            f"in TR 36.777 Annex {self.annex_id} ({self.version}). Available (scenario, condition): {available}"
        )

    def alternative_2(self, *, scenario: str, parameter: str, condition: str) -> Alternative2ModifiedParameterEntry:
        for entry in self._data.alternative_2_modified_parameters:
            if entry.scenario == scenario and entry.parameter == parameter and entry.condition == condition:
                return entry
        available = [(e.scenario, e.parameter, e.condition) for e in self._data.alternative_2_modified_parameters]
        raise ScenarioNotFoundError(
            f"No Alternative 2 modified-parameter entry for scenario={scenario!r}, parameter={parameter!r}, "
            f"condition={condition!r} in TR 36.777 Annex {self.annex_id} ({self.version}). "
            f"Available (scenario, parameter, condition): {available}"
        )


# Registry: annex id -> (YAML path relative to TR-36.777/<version>/, the
# Pydantic model that validates the whole file, the accessor class).
_ANNEX_REGISTRY = {
    "B": ("annex-b-channel-modelling/B-channel-modelling.yaml", AnnexBData, AnnexB),
}

_loader = TRLoader("TR-36.777", "TR 36.777", DEFAULT_VERSION, _ANNEX_REGISTRY)


def annex(annex_id: str, version: str = None) -> AnnexB:
    """Load and validate a processed TR 36.777 annex's data (cached per id+version)."""
    return _loader.load(annex_id, version)


def list_annexes(*, detail: bool = False, with_values: bool = False, version: str = None):
    """Discover the processed TR 36.777 annexes (real id + title) -- the annex
    parallel to tr38901.list_sections(). Returns `introspect.UnitInfo` objects."""
    from . import introspect
    return introspect.list_units(_loader, UNIT_KIND, "tr36777", detail=detail, with_values=with_values, version=version)


def describe(annex_id: str, *, with_values: bool = True, version: str = None):
    """Describe one annex's callable surface: methods, their keyword args and
    available values, and return types. Returns `introspect.UnitInfo`."""
    from . import introspect
    return introspect.describe_unit(_loader, UNIT_KIND, "tr36777", annex_id, with_values=with_values, version=version)
