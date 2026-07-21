# 3gpp-tr-library

[![CI](https://github.com/MehdiZD97/3gpp-tr-library/actions/workflows/ci.yml/badge.svg)](https://github.com/MehdiZD97/3gpp-tr-library/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Hand-verified, section-level 3GPP Technical Reports as queryable Markdown + CSV/YAML — and a typed Python API to pull channel-model parameters straight into simulation code.**

The tables, formulas, and parameters buried in 3GPP TRs are exactly the content that PDF extractors and LLMs mangle — merged cells, image-rendered equations, per-scenario conditions that flatten into nonsense. This repository takes select TRs and turns the sections that matter into **hand-verified, cross-checked** structured data: Markdown for reading, CSV + YAML for machines, and a small pip-installable API so you can call for a pathloss formula or a large-scale-parameter set instead of transcribing one out of a 160-page document.

It's built for LLM ingestion / RAG pipelines and for direct use in wireless simulation code.

## What's in it right now

Coverage grows opportunistically as research needs demand — not front-to-back through each document — and that selectivity is deliberate: depth and verification over breadth. Currently processed and `verified`:

| TR | Version | Section | What it covers |
|---|---|---|---|
| **TR 38.901** | v19.4.0 | §7.4 | Pathloss, LOS probability, and O2I (building/car) penetration modelling |
| **TR 38.901** | v19.4.0 | §7.5 | Fast fading model — the full 12-step channel-coefficient generation procedure + all 12 supporting tables (incl. the 49×16 channel-model-parameter table) |
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

Lookups return typed models (never a bare dict or `None`); an unknown scenario/section raises an error that lists what *is* available. Full API, install instructions, and organization are in **[tools/tr_api/README.md](tools/tr_api/README.md)**.

## Repository layout

Each processed section ships in **three coordinated formats** — that triple-format design is the point, not incidental:

- a **`.md`** with paraphrased prose, inline tables, and equations as LaTeX (human-readable);
- one **`.csv` per real TR table** using the TR's own table numbers (programmatic access);
- a **`.yaml`** of queryable parameters, validated against Pydantic models.

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

<!-- To be completed by the maintainer: related tools, datasets, and prior work,
     with framing (complementary vs. comparative) chosen deliberately. This is
     intentionally left for the author to populate rather than auto-generated. -->

*Related tools and datasets will be listed here.*

### How to cite this repository

<!-- Placeholder: a citable reference (e.g. a future write-up or a CITATION.cff)
     can be added here once one exists. -->

*A citation entry will be added here if/when a formal write-up exists.*
