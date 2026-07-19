"""
Pydantic models for the structured data this library produces.

`PathlossEntry` is TR-agnostic and shared across TRs, matching the shape
documented in `schemas/pathloss.yaml` -- any TR clause presenting a pathloss
table in the "scenario -> LOS/NLOS formula + shadow fading std +
applicability range" shape should validate against this model rather than
a new one.

The remaining models (`LosProbabilityEntry`, `O2IPenetrationLoss` and its
sub-models, `ShadowFadingAutocorrelation`) are section-specific -- real for
TR 38.901 clause 7.4, but not assumed to generalize the way `PathlossEntry`
does. They live here (not in `schemas/`) precisely to keep that boundary:
`schemas/` holds only what's genuinely reusable across TRs.

Used by both `tools/verify_tables.py` (validation) and `tools/tr_api`
(typed return values) -- one model, two jobs.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ShadowFadingStd(BaseModel):
    condition: Optional[str] = None
    value_db: float


class PathlossEntry(BaseModel):
    """Shared across TRs -- see `schemas/pathloss.yaml`."""

    scenario: str
    condition: Literal["LOS", "NLOS"]
    variant: Optional[str] = None
    formula: str
    formula_ref: Optional[str] = None
    shadow_fading_std_db: List[ShadowFadingStd] = Field(min_length=1)
    applicability_range: str
    notes: List[str] = Field(default_factory=list)


class LosProbabilityEntry(BaseModel):
    """Section-specific (TR 38.901 §7.4.2) -- not part of the shared pathloss schema."""

    scenario: str
    formula: str
    notes: List[str] = Field(default_factory=list)


class O2IMaterial(BaseModel):
    material: str
    formula: str
    notes: List[str] = Field(default_factory=list)


class O2IBuildingModel(BaseModel):
    model: str
    pl_tw_formula: str
    pl_in_formula: str
    std_p_db: float


class O2IBuildingSingleFrequencyBelow6GHz(BaseModel):
    pl_tw_db: float
    pl_in_formula: str
    sigma_p_db: float
    sigma_sf_db: float
    note: str


class O2ICarPenetrationLoss(BaseModel):
    formula: str
    formula_ref: Optional[str] = None
    mu_db: float
    mu_metallized_windows_db: float
    sigma_p_db: float
    applicable_range_ghz: str


class O2IPenetrationLoss(BaseModel):
    """Section-specific (TR 38.901 §7.4.3) -- four distinct sub-shapes, not one table."""

    materials: List[O2IMaterial]
    building_models: List[O2IBuildingModel]
    building_single_frequency_below_6ghz: O2IBuildingSingleFrequencyBelow6GHz
    car_penetration_loss: O2ICarPenetrationLoss


class ShadowFadingAutocorrelation(BaseModel):
    """Section-specific (TR 38.901 §7.4.4)."""

    formula: str
    formula_ref: Optional[str] = None
    note: str


class Section74Data(BaseModel):
    """The full validated shape of a `7.4-pathloss.yaml`-style section file."""

    pathloss: List[PathlossEntry]
    los_probability: List[LosProbabilityEntry]
    o2i_penetration_loss: O2IPenetrationLoss
    shadow_fading_autocorrelation: ShadowFadingAutocorrelation
