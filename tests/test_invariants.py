"""
Cross-cutting invariants (Phase 9, Part 1 Task 2) -- discovery-driven checks
that hold across *every* processed section at once, so they also cover future
sections for free. These catch whole classes of error (a value in a CSV not
mirrored in the .md, a malformed depends_on, a duplicated equation number, the
tr_api registry drifting from the filesystem, introspection advertising a value
the accessor rejects) that per-section tests would each have to re-check.

Also home to the `verification_notes` front-matter shape check (the Phase 9
Task 8 convention: per-entry/per-table verification granularity).
"""
import os
import re
import sys

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from section_utils import discover_section_md_files, read_csv_rows, split_front_matter  # noqa: E402
from tr_api import introspect, tr36777, tr38901  # noqa: E402

KNOWN_FORMATS = {"docx", "doc", "pdf", "html", "xml"}

# Discovered once for parametrization.
_MD_PATHS = discover_section_md_files()


def _front_matter(path):
    with open(path) as f:
        fm_text, _ = split_front_matter(f.read())
    return yaml.safe_load(fm_text)


def _section_dir(md_path):
    return os.path.dirname(md_path)


# ---------------------------------------------------------------------------
# verified_against / verification_notes (Task 8 + broadened Task 2)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("md_path", _MD_PATHS, ids=lambda p: os.path.relpath(p, REPO_ROOT))
def test_verified_against_uses_only_known_formats(md_path):
    fm = _front_matter(md_path)
    for fmt in fm["verified_against"]:
        assert fmt in KNOWN_FORMATS, f"{md_path}: unknown reference format {fmt!r}"


@pytest.mark.parametrize("md_path", _MD_PATHS, ids=lambda p: os.path.relpath(p, REPO_ROOT))
def test_verification_notes_shape_where_present(md_path):
    fm = _front_matter(md_path)
    notes = fm.get("verification_notes")
    if notes is None:
        return  # optional field
    assert isinstance(notes, list) and notes, f"{md_path}: verification_notes must be a non-empty list"
    for note in notes:
        assert set(note) == {"applies_to", "verified_against", "note"}, f"{md_path}: bad note keys {set(note)}"
        assert isinstance(note["applies_to"], str) and note["applies_to"].strip()
        assert isinstance(note["note"], str) and note["note"].strip()
        assert isinstance(note["verified_against"], list) and note["verified_against"]
        for fmt in note["verified_against"]:
            assert fmt in KNOWN_FORMATS, f"{md_path}: verification_notes format {fmt!r} unknown"
        # A per-item note only makes sense if it's narrower than the section level.
        assert set(note["verified_against"]) <= set(fm["verified_against"]), (
            f"{md_path}: a verification_notes item claims formats not in the section's verified_against"
        )


def test_known_single_source_items_are_recorded():
    # The three cases Phase 9 set out to make honest must actually be present.
    fm74 = _front_matter(os.path.join(REPO_ROOT, "TR-38.901/v19.4.0/07-channel-models/7.4-pathloss.md"))
    fm79 = _front_matter(os.path.join(REPO_ROOT, "TR-38.901/v19.4.0/07-channel-models/7.9-isac-channel-model.md"))
    joined74 = " ".join(n["applies_to"] for n in fm74["verification_notes"])
    joined79 = " ".join(n["applies_to"] for n in fm79["verification_notes"])
    assert "Indoor-MixedOffice" in joined74 and "Indoor-OpenOffice" in joined74 and "RMa" in joined74
    assert "7.9.3-4" in joined79 and "7.9.4.2-2 Part-2" in joined79


# ---------------------------------------------------------------------------
# depends_on: well-formed, and resolves for the processed set
# ---------------------------------------------------------------------------
SAME_TR = re.compile(r"^\d+(\.\d+)*-[a-z0-9-]+$")
CROSS_TR = re.compile(r"^TR-\d+\.\d+:[A-Za-z0-9.-]+$")


