# Contributing

Thanks for your interest in improving `3gpp-tr-library`. This document covers how to propose changes as an external contributor.

## Proposing a new section or a fix

This project follows the standard GitHub fork-and-pull-request flow:

1. Fork the repository.
2. Create a branch for your change.
3. Make your edits.
4. Open a pull request against `main` describing what you changed and why.

Keep pull requests scoped to one section (or one fix) at a time — it makes review much easier.

## Verification standard

Every table or parameter value that's marked `status: verified` in a section's front matter must have been cross-checked against the source 3GPP document before that status is set. A pull request introducing or changing a `verified` section should note, in the PR description, what source format(s) the values were checked against. Content that hasn't been cross-checked should stay at `planned` or `in-progress`.

## File structure

New section files should follow [`docs/section-template.md`](section-template.md) — it defines the required front matter fields and the expected body layout (prose, table, equations, figure references).

## Verification tooling

A `tools/verify_tables.py` script for automated CSV ↔ YAML consistency checks is coming soon. Until it lands, verification is manual.

## License and attribution

By contributing, you agree that your contributions are licensed under this repository's [MIT License](../LICENSE).
