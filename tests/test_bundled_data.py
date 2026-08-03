"""
The bundled-data path (Phase 10 Group C): what makes `pip install tr3gpp` work
without a repo checkout anywhere nearby.

Three things are guarded here, and the third is the important one:

1. **The sync produces a faithful bundle.** Every processed section's `.yaml`,
   its sibling `.md`, and every `tables/*.csv` is copied byte-for-byte, and
   nothing else is.
2. **The loader can resolve entirely from a bundle** -- the installed-wheel
   code path, exercised here without needing an install.
3. **A stale bundle can never shadow the repo.** `_loader.default_data_roots()`
   puts the repo checkout ahead of the bundled copy, so a developer editing a
   YAML in a clone sees the edit immediately even if an old bundle is sitting
   in the working tree. For a project whose premise is verified accuracy,
   silently serving stale numbers would be the worst possible bug, so it is
   pinned by a test that deliberately corrupts a bundle and asserts the repo
   value still wins.

Note these tests never mutate the working tree's bundle: the sync is exercised
into `tmp_path`, so they run identically whether or not `tools/tr3gpp/data/`
has been generated locally.
"""
import filecmp
import os
import shutil

import pytest
import sync_package_data
import yaml
from section_utils import discover_section_md_files
from tr3gpp import _loader, tr38901
from tr3gpp._loader import SectionNotFoundError, TRLoader
from tr3gpp.models import Section76Data

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING_TREE_BUNDLE = sync_package_data.DEFAULT_BUNDLE_DIR


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    """A freshly synced bundle in a temp dir (never the working tree's)."""
    dest = tmp_path_factory.mktemp("bundle") / "data"
    sync_package_data.build_bundle(str(dest))
    return str(dest)


# ---------------------------------------------------------------------------
# 1. The sync produces a faithful bundle
# ---------------------------------------------------------------------------
def test_manifest_is_deterministic_and_repo_relative():
    manifest = sync_package_data.bundle_manifest()
    assert manifest == sync_package_data.bundle_manifest(), "manifest is not deterministic"
    for src, rel in manifest:
        assert os.path.isabs(src) and os.path.isfile(src)
        assert not os.path.isabs(rel)
        assert rel.startswith("TR-"), f"bundle path escapes the TR dirs: {rel}"


def test_manifest_covers_exactly_the_processed_set():
    rels = {rel for _src, rel in sync_package_data.bundle_manifest()}
    for md_path in discover_section_md_files():
        md_rel = os.path.relpath(md_path, REPO_ROOT)
        assert md_rel in rels, f"section .md missing from the bundle manifest: {md_rel}"
        assert md_rel[:-3] + ".yaml" in rels, f"section .yaml missing from the bundle manifest: {md_rel}"
    # Every committed CSV of every processed chapter, and nothing else.
    chapters = {os.path.dirname(p) for p in discover_section_md_files()}
    on_disk = {
        os.path.relpath(os.path.join(chapter, "tables", name), REPO_ROOT)
        for chapter in chapters
        if os.path.isdir(os.path.join(chapter, "tables"))
        for name in os.listdir(os.path.join(chapter, "tables"))
        if name.endswith(".csv")
    }
    assert {rel for rel in rels if rel.endswith(".csv")} == on_disk


@pytest.mark.parametrize("rel", [rel for _s, rel in sync_package_data.bundle_manifest()])
def test_every_bundled_file_is_byte_identical_to_its_repo_original(rel, bundle):
    src = os.path.join(REPO_ROOT, rel)
    dst = os.path.join(bundle, rel)
    assert os.path.isfile(dst), f"missing from bundle: {rel}"
    assert filecmp.cmp(src, dst, shallow=False), f"bundle copy differs from the repo original: {rel}"


def test_bundle_includes_the_md_files_front_matter_needs(bundle):
    # Non-obvious requirement: TRLoader.front_matter() reads the sibling .md at
    # runtime for each section's title, so a yaml-only bundle would leave an
    # installed package describing every section with an empty title.
    for md_path in discover_section_md_files():
        rel = os.path.relpath(md_path, REPO_ROOT)
        assert os.path.isfile(os.path.join(bundle, rel)), f"{rel} not bundled"


def test_bundle_check_is_clean_for_a_fresh_bundle(bundle):
    assert sync_package_data.check_bundle(bundle) == []


