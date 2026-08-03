"""
Populate the `tr3gpp` package's bundled data directory from the repo-root TR
directories, so a built wheel is self-contained.

Why this exists (Phase 10 Group C)
----------------------------------
The processed data lives at the repo root (`TR-38.901/`, `TR-36.777/`) because
that is how people browse it on GitHub. A wheel installed into site-packages
has no repo around it, so it needs its own copy. This script produces that
copy; `tr3gpp._loader` then resolves each file against the repo checkout first
and the bundle second (see that module's docstring for why that order).

**Run this before `python -m build`.** Never hand-copy: the whole point is that
there is exactly one source of truth in version control (the repo-root files)
and the bundle is a regenerable build artifact, gitignored.

    python tools/sync_package_data.py            # populate tools/tr3gpp/data/
    python tools/sync_package_data.py --check    # verify an existing bundle, write nothing

What gets bundled, and why
--------------------------
Driven by `section_utils.discover_section_md_files()` -- the same discovery the
tests and `verify_tables.py` use -- so the bundle tracks exactly the processed
set and cannot drift from it via a hand-maintained list.

- `*.yaml`  -- required at runtime: the queryable data itself.
- `*.md`    -- required at runtime: `TRLoader.front_matter()` reads the sibling
               `.md` for each section's title (deliberately not duplicated into
               the registry), so without these an installed package would
               describe every section with an empty title.
- `tables/*.csv` -- **not** read by the package at runtime (confirmed: the only
               file reads in `tr3gpp/` are the `.yaml` load and the `.md` front
               matter; `dump --format csv` regenerates CSV from the models via
               `introspect.to_table`). They are bundled anyway because the
               repo's premise is three coordinated formats, and a wheel that
               silently shipped only two of them would be a worse artifact for
               a few tens of kilobytes.

TR-level and repo-level READMEs are deliberately *not* bundled: they are
documentation about the repo, not processed section data.

The repo-root `LICENSE` is also copied next to the package (not into `data/`),
so `license-files = ["LICENSE"]` in pyproject.toml ships the licence text
inside the built artifact. It is gitignored for the same reason the data bundle
is: exactly one copy in version control.
"""
import argparse
import filecmp
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from section_utils import REPO_ROOT, discover_section_md_files  # noqa: E402

PACKAGE_DIR = os.path.join(REPO_ROOT, "tools", "tr3gpp")
DEFAULT_BUNDLE_DIR = os.path.join(PACKAGE_DIR, "data")

# Sits beside the package (not inside data/) so pyproject's
# license-files = ["LICENSE"] finds it; gitignored, like the bundle.
LICENSE_SOURCE = os.path.join(REPO_ROOT, "LICENSE")
LICENSE_DEST = os.path.join(PACKAGE_DIR, "LICENSE")


def sync_license():
    """Copy the repo-root LICENSE next to the package. Returns the destination."""
    shutil.copy2(LICENSE_SOURCE, LICENSE_DEST)
    return LICENSE_DEST


def bundle_manifest():
    """[(absolute source path, repo-relative destination path)] for the bundle.

    Deterministic and sorted, so two runs produce byte-identical layouts and a
    diff of the manifest is a meaningful review artifact.
    """
    sources = set()
    chapter_dirs = set()
    for md_path in discover_section_md_files():
        sources.add(md_path)
        yaml_path = md_path[:-3] + ".yaml"
        if os.path.isfile(yaml_path):
            sources.add(yaml_path)
        chapter_dirs.add(os.path.dirname(md_path))

    for chapter in chapter_dirs:
        tables = os.path.join(chapter, "tables")
        if os.path.isdir(tables):
            for name in os.listdir(tables):
                if name.endswith(".csv"):
                    sources.add(os.path.join(tables, name))

    return sorted((src, os.path.relpath(src, REPO_ROOT)) for src in sources)


def build_bundle(dest_dir, clean=True):
    """Write the bundle into `dest_dir`. Returns the list of relative paths written."""
    if clean and os.path.isdir(dest_dir):
        # Wipe first, so a file removed from the repo cannot linger in the bundle.
        shutil.rmtree(dest_dir)
    written = []
    for src, rel in bundle_manifest():
        dst = os.path.join(dest_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        written.append(rel)
    return written


def check_bundle(dest_dir):
    """[problems] comparing an existing bundle against the repo-root originals."""
    problems = []
    if not os.path.isdir(dest_dir):
        return [f"no bundle at {dest_dir} (run: python tools/sync_package_data.py)"]

    expected = {rel: src for src, rel in bundle_manifest()}
    for rel, src in expected.items():
        dst = os.path.join(dest_dir, rel)
        if not os.path.isfile(dst):
            problems.append(f"missing from bundle: {rel}")
        elif not filecmp.cmp(src, dst, shallow=False):
            problems.append(f"STALE (differs from the repo original): {rel}")

    for root, _dirs, names in os.walk(dest_dir):
        for name in names:
            rel = os.path.relpath(os.path.join(root, name), dest_dir)
            if rel not in expected:
                problems.append(f"extra file in bundle (no repo original): {rel}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Sync the repo-root TR data into the tr3gpp package's bundled data directory."
    )
    parser.add_argument("--check", action="store_true",
                        help="verify the existing bundle against the repo originals; write nothing")
    parser.add_argument("--dest", default=DEFAULT_BUNDLE_DIR, help="bundle directory (default: tools/tr3gpp/data)")
    args = parser.parse_args(argv)

    if args.check:
        problems = check_bundle(args.dest)
        if args.dest == DEFAULT_BUNDLE_DIR and not (
            os.path.isfile(LICENSE_DEST) and filecmp.cmp(LICENSE_SOURCE, LICENSE_DEST, shallow=False)
        ):
            problems.append("LICENSE beside the package is missing or differs from the repo LICENSE")
        if problems:
            print(f"Bundle check FAILED ({len(problems)} problem(s)) against {args.dest}:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print(f"Bundle check clean: {args.dest} matches the repo-root originals.")
        return 0

    written = build_bundle(args.dest)
    total = sum(os.path.getsize(os.path.join(args.dest, r)) for r in written)
    by_ext = {}
    for rel in written:
        by_ext[os.path.splitext(rel)[1]] = by_ext.get(os.path.splitext(rel)[1], 0) + 1
    print(f"Bundled {len(written)} file(s) ({total / 1024:.0f} KB) into {args.dest}")
    for ext, n in sorted(by_ext.items()):
        print(f"  {ext or '(no ext)'}: {n}")
    if args.dest == DEFAULT_BUNDLE_DIR:
        print(f"Copied LICENSE to {sync_license()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
