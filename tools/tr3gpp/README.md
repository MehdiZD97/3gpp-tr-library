# tr3gpp

Typed Python access to [3gpp-tr-library](https://github.com/MehdiZD97/3gpp-tr-library)'s structured 3GPP TR data — for simulation code that needs pathloss formulas, LOS probability, penetration loss, and related parameters without parsing YAML/CSV by hand.

<!-- This file is the package's PyPI long description, so every link here must be
     an absolute URL: relative paths do not resolve on pypi.org. -->

Covers **TR 38.901 v19.4.0** §7.4 (pathloss, LOS probability, O2I penetration), §7.5 (fast fading), §7.6 (additional modelling components) and §7.9 (ISAC), plus **TR 36.777 v15.0.0** Annex B (aerial-UE deltas). Every value is hand-verified against multiple independent source formats — see the [verification story](https://github.com/MehdiZD97/3gpp-tr-library#how-its-verified).

`tr3gpp` is the distribution name, the import name and the console command — one stem for all three.

> **Renamed from `tr_api`.** This package was called `tr_api` (with a `tr-api` command) up to and including the `v0.1.0` tag. It was renamed before any PyPI release, because an unrelated project ([`cdamken/tr-api`](https://github.com/cdamken/tr-api), a Trade Republic client) declares exactly the same distribution name, top-level module and console script — installing both would have shadowed one another. If you have an older editable install, run `pip uninstall tr_api` before installing this one, and change `from tr_api import …` to `from tr3gpp import …`. Nothing else changed: the accessors, introspection layer and CLI subcommands are identical.

## Install

```sh
pip install tr3gpp
```

The package **bundles the processed TR data**, so it works with no clone of the repository anywhere — install it into your simulator's environment and query it.

Requires Python 3.9+; the only dependencies are `pydantic` and `pyyaml`.

### From a checkout instead

If you're editing the data (or contributing), install the package from a clone in editable mode:

```sh
pip install -e /path/to/3gpp-tr-library/tools/tr3gpp
```

`tr3gpp` resolves each data file against the repo checkout **first** and its own bundled copy second, so an editable install always reflects the clone's current state — your edits to `TR-*/` take effect immediately, and a previously generated bundle can never shadow them.

## Usage

```python
from tr3gpp import tr38901

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

# --- §7.6: Additional modelling components (7.6.0/1/3/4/8/9/10) ---
extra = tr38901.section("7.6")

extra.oxygen_absorption(f_ghz="60").alpha_db_per_km                       # Table 7.6.1-1

# Spatial consistency (7.6.3). Indoor/InF have no LOS/NLOS/O2I split, so
# `condition` is omitted for them:
extra.correlation_distance(scenario="UMa", condition="NLOS")              # Table 7.6.3.1-2
extra.correlation_distance(scenario="InF")
extra.correlation_type(parameter="Delays").correlation_type              # Table 7.6.3.4-1
extra.uncorrelated_states(parameter="Blockage")                          # Table 7.6.3.4-2

# Blockage (7.6.4), models A and B:
extra.self_blocking_region(mode="Portrait mode")                         # Table 7.6.4.1-1
extra.blocking_region(scenario="InH scenario")                           # Table 7.6.4.1-2
extra.blockage_correlation_distance(scenario="InH", condition="LOS")     # Table 7.6.4.1-4
extra.blocker_parameters(blocker="Human").dimensions                     # Table 7.6.4.2-5
extra.blockage_sign_description                                          # Table 7.6.4.1-3 (3x3 grid)

extra.ground_material(material_class="Concrete").a_epsilon               # Table 7.6.8-1
extra.absolute_time_of_arrival(scenario="UMa").mu_lg_delta_tau           # Table 7.6.9-1

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
from tr3gpp import tr36777

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

`section()` / `annex()` default to each TR's latest processed version (`v19.4.0` for TR 38.901, `v15.0.0` for TR 36.777) and accept an explicit `version=` keyword otherwise. (§7.9 covers the full ISAC clause 7.9.0-7.9.6; its 32 target/background fast-fading equations live as LaTeX in the section `.md` rather than the queryable surface, per the §7.5 precedent for procedural equations. §7.6 covers the dependency-driven core of its clause — 7.6.0/7.6.1/7.6.3/7.6.4/7.6.8/7.6.9/7.6.10, i.e. the sub-clauses the other processed sections actually reference; its 54 in-scope equations likewise live only in the `.md`, and 7.6.2 / 7.6.5–7.6.7 / 7.6.11–7.6.16 are not processed.) Each id resolves to its own YAML file, Pydantic model, and accessor class (see each module's `_SECTION_REGISTRY` / `_ANNEX_REGISTRY`) rather than assuming every section shares one shape. A lookup for a scenario/condition/variant that doesn't exist raises `ScenarioNotFoundError` with the list of what *is* available; an unprocessed section/annex or version raises `SectionNotFoundError`, listing what's actually processed -- neither returns `None` or a bare `KeyError`.

## Introspection — discover what's available without reading source

You don't have to know section or parameter names in advance; the API can tell you. `tr3gpp.introspect` describes the whole surface by **runtime inspection** of the accessors (so it never drifts from them), and each TR module exposes `list_*` / `describe`:

```python
from tr3gpp import tr38901, tr36777, introspect

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

## CLI — `tr3gpp`

Installing the package (`pip install -e tools/tr3gpp`) also installs a `tr3gpp` command, a **thin wrapper over the introspection layer** (no section knowledge of its own). Discover → describe → query, with no prior knowledge:

```console
$ tr3gpp list                       # every TR and its processed sections/annexes
$ tr3gpp describe tr38901 7.9        # a section's parameters, args, and available values
$ tr3gpp describe tr36777 B          # the annex, described the same way

# get: perform a lookup and print it readably
$ tr3gpp get tr38901 7.4 pathloss --scenario UMi-StreetCanyon --condition NLOS
$ tr3gpp get tr36777 B alternative_2 --scenario RMa-AV --parameter K --condition LOS

# dump: a whole parameter set as JSON/CSV for piping (machine output on stdout only)
$ tr3gpp dump tr38901 7.9 xpr --format json | jq '.[] | {target, mu_xpr_db}'
$ tr3gpp dump tr38901 7.5 channel_model_parameters --format csv > lsp.csv
```

`dump --format csv` matches the committed `tables/*.csv` where a single table exists (e.g. `channel_model_parameters` == `table-7.5-6.csv`). Unknown section/parameter/scenario prints the same "available: …" help the Python errors carry, to **stderr**, and exits non-zero — machine output stays clean for piping. The CLI uses only `argparse` (stdlib) — no added dependency.

## Organization

- `tr3gpp.models` — the Pydantic models. `PathlossEntry` is TR-agnostic (see `schemas/pathloss.yaml`); everything else is named for what it actually is: `LosProbabilityEntry` / `O2IPenetrationLoss` (+ sub-models) / `ShadowFadingAutocorrelation` (TR 38.901 §7.4), `ChannelModelParameterEntry` / `ZsdZodOffsetEntry` / `NotationEntry` / `ScalingFactorEntry` / `RayOffsetAngle` / `SubClusterInfo` (TR 38.901 §7.5), `SensingScenarioParameter` / `RcsModel1Entry` / `RcsModel2Entry` / `RcsModel2KParameter` / `XprEntry` / `ReferenceChannelModelEntry` / `TargetChannelLinkEntry` / `BackgroundChannelLinkEntry` / `LosConditionEntry` / `BackgroundChannelParamEntry` / `SpatialConsistencyCorrelationEntry` / `CalibrationAssumption` (TR 38.901 §7.9), and `PathlossDeltaEntry` / `LosProbabilityDeltaEntry` / `ShadowFadingDeltaEntry` / `FastFadingModelSelectionEntry` / `Alternative1DesiredParametersEntry` / `Alternative2ModifiedParameterEntry` (TR 36.777 Annex B).
- `tr3gpp._loader` — the TR-agnostic load/validate/cache machinery (`TRLoader`, `SectionNotFoundError`, `ScenarioNotFoundError`), shared by every per-TR module.
- `tr3gpp.tr38901` — TR 38.901's surface (`section()`, `Section74`, `Section75`, `Section79`, plus `list_sections()` / `describe()`).
- `tr3gpp.tr36777` — TR 36.777's surface (`annex()`, `AnnexB`, plus `list_annexes()` / `describe()`).
- `tr3gpp.introspect` — the self-describing surface (`UnitInfo`/`MemberInfo`, `all_units()`, `describe()`) derived by runtime inspection of the accessors, augmented by each accessor's small `_QUERYABLE` map (method → data field, so available values can be listed).
- `tr3gpp.cli` — the `tr3gpp` console command (`main(argv)`), a thin formatter over `tr3gpp.introspect`.

Adding a further TR is a new thin module (its registry + accessor classes + access verb) plus its models, not a copy of the loader. TR 38.901 §7.4/§7.5/§7.9 and TR 36.777 Annex B are available today.