def test_sync_is_idempotent(bundle, tmp_path):
    second = tmp_path / "again"
    sync_package_data.build_bundle(str(second))
    written_a = sorted(os.path.relpath(os.path.join(r, f), bundle)
                       for r, _d, fs in os.walk(bundle) for f in fs)
    written_b = sorted(os.path.relpath(os.path.join(r, f), str(second))
                       for r, _d, fs in os.walk(str(second)) for f in fs)
    assert written_a == written_b


def test_build_bundle_removes_files_that_left_the_repo(tmp_path):
    dest = tmp_path / "data"
    sync_package_data.build_bundle(str(dest))
    stray = dest / "TR-38.901" / "v19.4.0" / "07-channel-models" / "gone.yaml"
    stray.write_text("removed from the repo but still in the bundle\n")
    sync_package_data.build_bundle(str(dest))  # a clean rebuild wipes first
    assert not stray.exists(), "a rebuild left a file that no longer exists in the repo"


# ---------------------------------------------------------------------------
# The staleness guard's own guard
# ---------------------------------------------------------------------------
def test_check_bundle_detects_a_stale_file(tmp_path):
    dest = tmp_path / "data"
    sync_package_data.build_bundle(str(dest))
    target = dest / "TR-38.901" / "v19.4.0" / "07-channel-models" / "7.6-additional-components.yaml"
    target.write_text(target.read_text().replace("'15'", "'99'", 1))
    problems = sync_package_data.check_bundle(str(dest))
    assert any("STALE" in p for p in problems), problems


def test_check_bundle_detects_an_extra_file(tmp_path):
    dest = tmp_path / "data"
    sync_package_data.build_bundle(str(dest))
    (dest / "TR-38.901" / "v19.4.0" / "stowaway.yaml").write_text("x: 1\n")
    problems = sync_package_data.check_bundle(str(dest))
    assert any("extra file" in p for p in problems), problems


def test_check_bundle_reports_a_missing_bundle(tmp_path):
    problems = sync_package_data.check_bundle(str(tmp_path / "nope"))
    assert problems and "no bundle" in problems[0]


@pytest.mark.skipif(not os.path.isdir(WORKING_TREE_BUNDLE),
                    reason="no bundle generated in this working tree (it is gitignored / build-time only)")
def test_working_tree_bundle_is_not_stale():
    # If a bundle has been generated locally, it must match the repo. This is
    # the check that would catch someone building a wheel from an old bundle.
    assert sync_package_data.check_bundle(WORKING_TREE_BUNDLE) == []


# ---------------------------------------------------------------------------
# 2. The loader resolves from a bundle (the installed-wheel code path)
# ---------------------------------------------------------------------------
def _bundle_only_loader(bundle):
    return TRLoader("TR-38.901", "TR 38.901", "v19.4.0", tr38901._SECTION_REGISTRY, data_roots=[bundle])


def test_loader_resolves_data_from_a_bundle_only_root(bundle):
    loader = _bundle_only_loader(bundle)
    section = loader.load("7.6")
    assert section.ground_material(material_class="Metal").c_sigma == "10^7"
    assert section.absolute_time_of_arrival(scenario="SMa").mu_lg_delta_tau == "-7.702"


def test_loader_reads_front_matter_from_a_bundle_only_root(bundle):
    loader = _bundle_only_loader(bundle)
    assert loader.front_matter("7.6")["title"] == "Additional modelling components"
    assert loader.front_matter("7.9")["section"] == "7.9"


@pytest.mark.parametrize("section_id", ["7.4", "7.5", "7.6", "7.9"])
def test_every_section_loads_identically_from_bundle_and_repo(section_id, bundle):
    from_bundle = _bundle_only_loader(bundle).load(section_id)
    from_repo = tr38901.section(section_id)
    assert from_bundle._data.model_dump() == from_repo._data.model_dump()


def test_annex_also_resolves_from_a_bundle(bundle):
    from tr3gpp import tr36777
    loader = TRLoader("TR-36.777", "TR 36.777", "v15.0.0", tr36777._ANNEX_REGISTRY, data_roots=[bundle])
    assert loader.load("B").alternative_1(scenario="RMa-AV", condition="LOS").desired_k_db is not None
    assert loader.front_matter("B")["section"] == "Annex B"


