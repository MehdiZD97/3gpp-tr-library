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

# --- §7.9: Channel model(s) for ISAC (Rel-19), full clause 7.9.0-7.9.6 ---
isac = tr38901.section("7.9")

# Radar-cross-section models for the sensing targets:
isac.rcs_model_1(target="UAV with small size")                             # Table 7.9.2.1-1
isac.rcs_model_2(target="Vehicle with single scattering point",
                 scattering_point="Front")                                 # Tables 7.9.2.1-2..7
isac.xpr(target="UAV").mu_xpr_db                                           # Table 7.9.2.2-1

# Reference channel model mapping and LOS-condition determination:
isac.reference_channel_model(case="4").reference_tr                        # Table 7.9.3-1
isac.los_condition(case="9")                                               # list of Table 7.9.3-5 rows

isac.sensing_scenarios                                                     # Tables 7.9.1-1..5
isac.rcs_model_2_k_parameters                                             # (k1, k2) per target, Eq. 7.9.2-3

# Fast-fading background-channel params (7.9.4.2), calibration (7.9.6), spatial consistency (7.9.5.1):
isac.background_channel_params(sensing_mode="TRP monostatic", scenario="UMi")   # Tables 7.9.4.2-1/2
isac.calibration(table="7.9.6.1-1")                                        # list of Table 7.9.6.1-1 rows
isac.spatial_consistency_correlation                                       # Table 7.9.5.1-1
```

```python
from tr_api import tr36777

# TR 36.777 Annex B -- aerial-UE (drone) channel model, accessed via annex():
b = tr36777.annex("B")

# The delta tables are multi-band per scenario/condition (terrestrial baseline
# below a height threshold, aerial-specific formula above it), so these return
# a *list* of the height-band rows:
b.pathloss(scenario="RMa-AV", condition="LOS")             # Table B-2
b.los_probability(scenario="UMa-AV")                        # Table B-1
b.shadow_fading_std(scenario="UMi-AV", condition="NLOS")    # Table B-3
b.fast_fading_model_selection(scenario="RMa-AV")            # Table B-4

# The Alternative 1/2 parameter tables are uniquely keyed, so these return a
# single entry:
b.alternative_1(scenario="RMa-AV", condition="LOS").desired_k_db          # Table B.1.1-1
b.alternative_2(scenario="UMa-AV", parameter="DS", condition="NLOS").mu   # Table B.1.2-2
```

`section()` / `annex()` default to each TR's latest processed version (`v19.4.0` for TR 38.901, `v15.0.0` for TR 36.777) and accept an explicit `version=` keyword otherwise. (§7.9 covers the full ISAC clause 7.9.0-7.9.6; its 32 target/background fast-fading equations live as LaTeX in the section `.md` rather than the queryable surface, per the §7.5 precedent for procedural equations.) Each id resolves to its own YAML file, Pydantic model, and accessor class (see each module's `_SECTION_REGISTRY` / `_ANNEX_REGISTRY`) rather than assuming every section shares one shape. A lookup for a scenario/condition/variant that doesn't exist raises `ScenarioNotFoundError` with the list of what *is* available; an unprocessed section/annex or version raises `SectionNotFoundError`, listing what's actually processed -- neither returns `None` or a bare `KeyError`.

## Introspection — discover what's available without reading source

You don't have to know section or parameter names in advance; the API can tell you. `tr_api.introspect` describes the whole surface by **runtime inspection** of the accessors (so it never drifts from them), and each TR module exposes `list_*` / `describe`:

```python
from tr_api import tr38901, tr36777, introspect

introspect.all_units()                         # every processed section + annex, both TRs
tr38901.list_sections()                        # -> [UnitInfo(key="7.4", title="Pathloss, ...", verb="section"), ...]
tr36777.list_annexes()                         # the annex parallel -- first-class alongside sections

unit = tr38901.describe("7.9")                  # full callable surface of a section
for m in unit.members:
    # m.name, m.kind ("method"/"property"), m.args (with .available values from the data),
    # m.returns (e.g. "RcsModel2Entry" / "list[CalibrationAssumption]"), m.returns_list
    ...
