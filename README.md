# 3gpp-tr-library

Hand-curated, section-level 3GPP Technical Reports with queryable parameter tables.

## Purpose

This repository turns select 3GPP Technical Reports into hand-verified, section-level Markdown and structured data — Markdown for human readability, CSV/YAML for programmatic access. It's built for LLM ingestion, retrieval-augmented generation (RAG), and direct use in wireless simulation code, where a queryable table of channel-model parameters is more useful than a scanned PDF.

## Status

This is an active, evolving project — not all sections are populated yet, and coverage grows opportunistically as research needs demand rather than front-to-back through each document. See [INDEX.md](INDEX.md) for current section-by-section coverage and status.

## Directory structure

```
3gpp-tr-library/
├── TR-<number>/
│   └── v<version>/        # each version is fully self-contained
├── schemas/                # shared YAML schemas for parameter tables
├── tools/                  # verification scripts and a Python API for simulation use
└── docs/                   # templates and contributor guidelines
```

## Quickstart

Start at [INDEX.md](INDEX.md) to find the TR, version, and section you need. Each section file carries YAML front matter with a `status` field:

- `planned` — identified as in-scope, not yet written.
- `in-progress` — being drafted or cross-checked against source.
- `verified` — cross-checked against multiple source formats and ready to use.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

Developed by [Mehdi Zafari](https://mehdizd97.github.io/) during PhD research at [LS-Wireless](https://github.com/LS-Wireless), with the support of his advisor, Professor [A. Lee Swindlehurst](https://engineering.uci.edu/users/lee-swindlehurst).

## References

*Citations for 3GPP TRs and related datasets/tools will be added here.*
