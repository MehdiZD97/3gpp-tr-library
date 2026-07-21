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
from typing import Dict, List, Literal, Optional

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


# ---------------------------------------------------------------------------
# TR 38.901 section 7.5 (Fast fading model) -- section-specific, like the
# non-pathloss §7.4 models above. `ChannelModelParameterEntry` in particular
# is named for what it actually is (the TR's own "Channel model parameters"
# table, Table 7.5-6) rather than "CrossCorrelationMatrix" or similar --
# cross-correlations are only 21 of its 49 parameter rows, not the whole
# shape. Nearly every field is `str`, not `float`: nearly half the TR's own
# cells are carrier-frequency-dependent formulas or "N/A", not bare numbers.
# ---------------------------------------------------------------------------
class NotationEntry(BaseModel):
    """Section-specific (TR 38.901 Table 7.5-1)."""

    parameter: str
    notation: str


class ScalingFactorEntry(BaseModel):
    """One (# clusters -> scaling factor) pair from Table 7.5-2 or 7.5-4."""

    num_clusters: int
    c_phi_nlos: Optional[float] = None
    c_theta_nlos: Optional[float] = None


class RayOffsetAngle(BaseModel):
    """Section-specific (TR 38.901 Table 7.5-3)."""

    ray_numbers: str
    offset_angle: float


class SubClusterInfo(BaseModel):
    """Section-specific (TR 38.901 Table 7.5-5)."""

    sub_cluster: int
    mapping_to_rays: str
    power_fraction: str
    delay_offset: str


class ChannelModelParameterEntry(BaseModel):
    """
    One scenario/condition column of Table 7.5-6 -- the master large-scale
    parameter table. Field names match the YAML/CSV keys. Almost everything
    here is `str` rather than `float` because many of the table's cells are
    carrier-frequency-dependent formulas or "N/A", not bare numbers (see
    `7.5-fast-fading.md`'s own note).
    """

    scenario: str
    condition: Literal["LOS", "NLOS", "O2I"]

    mu_lgDS: str
    sigma_lgDS: str
    mu_lgASD: str
    sigma_lgASD: str
    mu_lgASA: str
    sigma_lgASA: str
    mu_lgZSA: str
    sigma_lgZSA: str
    sigma_SF: str
    mu_K: str
    sigma_K: str

    corr_ASD_DS: str
    corr_ASA_DS: str
    corr_ASA_SF: str
    corr_ASD_SF: str
    corr_DS_SF: str
    corr_ASD_ASA: str
    corr_ASD_K: str
    corr_ASA_K: str
    corr_DS_K: str
    corr_SF_K: str
    corr_ZSD_SF: str
    corr_ZSA_SF: str
    corr_ZSD_K: str
    corr_ZSA_K: str
    corr_ZSD_DS: str
    corr_ZSA_DS: str
    corr_ZSD_ASD: str
    corr_ZSA_ASD: str
    corr_ZSD_ASA: str
    corr_ZSA_ASA: str
    corr_ZSD_ZSA: str

    delay_scaling_parameter_r_tau: str
    mu_XPR: str
    sigma_XPR: str
    number_of_clusters: str
    number_of_rays_per_cluster: str
    cluster_DS_ns: str
    cluster_ASD_deg: str
    cluster_ASA_deg: str
    cluster_ZSA_deg: str
    per_cluster_shadowing_std_zeta_db: str

    corr_distance_DS_m: str
    corr_distance_ASD_m: str
    corr_distance_ASA_m: str
    corr_distance_SF_m: str
    corr_distance_K_m: str
    corr_distance_ZSA_m: str
    corr_distance_ZSD_m: str


class ZsdZodOffsetEntry(BaseModel):
    condition: Literal["LOS", "NLOS", "O2I"]
    mu_lgZSD: str
    sigma_lgZSD: str
    mu_offset_ZOD: str


class ZsdZodOffsetTable(BaseModel):
    """One of Tables 7.5-7 through 7.5-12 (one per scenario)."""

    tr_table: str
    note: Optional[str] = None
    entries: List[ZsdZodOffsetEntry]


class Section75Data(BaseModel):
    """The full validated shape of a `7.5-fast-fading.yaml`-style section file."""

    notations: List[NotationEntry]
    scaling_factors_aoa_aod_generation: List[ScalingFactorEntry]
    ray_offset_angles: List[RayOffsetAngle]
    scaling_factors_zoa_zod_generation: List[ScalingFactorEntry]
    sub_cluster_info: List[SubClusterInfo]
    channel_model_parameters: List[ChannelModelParameterEntry]
    zsd_zod_offset_parameters: Dict[str, ZsdZodOffsetTable]


# ---------------------------------------------------------------------------
# TR 36.777 Annex B (Channel modelling details) -- the aerial-UE (drone)
# channel model. Every model here is TR 36.777-specific: these are height-
# dependent *deltas* to TR 38.901's terrestrial UMa/UMi/RMa models, not a
# generic reusable shape, so they stay out of schemas/ (same restraint as
# the §7.4/§7.5 section-specific models above). Formula-bearing fields are
# `str` (LaTeX or an "According to ... of [4]" reference), like §7.5's
# formula cells -- see the section .md's verification note on why TR 36.777
# formula content is PDF-visual single-source.
# ---------------------------------------------------------------------------
class LosProbabilityDeltaEntry(BaseModel):
    """One (scenario, height band) row of Table B-1."""

    scenario: str
    height_range: str
    los_probability: str
    notes: List[str] = Field(default_factory=list)


class PathlossDeltaEntry(BaseModel):
    """One (scenario, condition, height band) row of Table B-2."""

    scenario: str
    condition: Literal["LOS", "NLOS"]
    height_range: str
    pathloss: str
    notes: List[str] = Field(default_factory=list)


class ShadowFadingDeltaEntry(BaseModel):
    """One (scenario, condition, height band) row of Table B-3."""

    scenario: str
    condition: Literal["LOS", "NLOS"]
    height_range: str
    sf_std: str


class FastFadingModelSelectionEntry(BaseModel):
    """One (scenario, height band) row of Table B-4."""

    scenario: str
    height_range: str
    model: str


class Alternative1DesiredParametersEntry(BaseModel):
    """One (scenario, condition) row of Table B.1.1-1 / B.1.1-2 (Alternative 1)."""

    scenario: str
    condition: Literal["LOS", "NLOS"]
    asa_deg: str
    asd_deg: str
    zsa_deg: str
    zsd_deg: str
    desired_k_db: str
    desired_ds_ns: str


class Alternative2ModifiedParameterEntry(BaseModel):
    """One (scenario, parameter, condition) row of Table B.1.2-1 / B.1.2-2 (Alternative 2)."""

    scenario: str
    parameter: Literal["DS", "ASA", "ASD", "ZSA", "ZSD", "K"]
    condition: Literal["LOS", "NLOS"]
    mu: str
    sigma: str


class AnnexBData(BaseModel):
    """The full validated shape of a `B-channel-modelling.yaml`-style annex file."""

    los_probability: List[LosProbabilityDeltaEntry]
    los_probability_notes: Dict[str, str]
    pathloss: List[PathlossDeltaEntry]
    pathloss_notes: Dict[str, str]
    shadow_fading_std: List[ShadowFadingDeltaEntry]
    fast_fading_model_selection: List[FastFadingModelSelectionEntry]
    alternative_1_desired_parameters: List[Alternative1DesiredParametersEntry]
    alternative_2_modified_parameters: List[Alternative2ModifiedParameterEntry]