```

`describe(...)` reports, per method, its keyword args **and the values actually available for each** (pulled from the data, e.g. `rcs_model_2` → `target=[UAV with large size, ...], scattering_point=[Front, Left, ...]`). Properties (like `.notations`, `.sensing_scenarios`) are listed as direct-access, no-arg members. Both TRs are described identically — the lettered `annex()` is as first-class as the numbered `section()`.

## CLI — `tr-api`

Installing the package (`pip install -e tools/tr_api`) also installs a `tr-api` command, a **thin wrapper over the introspection layer** (no section knowledge of its own). Discover → describe → query, with no prior knowledge:

```console
$ tr-api list                       # every TR and its processed sections/annexes
$ tr-api describe tr38901 7.9        # a section's parameters, args, and available values
$ tr-api describe tr36777 B          # the annex, described the same way

# get: perform a lookup and print it readably
$ tr-api get tr38901 7.4 pathloss --scenario UMi-StreetCanyon --condition NLOS
$ tr-api get tr36777 B alternative_2 --scenario RMa-AV --parameter K --condition LOS

# dump: a whole parameter set as JSON/CSV for piping (machine output on stdout only)
$ tr-api dump tr38901 7.9 xpr --format json | jq '.[] | {target, mu_xpr_db}'
$ tr-api dump tr38901 7.5 channel_model_parameters --format csv > lsp.csv
```

`dump --format csv` matches the committed `tables/*.csv` where a single table exists (e.g. `channel_model_parameters` == `table-7.5-6.csv`). Unknown section/parameter/scenario prints the same "available: …" help the Python errors carry, to **stderr**, and exits non-zero — machine output stays clean for piping. The CLI uses only `argparse` (stdlib) — no added dependency.

## Organization

- `tr_api.models` — the Pydantic models. `PathlossEntry` is TR-agnostic (see `schemas/pathloss.yaml`); everything else is named for what it actually is: `LosProbabilityEntry` / `O2IPenetrationLoss` (+ sub-models) / `ShadowFadingAutocorrelation` (TR 38.901 §7.4), `ChannelModelParameterEntry` / `ZsdZodOffsetEntry` / `NotationEntry` / `ScalingFactorEntry` / `RayOffsetAngle` / `SubClusterInfo` (TR 38.901 §7.5), `SensingScenarioParameter` / `RcsModel1Entry` / `RcsModel2Entry` / `RcsModel2KParameter` / `XprEntry` / `ReferenceChannelModelEntry` / `TargetChannelLinkEntry` / `BackgroundChannelLinkEntry` / `LosConditionEntry` / `BackgroundChannelParamEntry` / `SpatialConsistencyCorrelationEntry` / `CalibrationAssumption` (TR 38.901 §7.9), and `PathlossDeltaEntry` / `LosProbabilityDeltaEntry` / `ShadowFadingDeltaEntry` / `FastFadingModelSelectionEntry` / `Alternative1DesiredParametersEntry` / `Alternative2ModifiedParameterEntry` (TR 36.777 Annex B).
- `tr_api._loader` — the TR-agnostic load/validate/cache machinery (`TRLoader`, `SectionNotFoundError`, `ScenarioNotFoundError`), shared by every per-TR module.
- `tr_api.tr38901` — TR 38.901's surface (`section()`, `Section74`, `Section75`, `Section79`, plus `list_sections()` / `describe()`).
- `tr_api.tr36777` — TR 36.777's surface (`annex()`, `AnnexB`, plus `list_annexes()` / `describe()`).
- `tr_api.introspect` — the self-describing surface (`UnitInfo`/`MemberInfo`, `all_units()`, `describe()`) derived by runtime inspection of the accessors, augmented by each accessor's small `_QUERYABLE` map (method → data field, so available values can be listed).
- `tr_api.cli` — the `tr-api` console command (`main(argv)`), a thin formatter over `tr_api.introspect`.

Adding a further TR is a new thin module (its registry + accessor classes + access verb) plus its models, not a copy of the loader. TR 38.901 §7.4/§7.5/§7.9 and TR 36.777 Annex B are available today.