# ---------------------------------------------------------------------------
# 3. A stale bundle can never shadow the repo
# ---------------------------------------------------------------------------
def test_default_data_roots_put_the_repo_checkout_first():
    roots = _loader.default_data_roots()
    assert roots == [_loader.REPO_ROOT, _loader.BUNDLED_DATA_ROOT]
    # ...and the repo-root candidate really is this repo when running from a clone.
    assert (_loader.REPO_ROOT / "TR-38.901").is_dir()


def test_repo_checkout_wins_over_a_stale_bundle(tmp_path):
    dest = tmp_path / "data"
    sync_package_data.build_bundle(str(dest))
    target = dest / "TR-38.901" / "v19.4.0" / "07-channel-models" / "7.6-additional-components.yaml"
    data = yaml.safe_load(target.read_text())
    for entry in data["ground_material_properties"]:
        if entry["material_class"] == "Metal":
            entry["c_sigma"] = "STALE-BUNDLE-VALUE"
    target.write_text(yaml.safe_dump(data, sort_keys=False))
    # sanity: the corrupted bundle really would serve the wrong value on its own
    assert _bundle_only_loader(str(dest)).load("7.6").ground_material(
        material_class="Metal").c_sigma == "STALE-BUNDLE-VALUE"

    both = TRLoader("TR-38.901", "TR 38.901", "v19.4.0", tr38901._SECTION_REGISTRY,
                    data_roots=[REPO_ROOT, str(dest)])
    assert both.load("7.6").ground_material(material_class="Metal").c_sigma == "10^7", (
        "a stale bundle shadowed the live repo data"
    )


def test_bundle_is_used_when_the_repo_root_is_absent(tmp_path):
    # The installed-wheel situation: a first root that doesn't exist at all.
    dest = tmp_path / "data"
    sync_package_data.build_bundle(str(dest))
    loader = TRLoader("TR-38.901", "TR 38.901", "v19.4.0", tr38901._SECTION_REGISTRY,
                      data_roots=[tmp_path / "no-such-repo", str(dest)])
    assert loader.load("7.4").pathloss(scenario="RMa", condition="LOS").condition == "LOS"


def test_missing_everywhere_names_every_root_tried(tmp_path):
    loader = TRLoader("TR-38.901", "TR 38.901", "v19.4.0", tr38901._SECTION_REGISTRY,
                      data_roots=[tmp_path / "a", tmp_path / "b"])
    with pytest.raises(SectionNotFoundError) as exc:
        loader.load("7.6")
    message = str(exc.value)
    assert "looked in" in message and str(tmp_path / "a") in message and str(tmp_path / "b") in message


def test_front_matter_returns_empty_rather_than_raising_when_no_md_anywhere(tmp_path):
    dest = tmp_path / "data"
    sync_package_data.build_bundle(str(dest))
    os.remove(dest / "TR-38.901" / "v19.4.0" / "07-channel-models" / "7.6-additional-components.md")
    loader = TRLoader("TR-38.901", "TR 38.901", "v19.4.0", tr38901._SECTION_REGISTRY,
                      data_roots=[tmp_path / "no-such-repo", str(dest)])
    assert loader.front_matter("7.6") == {}
    # the data itself still loads -- the .md is only needed for the title
    assert isinstance(loader.load("7.6")._data, Section76Data)


# ---------------------------------------------------------------------------
# Packaging declaration: the globs in pyproject.toml must actually match the
# bundle's layout, or the wheel would ship an empty data/ directory.
# ---------------------------------------------------------------------------
def test_pyproject_package_data_globs_match_the_real_bundle_layout(bundle):
    import glob
    import re

    with open(os.path.join(REPO_ROOT, "tools", "tr3gpp", "pyproject.toml")) as f:
        text = f.read()
    block = text.split("[tool.setuptools.package-data]", 1)[1]
    patterns = re.findall(r'"(data/[^"]+)"', block)
    assert patterns, "no package-data globs declared for the bundled data"

    staged = os.path.join(os.path.dirname(bundle), "pkg")
    os.makedirs(staged, exist_ok=True)
    shutil.copytree(bundle, os.path.join(staged, "data"), dirs_exist_ok=True)

    matched = set()
    for pattern in patterns:
        matched |= {os.path.relpath(p, staged) for p in glob.glob(os.path.join(staged, pattern))}
    expected = {os.path.join("data", rel) for _s, rel in sync_package_data.bundle_manifest()}
    assert matched == expected, (
        f"package-data globs miss {sorted(expected - matched)[:5]} / include extra {sorted(matched - expected)[:5]}"
    )