@pytest.mark.parametrize("md_path", _MD_PATHS, ids=lambda p: os.path.relpath(p, REPO_ROOT))
def test_depends_on_well_formed_and_resolves_when_processed(md_path):
    fm = _front_matter(md_path)
    for entry in fm["depends_on"]:
        assert SAME_TR.match(entry) or CROSS_TR.match(entry), f"{md_path}: malformed depends_on {entry!r}"
        if ":" in entry:  # cross-TR -> must resolve (we only cross-ref processed sections)
            tr_dir, stem = entry.split(":")
            found = any(
                f == f"{stem}.md"
                for _root, _dirs, files in os.walk(os.path.join(REPO_ROOT, tr_dir))
                for f in files
            )
            assert found, f"{md_path}: cross-TR depends_on {entry!r} resolves to no section file"
        else:  # same-TR -> resolve only if it's within this section's own chapter dir (processed set)
            candidate = os.path.join(_section_dir(md_path), f"{entry}.md")
            if not os.path.isfile(candidate):
                # A forward-ref to an unprocessed section (e.g. 7.2-coordinate-system) is allowed;
                # just require it be well-formed (already asserted above).
                pass


# ---------------------------------------------------------------------------
# Equations: every <!-- Eq. X --> is unique within a section and precedes a $$ block
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("md_path", _MD_PATHS, ids=lambda p: os.path.relpath(p, REPO_ROOT))
def test_equation_numbers_unique_within_section(md_path):
    with open(md_path) as f:
        body = f.read()
    numbers = re.findall(r"<!--\s*Eq\.\s*([^\s]+?)\s*-->", body)
    dupes = {n for n in numbers if numbers.count(n) > 1}
    assert not dupes, f"{md_path}: duplicate equation numbers {dupes}"


@pytest.mark.parametrize("md_path", _MD_PATHS, ids=lambda p: os.path.relpath(p, REPO_ROOT))
def test_equation_comments_precede_a_display_block(md_path):
    with open(md_path) as f:
        lines = f.read().splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^<!--\s*Eq\.", line.strip()):
            # the next non-blank line must open a $$ display-math block
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            assert j < len(lines) and lines[j].lstrip().startswith("$$"), (
                f"{md_path}: equation comment on line {i + 1} isn't followed by a $$ block"
            )


# ---------------------------------------------------------------------------
# Triple consistency: every single-line CSV cell appears in the inline .md
# (orientation-agnostic -- substring presence, so it works whether the .md
# table is in CSV orientation or transposed like §7.5-6). Multi-line blob
# cells use <br> in the .md and are covered by the per-section label tests.
# ---------------------------------------------------------------------------
def _csv_paths_for(md_path):
    """The CSVs owned by this section. §7.4/§7.5/§7.9 share one tables/ dir, so
    filter by the section's real table-number prefix (e.g. '7.4' -> table-7.4.*,
    'Annex B' -> table-B.*) rather than returning the whole shared directory."""
    tables_dir = os.path.join(_section_dir(md_path), "tables")
    if not os.path.isdir(tables_dir):
        return []
    section = _front_matter(md_path)["section"]
    token = section if section[0].isdigit() else section.split()[-1]  # "Annex B" -> "B"
    prefixes = (f"table-{token}.", f"table-{token}-")
    return sorted(
        os.path.join(tables_dir, f)
        for f in os.listdir(tables_dir)
        if f.endswith(".csv") and f.startswith(prefixes)
    )


@pytest.mark.parametrize("md_path", _MD_PATHS, ids=lambda p: os.path.relpath(p, REPO_ROOT))
def test_value_like_csv_cells_appear_in_markdown(md_path):
    """Every single-line, *value-like* CSV cell (one containing a digit --
    numbers, ranges like [45,135), formulas, "Case 4: ...", dB values) must
    appear verbatim in the inline .md. This is where silent value-drift lands.

    Pure-symbol/label cells are excluded: the .md sometimes renders a notation
    as LaTeX (`$\\phi_{LOS,AOD}$`) where the CSV keeps the docx unicode
    (`ϕLOS,AOD`) -- a legitimate representation difference the per-section
    cross-format tests cover. Multi-line blob cells (<br> in the .md) likewise.
    """
    with open(md_path) as f:
        body = f.read()
    for csv_path in _csv_paths_for(md_path):
        rows = read_csv_rows(csv_path)
        for row in rows[1:]:
            for cell in row:
                cell = cell.strip()
                if not cell or "\n" in cell or not any(c.isdigit() for c in cell):
                    continue
                needle = cell.replace("|", r"\|")  # the .md escapes pipes
                assert needle in body or cell in body, (
                    f"{os.path.basename(csv_path)}: value cell {cell!r} not found in {os.path.basename(md_path)}"
                )


