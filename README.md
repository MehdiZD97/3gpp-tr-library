<div align="center">

# 3gpp-tr-library

[![CI](https://github.com/MehdiZD97/3gpp-tr-library/actions/workflows/ci.yml/badge.svg)](https://github.com/MehdiZD97/3gpp-tr-library/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![3GPP](https://img.shields.io/badge/Standard-3GPP-orange?style=flat&logo=bookstack&logoColor=white)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg?logo=python&logoColor=white)
![Last Commit](https://img.shields.io/github/last-commit/MehdiZD97/3gpp-tr-library)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)

</div>

**Hand-verified, section-level 3GPP Technical Reports as queryable Markdown + CSV/YAML — and a typed Python API to pull channel-model parameters straight into simulation code.**

The tables, formulas, and parameters buried in 3GPP TRs are exactly the content that PDF extractors and LLMs mangle — merged cells, image-rendered equations, per-scenario conditions that flatten into nonsense. This repository takes select TRs and turns the sections that matter into **hand-verified, cross-checked** structured data: Markdown for reading, CSV + YAML for machines, and a small pip-installable API so you can call for a pathloss formula or a large-scale-parameter set instead of transcribing one out of a 160-page document.

It's built for LLM ingestion / RAG pipelines and for direct use in wireless simulation code.

## What's in it right now

Coverage grows opportunistically as research needs demand — not front-to-back through each document — and that selectivity is deliberate: depth and verification over breadth. Currently processed and `verified`:

| TR | Version | Section | What it covers |
|---|---|---|---|
| **TR 38.901** | v19.4.0 | §7.4 | Pathloss, LOS probability, and O2I (building/car) penetration modelling |
| **TR 38.901** | v19.4.0 | §7.5 | Fast fading model — the full 12-step channel-coefficient generation procedure + all 12 supporting tables (incl. the 49×16 channel-model-parameter table) |
| **TR 38.901** | v19.4.0 | §7.9 | Channel model(s) for ISAC (Integrated Sensing and Communication) — the full Rel-19 clause: sensing scenarios, the physical-object/RCS target model, reference-channel mapping, the target/background fast-fading procedure, additional components, and calibration (32 tables, ~37 equations) |
| **TR 36.777** | v15.0.0 | Annex B | Aerial-UE (drone) channel model for RMa-AV/UMa-AV/UMi-AV — height-dependent deltas to TR 38.901's terrestrial models |

See **[INDEX.md](INDEX.md)** for the live, section-by-section status table.

## The `tr_api` Python package

The headline feature: a typed, pip-installable API that reads the structured data directly, so version-pinned 3GPP parameters go into your simulation code without a hand-transcription step.

```python
from tr_api import tr38901, tr36777

# TR 38.901 §7.4 — pathloss for a UMi Street-Canyon NLOS link:
entry = tr38901.section("7.4").pathloss(scenario="UMi-StreetCanyon", condition="NLOS")
entry.formula                # LaTeX string
entry.shadow_fading_std_db   # a typed Pydantic model, not a raw dict

# TR 38.901 §7.5 — large-scale parameters for UMa NLOS:
lsp = tr38901.section("7.5").channel_model_parameters(scenario="UMa", condition="NLOS")
lsp.mu_lgDS                  # carrier-frequency-dependent delay-spread mean

# TR 36.777 Annex B — aerial-UE pathloss (returns the height bands):
tr36777.annex("B").pathloss(scenario="RMa-AV", condition="LOS")
```

Lookups return typed models (never a bare dict or `None`); an unknown scenario/section raises an error that lists what *is* available.

**Don't know the section or parameter names?** The API is self-describing, and installing it also installs a `tr-api` command that discovers everything for you — no prior knowledge, no reading source:

```console
$ tr-api list                       # every TR and its processed sections/annexes
$ tr-api describe tr38901 7.9        # a section's parameters, their args, and available values
$ tr-api get tr38901 7.4 pathloss --scenario UMi-StreetCanyon --condition NLOS
$ tr-api dump tr38901 7.5 channel_model_parameters --format csv > lsp.csv   # or --format json | jq
```

Full API, the introspection layer, the CLI, install instructions, and organization are in **[tools/tr_api/README.md](tools/tr_api/README.md)**.

## Why three formats

Each processed section ships in **three coordinated, mutually-verified formats**. That's the point, not incidental packaging — each exists because a different consumer needs the *same* verified numbers in a different shape, and the origin problem (PDF extractors and LLMs mangling merged cells and image-rendered equations) is exactly what makes a single format insufficient:

- **`.md` — for humans and for RAG.** A section is a self-contained unit: front-matter scaffolding (TR, version, clause, `depends_on`, `verified_against`), paraphrased prose, inline tables, and equations as LaTeX. That's what you read to understand the model — and, because it's one coherent chunk with metadata, what an LLM can ingest *whole* for retrieval-augmented generation without the table-mangling that wrecks raw-PDF ingestion.
- **`.csv` — for spreadsheets, pandas, and diffing.** One file per *real* TR table, named with the TR's own table number (`table-7.9.2.1-2.csv`, not a made-up scheme), so it maps straight back to the source document. Load it in pandas, open it in a spreadsheet, or `git diff` it across TR versions — tabular workflows want a table, not prose.
- **`.yaml` + the typed API — for simulation code.** Queryable parameters validated against Pydantic models, so version-pinned 3GPP values flow into your simulator through `tr_api` (or the `tr-api` CLI) with no hand-transcription step — the transcription step being precisely where errors creep into research code.

**The same parameter, three ways.** Take the UAV cross-polarization ratio (§7.9, Table 7.9.2.2-1): the `.md` shows a row `| UAV | 13.75 | 7.07 |` under the XPR equations; `tables/table-7.9.2.2-1.csv` has `UAV,13.75,7.07`; the `.yaml` has `- {target: UAV, mu_xpr_db: "13.75", sigma_xpr_db: "7.07"}`, reachable as `tr38901.section("7.9").xpr(target="UAV").mu_xpr_db`. All three are checked against each other on every push (see [How it's verified](#how-its-verified)), so they can't silently drift apart.

## Repository layout

```
3gpp-tr-library/
├── TR-38.901/  TR-36.777/     # TR-first, then version-first; each version self-contained
│   └── v<version>/<chapter>/  #   section .md + .yaml, and tables/*.csv
├── schemas/                    # shared, TR-agnostic YAML schemas (e.g. the pathloss table shape)
├── tools/
│   ├── tr_api/                 # the pip-installable typed Python API
│   └── verify_tables.py        # the CSV↔YAML consistency + formula cross-check gate
├── tests/                      # pytest suite (structure, versions, values, cross-format)
└── docs/                       # section template, contributing guide, "adding a new TR" how-to
```

## How it's verified

The value here is that nothing is batch-converted and hoped-for. Every `verified` value is **cross-checked against multiple independent source formats** before its status is set — for TR 38.901 that means the `.docx` structure, a rendered-PDF visual read, and the HTML export's equation text, reconciled against each other. `python tools/verify_tables.py` and a GitHub Actions CI run enforce CSV↔YAML↔Markdown agreement and schema validity on every push.

Where that automated cross-check *can't* apply, the README says so rather than papering over it: older TRs (e.g. TR 36.777, a 2017 document) render every equation as an image, so their formula content is **PDF-visual-verified** — a careful manual read, honestly recorded as single-source, not dressed up as something it isn't. The honesty is part of the trust story.

## Quickstart

1. **Browse:** start at **[INDEX.md](INDEX.md)** to find the TR / version / section you need. Each section file carries YAML front matter with a `status`:
   - `planned` — identified as in-scope, not yet written.
   - `in-progress` — being drafted or cross-checked against source.
   - `verified` — cross-checked against multiple source formats and ready to use.
2. **Use from code:** `pip install -e /path/to/3gpp-tr-library/tools/tr_api`, then `from tr_api import tr38901` (see [tools/tr_api/README.md](tools/tr_api/README.md)).

## Contributing

Contributions (new sections, fixes, verification improvements) are welcome — see **[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)** for the workflow, the verification standard, and the development setup. New TRs have their own walkthrough in [docs/adding-a-new-tr.md](docs/adding-a-new-tr.md).

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

Developed by [Mehdi Zafari](https://mehdizd97.github.io/) during PhD research at [LS-Wireless](https://github.com/LS-Wireless), with the support of his advisor, Professor [A. Lee Swindlehurst](https://engineering.uci.edu/users/lee-swindlehurst).

## References

### 3GPP source documents

The authoritative sources for the content in this library. Always defer to these for the canonical text.

- **3GPP TR 38.901** v19.4.0 — *Study on channel model for frequencies from 0.5 to 100 GHz* (Release 19). <https://www.3gpp.org/dynareport/38901.htm>
- **3GPP TR 36.777** v15.0.0 — *Study on Enhanced LTE Support for Aerial Vehicles* (Release 15). <https://www.3gpp.org/dynareport/36777.htm>

This repository redistributes hand-verified structured *extracts*, not the original documents. The 3GPP TRs themselves are © 3GPP and are not included here.

### Related work

- **TSpec-LLM** — *An Open-source Comprehensive Dataset of 3GPP Specifications for LLM Understanding* ([dataset](https://huggingface.co/datasets/rasoul-nikbakht/TSpec-LLM)). A broad corpus of 3GPP specification text prepared for large-language-model consumption — retrieval, training, and evaluation across many documents.
- **3GPP MCP server** ([github.com/edhijlu/3gpp-mcp-server](https://github.com/edhijlu/3gpp-mcp-server)) — a Model Context Protocol server that exposes 3GPP material to LLM clients.

This repository is **complementary** to those efforts rather than a substitute for them. Where a broad-corpus dataset or an MCP bridge optimizes for *coverage* — as much 3GPP text as possible, in an LLM-friendly form — this project optimizes for *depth and correctness on a focused set of high-value TRs*: hand-verified, section-level extracts with queryable **typed** parameters (`tr_api`), the TR's own real table numbers, and cross-format verification against multiple independent source formats before anything is marked `verified`. In short: those provide breadth for language-model workflows; this provides depth and machine-usable, version-pinned parameters for simulation and analysis. The two serve different needs and pair naturally.

### How to cite this repository

<!-- Placeholder: a citable reference (e.g. a future write-up or a CITATION.cff)
     can be added here once one exists. -->

*A citation entry will be added here if/when a formal write-up exists.*
