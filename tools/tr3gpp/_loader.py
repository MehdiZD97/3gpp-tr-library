"""
TR-agnostic loading machinery shared by every per-TR module (`tr38901`,
`tr36777`, and any future sibling).

A per-TR module supplies a `_SECTION_REGISTRY` mapping a section/annex id to
`(yaml_path_relative_to_version_dir, pydantic_model, accessor_class)`, and
constructs a `TRLoader` with its TR directory name, human-readable label,
and default version. The loader resolves the YAML path, loads + Pydantic-
validates it, wraps it in the accessor class, and caches per (id, version).

Factoring this out is the Phase 5 generalization: before a second TR
existed, this logic lived inline in `tr38901.py` with `"TR-38.901"` and
`"v19.4.0"` hardcoded. Nothing here knows about a specific TR.

Data resolution (Phase 10 Group C)
----------------------------------
The processed TR data lives at the **repo root** (`TR-38.901/`, `TR-36.777/`)
because that is how people browse it on GitHub -- a core value proposition,
not an implementation detail, so it cannot move inside this package. But a
wheel installed into `site-packages/` has no repo around it. So the loader
resolves each file against an ordered list of data roots:

1. **The repo checkout** -- `parents[2]` of this file. Real in an editable
   install from a clone; meaningless (and non-existent) inside site-packages.
2. **The bundled copy** -- `<package>/data/`, produced at build time by
   `tools/sync_package_data.py` and shipped inside the wheel.

**The repo checkout is deliberately tried FIRST**, which is the reverse of
the obvious "prefer what's bundled" instinct. The reason is staleness: in a
clone, a developer editing `TR-38.901/.../7.6-additional-components.yaml`
must see that edit immediately. If a previously generated `data/` bundle won,
every test and every query would silently read old values -- and for a
project whose entire premise is verified accuracy, silently serving stale
numbers is the worst possible bug. Ordering it this way makes that failure
mode unreachable rather than merely test-guarded (it is *also* test-guarded,
see tests/test_bundled_data.py). In an installed wheel the repo-root
candidate simply doesn't exist, so the bundled copy is used.
"""
import re
from pathlib import Path

import yaml

_FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _package_dir():
    """This package's directory on disk.

    Uses `importlib.resources` (the supported way to locate package files)
    with a `__file__` fallback, so it keeps working if the package is ever
    loaded through a non-filesystem loader.
    """
    try:
        from importlib.resources import files
        return Path(str(files(__package__)))
    except Exception:  # pragma: no cover - defensive; normal installs hit the fast path
        return Path(__file__).resolve().parent


PACKAGE_DIR = _package_dir()

# The bundled data shipped inside the wheel (absent in a plain clone until
# tools/sync_package_data.py is run; it is gitignored, generated on build).
BUNDLED_DATA_ROOT = PACKAGE_DIR / "data"

# The repo checkout: this file lives at tools/tr3gpp/_loader.py, so the repo
# root is two levels up. Inside site-packages this resolves to something
# meaningless, which is exactly why resolution is per-file rather than by
# sniffing a directory.
REPO_ROOT = Path(__file__).resolve().parents[2]


def default_data_roots():
    """The ordered data roots: live repo checkout first, bundled copy second.

    See this module's docstring for why the repo checkout wins.
    """
    return [REPO_ROOT, BUNDLED_DATA_ROOT]


class SectionNotFoundError(LookupError):
    """Raised when a section/annex id or version has no processed data available."""


class ScenarioNotFoundError(LookupError):
    """Raised when a lookup's scenario/condition/variant doesn't match any entry."""


class TRLoader:
    """
    Loads and caches processed sections/annexes for one TR.

    tr_dir:          top-level directory name, e.g. "TR-38.901".
    tr_label:        human-readable label for error messages, e.g. "TR 38.901".
    default_version: version used when a caller doesn't pass one, e.g. "v19.4.0".
    registry:        {id: (rel_yaml_path, model_cls, accessor_cls)}.
    data_roots:      ordered roots to resolve data files against; defaults to
                     `default_data_roots()`. Passing an explicit list is how
                     tests exercise the bundled-only and repo-only modes.
    """

    def __init__(self, tr_dir, tr_label, default_version, registry, data_roots=None):
        self.tr_dir = tr_dir
        self.tr_label = tr_label
        self.default_version = default_version
        self.registry = registry
        self.data_roots = [Path(r) for r in (data_roots if data_roots is not None else default_data_roots())]
        self._cache = {}

    # --- resolution -------------------------------------------------------
    def _relative(self, section_id, version, suffix=None):
        rel_path = Path(self.registry[section_id][0])
        if suffix is not None:
            rel_path = rel_path.with_suffix(suffix)
        return Path(self.tr_dir) / version / rel_path

    def _resolve(self, relative):
        """(first existing path, [every path tried]) for a repo-relative path."""
        tried = []
        for root in self.data_roots:
            candidate = root / relative
            tried.append(candidate)
            if candidate.is_file():
                return candidate, tried
        return None, tried

    def _require_registered(self, section_id):
        if section_id not in self.registry:
            raise SectionNotFoundError(
                f"No data available for {self.tr_label} section {section_id!r}. "
                f"Processed: {sorted(self.registry)}"
            )

    # --- public API -------------------------------------------------------
    def load(self, section_id, version=None):
        version = version or self.default_version
        cache_key = (section_id, version)
        if cache_key in self._cache:
            return self._cache[cache_key]

        self._require_registered(section_id)
        _rel_path, model_cls, accessor_cls = self.registry[section_id]
        yaml_path, tried = self._resolve(self._relative(section_id, version))
        if yaml_path is None:
            looked = ", ".join(str(p) for p in tried)
            raise SectionNotFoundError(
                f"No data file for {self.tr_label} {section_id} version {version!r} -- looked in: {looked}"
            )
        with open(yaml_path) as f:
            raw = yaml.safe_load(f)
        accessor = accessor_cls(section_id, version, model_cls(**raw))
        self._cache[cache_key] = accessor
        return accessor

    def accessor_class(self, section_id):
        """The accessor class registered for a section/annex id (no data loaded)."""
        self._require_registered(section_id)
        return self.registry[section_id][2]

    def front_matter(self, section_id, version=None):
        """The parsed YAML front matter of a section/annex's `.md` file.

        The registry knows only the `.yaml` data path; the human-readable
        `title` (and the real clause/annex identifier) live in the sibling
        `.md`'s front matter, which is the single authoritative source for
        those -- so the introspection layer reads them from here rather than
        duplicating titles into the registry. Returns {} if the .md is absent.

        This is why the wheel has to bundle the `.md` files as well as the
        `.yaml` ones: without them an installed package would describe every
        section with an empty title.
        """
        version = version or self.default_version
        self._require_registered(section_id)
        md_path, _tried = self._resolve(self._relative(section_id, version, suffix=".md"))
        if md_path is None:
            return {}
        match = _FRONT_MATTER_RE.match(md_path.read_text())
        return yaml.safe_load(match.group(1)) if match else {}
