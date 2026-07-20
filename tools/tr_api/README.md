# tr_api

Typed Python access to [3gpp-tr-library](../../README.md)'s structured 3GPP TR data — for simulation code that needs pathloss formulas, LOS probability, penetration loss, and related parameters without parsing YAML/CSV by hand.

## Install

From a separate project's environment, pointed at wherever this repo is cloned locally:

```sh
pip install -e /path/to/3gpp-tr-library/tools/tr_api
```

This is an editable install: `tr_api` reads data directly from the cloned repo's `TR-*/` directories at call time, so it always reflects the repo's current state without needing to be rebuilt or republished.

## Usage

```python
from tr_api import tr38901

# --- §7.4: Pathloss, LOS probability and penetration modelling ---
entry = tr38901.section("7.4").pathloss(scenario="UMi-StreetCanyon", condition="NLOS")
entry.formula                # LaTeX string
entry.shadow_fading_std_db   # list[ShadowFadingStd] -- a Pydantic model, not a raw dict

los = tr38901.section("7.4").los_probability(scenario="UMa")

o2i = tr38901.section("7.4").o2i_penetration_loss
o2i.materials                              # Table 7.4.3-1
o2i.building_models                        # Table 7.4.3-2
o2i.building_single_frequency_below_6ghz   # Table 7.4.3-3
o2i.car_penetration_loss                   # §7.4.3.2

autocorr = tr38901.section("7.4").shadow_fading_autocorrelation

# --- §7.5: Fast fading model ---
lsp = tr38901.section("7.5").channel_model_parameters(scenario="UMa", condition="NLOS")
lsp.mu_lgDS                  # carrier-frequency-dependent formula, as a string (Table 7.5-6)
lsp.corr_ASD_DS              # cross-correlation entries live on the same model

zsd = tr38901.section("7.5").zsd_zod_offset(scenario="UMa", condition="NLOS")  # Tables 7.5-7..12

notations = tr38901.section("7.5").notations                              # Table 7.5-1
scaling = tr38901.section("7.5").scaling_factors_aoa_aod_generation       # Table 7.5-2
ray_offsets = tr38901.section("7.5").ray_offset_angles                    # Table 7.5-3
sub_clusters = tr38901.section("7.5").sub_cluster_info                    # Table 7.5-5
```

`section()` defaults to the latest processed version (currently `v19.4.0`) and accepts an explicit `version=` keyword otherwise. It's a real dispatcher: each section id resolves to its own YAML file, Pydantic model, and accessor class (see `_SECTION_REGISTRY` in `tr38901.py`) rather than assuming every section shares one shape. A lookup for a scenario/condition/variant that doesn't exist raises `tr38901.ScenarioNotFoundError` with the list of what *is* available; an unprocessed section or version raises `tr38901.SectionNotFoundError`, listing what's actually processed -- neither returns `None` or a bare `KeyError`.

## Organization

- `tr_api.models` — the Pydantic models. `PathlossEntry` is TR-agnostic (see `schemas/pathloss.yaml`); everything else — `LosProbabilityEntry`, `O2IPenetrationLoss` and its sub-models, `ShadowFadingAutocorrelation` (§7.4-specific), and `ChannelModelParameterEntry`, `ZsdZodOffsetEntry`, `NotationEntry`, `ScalingFactorEntry`, `RayOffsetAngle`, `SubClusterInfo` (§7.5-specific) — is named for what it actually is rather than a generality it doesn't have.
- `tr_api.tr38901` — the TR 38.901 API surface (`section()`, `Section74`, `Section75`). A `tr36777` sibling module is the natural place for TR 36.777 support once that TR is processed.

TR 38.901 §7.4 and §7.5 are available today; `tr38901.section()` raises `SectionNotFoundError` for anything else, listing what's actually processed.
