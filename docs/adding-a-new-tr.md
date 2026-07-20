# Adding a new TR (or a new section of an existing TR)

A concrete how-to, written from actually adding TR 36.777 Annex B as the
library's second TR. It captures the real steps and the gotchas that aren't
obvious until you hit them. For the section-file format itself, see
[`section-template.md`](section-template.md); this document is about the
surrounding plumbing.

## 0. Reconnaissance first, then confirm scope

Before extracting anything, map what's actually there — sub-clauses, the
real table inventory (with the TR's own table numbers), equation count,
rough page count — and settle the **format/verification strategy
empirically**, per table if needed. Two things that vary between documents
and materially change the work:

- **How equations are encoded.** Newer 3GPP exports (e.g. TR 38.901, 2026)
  carry equations as OMML *text* inside `<!--[if gte msEquation]>` HTML
  comments, so tag-stripping the HTML recovers every formula as text — a
  genuine second source you can cross-check automatically. Older documents
  (e.g. TR 36.777, 2017) render every equation as an **image** (`.png`/
  `.wmz`); the HTML has zero OMML and hundreds of image refs, and even the
  PDF's text layer doesn't carry the formula digits. Check this on-disk with
  a couple of the actual equation-bearing tables — don't assume from another
  TR. When equations are image-only, formula content is **PDF-visual
  single-source**, and that's fine — record it honestly (see step 6).
- **Which format gives clean structure.** `python-docx` can't read binary
  `.doc`; you may have a provided `.xml`, or need a `.doc`→`.docx`
  conversion (LibreOffice `--headless --convert-to docx`, run in `_scratch/`,
  never committed). Often the PDF text layer (pymupdf `get_text()`) plus the
  HTML tag-strip together cover structure and non-formula content without any
  docx at all.

If scope is genuinely uncertain (how big is the annex? is an accompanying
`.xlsx` in-scope or reference-only?), **surface it and get a decision** rather
than silently narrowing or expanding — the pattern every phase in this repo
has used.

## 1. Reference files and `.gitignore`

Source documents live under `references/<doc-folder>/<version>/` and are
gitignored except each folder's `README.md`. When you add a document folder,
confirm nothing large is accidentally trackable:

```sh
git status --porcelain references/          # should show nothing new/untracked
git check-ignore -v references/<doc>/<ver>/<some-source-file>
```

The `references/*` pattern with per-folder un-ignore of `README.md` already
covers new files and "Save as Web Page" sidecar directories (`*_files/`,
hundreds of images). Verify, don't assume — a gap here commits a lot of
unwanted binary.

Fill in `references/<doc-folder>/<version>/README.md` (release date, 3GPP
link, role in the repo) and link it from `references/README.md`.

## 2. Directory structure and naming

TR content lives at `TR-<number>/v<version>/<chapter>/<section>.{md,yaml}`
plus `<chapter>/tables/*.csv`. Conventions that set precedent:

- **Numbered clauses:** zero-padded chapter dir + real clause number, e.g.
  `07-channel-models/7.4-pathloss.md`.
- **Lettered annexes:** mirror that spirit with a lettered chapter dir and a
  real-identifier-preserving file, e.g.
  `annex-b-channel-modelling/B-channel-modelling.md`, with
  `section: "Annex B"` in the front matter (the template's own example
  sanctions a non-numeric section string).
- **Table CSVs use the TR's real table numbers** — `table-7.4.1-1.csv`,
  `table-B-1.csv`, `table-B.1.2-2.csv` — never a re-invented flat sequence.
- Add `TR-<number>/README.md` (model it on `TR-38.901/README.md`).

## 3. Cross-TR `depends_on`

`depends_on` entries are normally same-TR section-id stems
(`7.2-coordinate-system`). A section that depends on **another TR's** section
uses a TR-qualified form: `TR-38.901:7.4-pathloss`. Keep the bare form for
same-TR deps. If you introduce a cross-TR dep, the well-formedness test
(`tests/test_values_annexB.py`) already accepts both shapes — extend its
allow-list, don't overload the bare form in a way that breaks the same-TR
assumption.

## 4. Extraction → CSV + YAML + inline Markdown, from one source of truth

Write a build script in `_scratch/` (gitignored) that holds the extracted
values **once** and emits the CSVs, the section YAML, and the inline-Markdown
table fragments from that single dataset — so the three copies can't drift.
Paraphrase prose (don't copy TR prose verbatim); reproduce numeric values and
formulas faithfully. This is the same pattern `_scratch/build_data_*.py` uses
for every processed section.

## 5. Pydantic models (`tools/tr_api/models.py`)

Give each new data shape its own model. Keep the **`schemas/` restraint**:
only genuinely cross-TR-reusable shapes (like `PathlossEntry`) go in
`schemas/`; everything TR- or section-specific stays as a model in
`models.py`, named for what it actually is (aerial-UE delta tables are
`PathlossDeltaEntry` etc., not a pretend-generic name). Formula-bearing
fields are `str` (LaTeX or an "According to … of [4]" reference).

## 6. The `tr_api` package

The TR-agnostic load/validate/cache machinery lives in
`tools/tr_api/_loader.py` (`TRLoader`, `SectionNotFoundError`,
`ScenarioNotFoundError`). A per-TR module is thin:

1. A `_SECTION_REGISTRY` / `_ANNEX_REGISTRY` mapping each id to
   `(yaml_path_relative_to_version_dir, pydantic_model, accessor_class)`.
2. Accessor classes with lookup methods returning typed models (raise
   `ScenarioNotFoundError` listing what *is* available, never `None`/`KeyError`).
3. A `TRLoader("TR-<number>", "TR <number>", "v<version>", registry)` and a
   thin access verb — `section()` for numbered clauses, `annex()` for a
   lettered annex.

Then expose the module in `tools/tr_api/__init__.py` and add a usage block to
`tools/tr_api/README.md`. **Do not break existing import paths** (e.g.
`from tr_api import tr38901`) — CORDIS code may already use them; confirm with
`tests/test_tr_api.py` after any loader change.

## 7. `tools/verify_tables.py`

- Reuse `verify_table()` / `verify_flat_param_table()` — most parameter
  tables fit the list-of-entities shape. Only write a new checker if a table
  genuinely doesn't (none has needed one so far, including a 49×16 matrix and
  aerial delta tables).
- Register the new checker in `main()`'s dispatch, which keys on
  **`(tr, section)`** — a second TR could reuse a clause number, so section
  string alone isn't a safe key.
- Discovery (`section_utils.discover_section_md_files`) globs `TR-*/v*/**` and
  finds a new TR automatically — confirm by running
  `python tools/verify_tables.py` and seeing the new TR reported.
- **HTML formula cross-check applicability is per-TR.** Use
  `html_region_has_text_formulas()` to skip (not fail, not fake-pass) the
  cross-check for a TR whose equations are image-embedded.

## 8. Tests

- The generic discovery-based tests (`test_structure.py`,
  `test_versions.py`) pick up a new section/TR automatically — but confirm
  they actually *cover* it, not silently skip. For example
  `test_versions.py` checks `source_pdf` only for TRs in its
  `KNOWN_SOURCE_PDF_BY_TR` map — add the new TR there.
- Add value-regression tests (representative PDF-confirmed samples +
  completeness checks) following `test_values_annexB.py`.
- If the new content is a delta to an already-processed section, add an
  **internal cross-check** that its baseline references actually exist in the
  committed data — a consistency check the repo is uniquely positioned to do.
- Full suite (`pytest tests/ -v`) and `python tools/verify_tables.py` must
  both pass (warnings are errors via `pytest.ini`).

## 9. Finish

Update `INDEX.md` (a new row; confirm the format handles a lettered annex /
second TR cleanly), update `CLAUDE.md`'s phase status and directory layout,
and — per the repo rules — **do not commit**; report what you'd commit and
wait for the go-ahead.
