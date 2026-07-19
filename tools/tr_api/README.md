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
```

`section()` defaults to the latest processed version (currently `v19.4.0`) and accepts an explicit `version=` keyword otherwise. A lookup for a scenario/condition/variant that doesn't exist raises `tr38901.ScenarioNotFoundError` with the list of what *is* available, rather than returning `None` or a bare `KeyError`.

## Organization

- `tr_api.models` — the Pydantic models (`PathlossEntry`, `LosProbabilityEntry`, `O2IPenetrationLoss` and its sub-models, `ShadowFadingAutocorrelation`). `PathlossEntry` is TR-agnostic (see `schemas/pathloss.yaml`); the rest are TR 38.901 §7.4-specific.
- `tr_api.tr38901` — the TR 38.901 API surface (`section()`, `Section`). A `tr36777` sibling module is the natural place for TR 36.777 support once that TR is processed.

Only TR 38.901 §7.4 is available today; `tr38901.section()` raises `SectionNotFoundError` for anything else, listing what's actually processed.
