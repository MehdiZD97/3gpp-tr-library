# Publishing `tr3gpp`

Maintainer runbook for cutting a release of the Python package. Everything here is run **by hand by the maintainer** — nothing in this repo uploads anything automatically, and no CI job has publish credentials.

The package is distributed as **`tr3gpp`** — the same string is the PyPI distribution name, the Python import name and the console command.

> **Read this first if you change nothing else:** the wheel ships its own copy of the processed TR data, and that copy is **generated, not tracked**. If you build without running `python tools/sync_package_data.py`, you publish a package with stale or missing data. Step 3 below is not optional.

---

## Release order (and why it matters)

Do these in order. Two later steps depend on `main` already containing the release:

1. **Merge `developer` → `main`.** The git tag, the GitHub release and the Zenodo archive all attach to `main`, and the package's `Documentation` project URL points at `https://github.com/MehdiZD97/3gpp-tr-library/blob/main/tools/tr3gpp/README.md` — that URL 404s until the merge lands, and PyPI metadata is **immutable once uploaded**.
2. **Tag and release on GitHub**, which triggers the Zenodo archive.
3. **Then** build and upload to PyPI.

Publishing to PyPI before merging would ship a project URL that doesn't resolve, and you cannot edit it afterwards — you'd have to burn a version number.

---

## Version-bump checklist

One number, everywhere. Before building, confirm all four agree:

| Where | What to set |
|---|---|
| `tools/tr3gpp/pyproject.toml` | `version = "X.Y.Z"` |
| `CITATION.cff` | `version: X.Y.Z`, and add `date-released: YYYY-MM-DD` on the day you release |
| git tag on `main` | `vX.Y.Z` |
| GitHub release | title/tag `vX.Y.Z` |
| Zenodo | the archive created from that release records `vX.Y.Z` |

Versioning follows SemVer, read for a 0.x project: a **breaking change bumps the minor**, additive content bumps the patch or minor. Examples from the history: `v0.1.0` was the first public archive; `v0.2.0` added TR 38.901 §7.6, renamed the package `tr_api` → `tr3gpp` (breaking), and made a standalone `pip install` work.

`1.0.0` is deliberately **not** claimed yet — it should mean "the API surface is committed", and it's worth waiting until the content set settles (e.g. §7.6 completed, or a third TR landed) rather than defaulting into it.

### About the DOI

`10.5281/zenodo.21501655` is the Zenodo **concept DOI** — it always resolves to the latest archived version, so the README badge, the citation and the package's `Archive (DOI)` project URL never go stale and need no edit per release. Each release also gets its own version DOI (v0.1.0's is `10.5281/zenodo.21501656`); use a version DOI only when citing a specific archived snapshot.

---

## Publishing steps

### 0. Prerequisites

```sh
source .venv/bin/activate
pip install -r requirements-dev.txt     # includes `build`
pip install twine
```

Authentication uses a **PyPI API token**, configured either in `~/.pypirc` or via `twine`'s standard environment variables. Create the token in your PyPI account settings and scope it to this project once it exists. Never put a token in a file inside the repo.

### 1. Confirm the gate is green

```sh
python -m pytest tests/ -q
python tools/verify_tables.py
```

Both must pass — the tests are the only thing standing between a data error and a published artifact.

### 2. Set the version

Edit `version` in `tools/tr3gpp/pyproject.toml`, commit it on `developer`, then merge `developer` → `main` (see "Release order" above).

### 3. Sync the bundled data — **do not skip**

```sh
python tools/sync_package_data.py
python tools/sync_package_data.py --check     # must report "clean"
```

This copies the repo-root `TR-*/` data and the repo `LICENSE` into `tools/tr3gpp/` (both gitignored). `--check` exits non-zero if any bundled file is stale, missing or extra.

### 4. Build

```sh
rm -rf tools/tr3gpp/dist tools/tr3gpp/build tools/tr3gpp/*.egg-info
python -m build tools/tr3gpp
```

Produces `tools/tr3gpp/dist/tr3gpp-X.Y.Z-py3-none-any.whl` and `.tar.gz`.

A benign warning — `Package 'tr3gpp.data' is absent from the 'packages' configuration` — is expected: `data/` is package *data*, not a subpackage, and is included via `[tool.setuptools.package-data]`. Step 5 confirms it actually made it in.

