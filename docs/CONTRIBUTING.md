# Contributing

Thanks for your interest in improving `3gpp-tr-library`. This document covers how to propose changes as an external contributor.

## Proposing a new section or a fix

This project follows the standard GitHub fork-and-pull-request flow:

1. Fork the repository.
2. Create a branch for your change.
3. Make your edits.
4. Open a pull request against `main` describing what you changed and why.

Keep pull requests scoped to one section (or one fix) at a time — it makes review much easier.

## Development setup

```sh
python3 -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r requirements-dev.txt
pip install -e tools/tr3gpp
```

The first `pip install` covers everything needed to work on the repo itself — source extraction (`python-docx`, `pymupdf`, `beautifulsoup4`, `lxml`), and the test/verification tooling (`pytest`, `pyyaml`, `pydantic`). The second, editable install of `tools/tr3gpp` is needed to run its own tests (`tests/test_models.py`, `tests/test_tr3gpp.py`) and to use the package the way downstream simulation code would — see [`tools/tr3gpp/README.md`](../tools/tr3gpp/README.md) if you're consuming the library rather than contributing to it.

An editable install reads the TR data straight from the repo's `TR-*/` directories, so nothing extra is needed for day-to-day work.

## Building a distributable wheel

A wheel has no repo around it, so it ships its own copy of the processed data. That copy is **generated, not tracked** — regenerate it before every build:

```sh
python tools/sync_package_data.py     # populates tools/tr3gpp/data/ from TR-*/
python -m build tools/tr3gpp
```

`tools/tr3gpp/data/` is gitignored: the repo-root `TR-*/` directories remain the single source of truth in version control. `python tools/sync_package_data.py --check` verifies an existing bundle against those originals and exits non-zero if any file is stale, missing, or extra — worth running if you're unsure whether a bundle in your working tree is current. At runtime the package always prefers the repo checkout over its bundled copy, so a stale bundle can't shadow your edits while you work.

## Verification standard

Every table or parameter value that's marked `status: verified` in a section's front matter must have been cross-checked against the source 3GPP document before that status is set. A pull request introducing or changing a `verified` section should note, in the PR description, what source format(s) the values were checked against. Content that hasn't been cross-checked should stay at `planned` or `in-progress`.

## File structure

New section files should follow [`docs/section-template.md`](section-template.md) — it defines the required front matter fields and the expected body layout (prose, table, equations, figure references).

## Verification tooling

Run `python tools/verify_tables.py` before opening a pull request that touches a section's CSV/YAML/Markdown — it discovers every processed section, validates the YAML against the shared Pydantic models, and cross-checks every table's CSV against its YAML, printing a pass/fail summary and exiting non-zero on any mismatch. Formula content (as opposed to structure) can only be automatically cross-checked where the source document's equations are extractable as text — this doesn't cover every table; see the tool's own comments for specifics on TR 38.901 §7.4.

## License and attribution

By contributing, you agree that your contributions are licensed under this repository's [MIT License](../LICENSE).
