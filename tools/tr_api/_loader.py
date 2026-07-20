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
"""
from pathlib import Path

import yaml

# This file lives at tools/tr_api/_loader.py; the repo root is two levels up.
_REPO_ROOT = Path(__file__).resolve().parents[2]


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
    """

    def __init__(self, tr_dir, tr_label, default_version, registry, repo_root=_REPO_ROOT):
        self.tr_dir = tr_dir
        self.tr_label = tr_label
        self.default_version = default_version
        self.registry = registry
        self.repo_root = Path(repo_root)
        self._cache = {}

    def load(self, section_id, version=None):
        version = version or self.default_version
        cache_key = (section_id, version)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if section_id not in self.registry:
            raise SectionNotFoundError(
                f"No data available for {self.tr_label} section {section_id!r}. "
                f"Processed: {sorted(self.registry)}"
            )
        rel_path, model_cls, accessor_cls = self.registry[section_id]
        yaml_path = self.repo_root / self.tr_dir / version / rel_path
        if not yaml_path.is_file():
            raise SectionNotFoundError(
                f"No data file for {self.tr_label} {section_id} version {version!r} -- expected {yaml_path}"
            )
        with open(yaml_path) as f:
            raw = yaml.safe_load(f)
        accessor = accessor_cls(section_id, version, model_cls(**raw))
        self._cache[cache_key] = accessor
        return accessor