### 5. Check the artifacts

```sh
twine check tools/tr3gpp/dist/*
```

Must print `PASSED` for both. This catches long-description rendering problems before PyPI does.

Then audit the wheel by hand:

```sh
unzip -l tools/tr3gpp/dist/tr3gpp-*.whl
```

Confirm all of these:

- The `tr3gpp/data/...` tree is present (currently **78** files: 5 `.yaml`, 5 `.md`, 68 `.csv`). If it's missing, you skipped step 3.
- `tr3gpp/py.typed` is present (so type checkers use the annotations).
- `tr3gpp-X.Y.Z.dist-info/licenses/LICENSE` is present.
- **Nothing from `references/`, `_scratch/`, `.venv/`, `docs/phase-plans/` or `CLAUDE.md`, and no `.pdf` / `.docx` / `.xml` source document.** A copyrighted 3GPP source document inside a published wheel would be a serious problem — check this explicitly, every time:

```sh
unzip -l tools/tr3gpp/dist/tr3gpp-*.whl | grep -iE 'references|_scratch|\.venv|\.pdf|\.docx|\.xlsx|CLAUDE|phase-plans' && echo "STOP — do not upload" || echo "clean"
```

- The wheel is well under 1 MB (it is ~150 KB).

### 6. Verify a clean install *before* uploading

The one test that actually proves the package works for someone who isn't you: install the built artifact into a fresh environment with no clone of this repo anywhere near it.

```sh
cd "$(mktemp -d)"
cp /path/to/3gpp-tr-library/tools/tr3gpp/dist/tr3gpp-*.whl .
python3 -m venv venv
./venv/bin/pip install ./tr3gpp-*.whl
rm tr3gpp-*.whl                     # nothing repo-shaped left in this directory
./venv/bin/python -c "from tr3gpp import tr38901; print(tr38901.section('7.6').ground_material(material_class='Metal').c_sigma)"
./venv/bin/tr3gpp list
```

Expected: `10^7`, and a `list` naming §7.4, §7.5, §7.6, §7.9 and TR 36.777 Annex B **with their titles** (titles come from the bundled `.md` front matter, so a wrong bundle shows up here as blank titles).

### 7. Optional rehearsal on TestPyPI

Worth doing for a first upload or after any metadata change:

```sh
twine upload --repository testpypi tools/tr3gpp/dist/*
```

Then install from TestPyPI in a fresh venv — dependencies must come from real PyPI:

```sh
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ tr3gpp
```

Check the rendered project page on test.pypi.org: description, README rendering, the classifiers and every project link. **TestPyPI version numbers are also consumed permanently** — if you rehearse `X.Y.Z` there you cannot re-upload the same number, so rehearse the exact version you intend to ship and fix problems by bumping.

### 8. Upload to PyPI

```sh
twine upload tools/tr3gpp/dist/*
```

**This is irreversible.** A version number can be yanked but never reused, and the metadata cannot be edited afterwards.

### 9. Post-publish verification

```sh
cd "$(mktemp -d)"
python3 -m venv venv
./venv/bin/pip install tr3gpp
./venv/bin/python -c "import importlib.metadata as m; print(m.version('tr3gpp'))"
./venv/bin/tr3gpp describe tr38901 7.6
```

Then on `https://pypi.org/project/tr3gpp/`, confirm the long description renders, and click every link under "Project links" — Homepage, Documentation, Repository, Issues, Changelog and the DOI. All should resolve; the Documentation link is the one that depends on the `developer` → `main` merge having happened first.

---

## After the release

- Update the "What's in it right now" table in the root `README.md` if the content set changed.
- Check the repo's About description and topics on GitHub still match.
- Confirm the Zenodo archive for the new tag appears, and that the concept DOI now resolves to it.

## If something goes wrong

- **Wrong metadata published.** It cannot be edited. Fix the source, bump the patch version, and publish again. Yank the bad version on PyPI so it isn't installed by default.
- **Data missing from the wheel.** You skipped `python tools/sync_package_data.py`. Bump the patch version, sync, rebuild, re-verify with step 6, publish.
- **`twine check` fails on the long description.** The long description is `tools/tr3gpp/README.md`. Every link in it must be an **absolute URL** — relative paths don't resolve on PyPI.