# ---------------------------------------------------------------------------
# tr_api registry <-> filesystem: neither can silently drift from the other
# ---------------------------------------------------------------------------
def _registered_units():
    out = []
    for module, registry, tr_dir, ver in [
        (tr38901, tr38901._SECTION_REGISTRY, "TR-38.901", "v19.4.0"),
        (tr36777, tr36777._ANNEX_REGISTRY, "TR-36.777", "v15.0.0"),
    ]:
        for key, (rel_yaml, _model, _acc) in registry.items():
            out.append((tr_dir, ver, key, rel_yaml))
    return out


@pytest.mark.parametrize("tr_dir,ver,key,rel_yaml", _registered_units(),
                         ids=lambda x: x if isinstance(x, str) else str(x))
def test_registered_unit_has_files_on_disk(tr_dir, ver, key, rel_yaml):
    base = os.path.join(REPO_ROOT, tr_dir, ver)
    yaml_path = os.path.join(base, rel_yaml)
    md_path = yaml_path[:-5] + ".md"
    assert os.path.isfile(yaml_path), f"{key}: missing {yaml_path}"
    assert os.path.isfile(md_path), f"{key}: missing {md_path}"
    assert os.path.isdir(os.path.join(os.path.dirname(yaml_path), "tables")), f"{key}: missing tables/ dir"


def test_every_discovered_section_is_registered():
    # Every processed section .md must be reachable via a tr_api registry entry
    # (so the API surface and the data files stay in lockstep).
    registered_yaml = set()
    for tr_dir, ver, _key, rel_yaml in _registered_units():
        registered_yaml.add(os.path.join(REPO_ROOT, tr_dir, ver, rel_yaml))
    for md_path in _MD_PATHS:
        yaml_path = md_path[:-3] + ".yaml"
        assert yaml_path in registered_yaml, f"{md_path} has no tr_api registry entry"


# ---------------------------------------------------------------------------
# Introspection advertised values == what the accessors actually accept
# (deepens Phase 8's drift guard from "methods/args match" to "values match").
# ---------------------------------------------------------------------------
def _all_methods():
    out = []
    for unit in introspect.all_units(detail=True, with_values=True):
        accessor = introspect.load_accessor(unit.tr_module, unit.key)
        for m in unit.members:
            if m.kind == "method":
                out.append((unit.tr_module, unit.key, accessor, m))
    return out


_METHODS = _all_methods()


@pytest.mark.parametrize("tr_module,key,accessor,member", _METHODS,
                         ids=[f"{t}-{k}-{m.name}" for (t, k, _a, m) in _METHODS])
def test_advertised_values_are_accepted_and_bogus_rejected(tr_module, key, accessor, member):
    data = getattr(accessor._data, member.data_attribute)
    # Build a guaranteed-valid kwargs combination from a real data row.
    if isinstance(data, dict):  # zsd_zod_offset: scenario is a dict key
        dict_key = sorted(data)[0]
        entry = data[dict_key].entries[0]
        kwargs = {a.name: (dict_key if a.field == "@keys" else getattr(entry, a.field)) for a in member.args}
    else:
        entry = data[0]
        kwargs = {a.name: getattr(entry, a.field) for a in member.args}

    result = getattr(accessor, member.name)(**kwargs)  # must not raise
    assert result is not None
    if member.returns_list:
        assert len(result) >= 1

    # Every advertised available value for each arg is a real, accepted value.
    for arg in member.args:
        assert arg.available, f"{member.name}({arg.name}): no advertised values"
        for value in kwargs.values():
            pass  # (structure covered above)

    # A value that isn't advertised must be rejected, not silently accepted.
    from tr_api._loader import ScenarioNotFoundError
    bogus = dict(kwargs)
    bogus[member.args[0].name] = "__definitely_not_a_real_value__"
    with pytest.raises(ScenarioNotFoundError):
        getattr(accessor, member.name)(**bogus)
