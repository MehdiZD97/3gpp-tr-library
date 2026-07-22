"""
Self-describing surface for `tr_api` -- so a user (or the CLI) can discover
which TRs / sections / parameters exist and how to call them, without reading
source or memorizing names and signatures.

Design (Phase 8, Option A): the metadata is derived by **runtime inspection**
of the existing accessor classes -- `inspect` for each public method's keyword
args, its return annotation (single vs list), and its docstring; `property` vs
method is distinguished structurally. The accessors stay the single behavioural
source of truth; this module *describes* them, it never reimplements their
dispatch. The one thing inspection can't reach -- *which data field a lookup
method queries*, needed to list the values actually available -- is supplied by
a tiny explicit `_QUERYABLE` map on each accessor (method -> data attribute +
{arg: field}). Human-readable section titles come from the section `.md`
front-matter (`TRLoader.front_matter`), the authoritative source, not the
registry.

Both TRs are first-class: TR 38.901's numbered `section()` clauses and TR
36.777's lettered `annex()` are described through the same `UnitInfo`/verb
machinery -- nothing here privileges `section()`.
"""
import inspect
import typing
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class ParamInfo:
    """One keyword argument of a lookup method."""

    name: str                          # the keyword arg name, e.g. "scenario"
    field: str                         # underlying data field ("@keys" = dict keys)
    available: Optional[List[str]] = None   # distinct values in the data, if computed


@dataclass
class MemberInfo:
    """One callable member of an accessor -- a lookup method or a property."""

    name: str
    kind: str                          # "method" | "property"
    args: List[ParamInfo] = field(default_factory=list)
    returns: str = ""                  # display type, e.g. "PathlossEntry" / "list[RcsModel2Entry]"
    returns_list: bool = False
    doc: str = ""
    data_attribute: str = ""           # the Section*Data attribute it reads (used by `dump`)


@dataclass
class UnitInfo:
    """A described section (TR 38.901) or annex (TR 36.777)."""

    tr_module: str                     # "tr38901" | "tr36777"
    tr_label: str                      # "TR 38.901"
    verb: str                          # "section" | "annex" -- how you access it
    key: str                           # what to pass to the verb: "7.4" | "B"
    clause: str                        # real clause/annex id from front matter: "7.4" | "Annex B"
    title: str
    version: str
    members: List[MemberInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Runtime inspection of an accessor class
# ---------------------------------------------------------------------------
def _type_display(annotation):
    """(display_name, is_list) for a return annotation."""
    if annotation is inspect.Signature.empty or annotation is None:
        return ("", False)
    origin = typing.get_origin(annotation)
    if origin in (list, List):
        args = typing.get_args(annotation) or (Any,)
        inner = args[0]
        return (f"list[{getattr(inner, '__name__', str(inner))}]", True)
    return (getattr(annotation, "__name__", str(annotation)), False)


def discover_members(accessor_cls):
    """[MemberInfo] for an accessor class from inspection + its `_QUERYABLE`.

    Args carry their `field` mapping but not `available` values yet (that needs
    loaded data -- see `fill_available_values`).
    """
    queryable = getattr(accessor_cls, "_QUERYABLE", {})
    members = []
    for name in sorted(dir(accessor_cls)):
        if name.startswith("_"):
            continue
        static = inspect.getattr_static(accessor_cls, name)
        if isinstance(static, property):
            disp, is_list = _type_display(inspect.signature(static.fget).return_annotation)
            members.append(MemberInfo(
                name=name, kind="property", returns=disp, returns_list=is_list,
                doc=inspect.getdoc(static.fget) or "", data_attribute=name,
            ))
        elif inspect.isfunction(static):
            sig = inspect.signature(static)
            data_attr, arg_fields = queryable.get(name, (name, {}))
            args = [
                ParamInfo(name=pname, field=arg_fields.get(pname, pname))
                for pname in sig.parameters if pname != "self"
            ]
            disp, is_list = _type_display(sig.return_annotation)
            members.append(MemberInfo(
                name=name, kind="method", args=args, returns=disp, returns_list=is_list,
                doc=inspect.getdoc(static) or "", data_attribute=data_attr,
            ))
    return members


def _distinct(data_value, field_name):
    """Distinct string values of `field_name` across a data attribute (a flat
    list of models, or a dict-of-tables whose values have `.entries`)."""
    if field_name == "@keys":
        return sorted(data_value.keys()) if isinstance(data_value, dict) else []
    if isinstance(data_value, dict):
        entries = [e for table in data_value.values() for e in getattr(table, "entries", [])]
    elif isinstance(data_value, list):
        entries = data_value
    else:
        return None
    values = {str(getattr(e, field_name)) for e in entries if getattr(e, field_name, None) is not None}
    return sorted(values)


def fill_available_values(section_data, members):
    """Populate each method arg's `available` list from the loaded data, in place."""
    for member in members:
        if member.kind != "method":
            continue
        data_value = getattr(section_data, member.data_attribute, None)
        if data_value is None:
            continue
        for arg in member.args:
            arg.available = _distinct(data_value, arg.field)


# ---------------------------------------------------------------------------
# Unit (section / annex) level -- driven by a TRLoader + its access verb
# ---------------------------------------------------------------------------
def list_units(loader, verb, tr_module, detail=False, with_values=False, version=None):
    """[UnitInfo] for every processed section/annex of one TR.

    detail=False -> identifier + title only (cheap). detail=True -> also each
    unit's callable members; with_values=True additionally loads the data to
    fill in the available scenario/target/... values.
    """
    units = []
    for key in sorted(loader.registry):
        if detail:
            units.append(describe_unit(loader, verb, tr_module, key, with_values=with_values, version=version))
        else:
            fm = loader.front_matter(key, version)
            units.append(UnitInfo(
                tr_module=tr_module, tr_label=loader.tr_label, verb=verb, key=key,
                clause=fm.get("section", key), title=fm.get("title", ""),
                version=version or loader.default_version,
            ))
    return units


def describe_unit(loader, verb, tr_module, key, with_values=True, version=None):
    """Full callable-surface description of one section/annex."""
    fm = loader.front_matter(key, version)
    members = discover_members(loader.accessor_class(key))
    if with_values:
        fill_available_values(loader.load(key, version)._data, members)
    return UnitInfo(
        tr_module=tr_module, tr_label=loader.tr_label, verb=verb, key=key,
        clause=fm.get("section", key), title=fm.get("title", ""),
        version=version or loader.default_version, members=members,
    )


# ---------------------------------------------------------------------------
# All-TRs -- the backbone the CLI renders. Lazy import of the TR modules keeps
# this module free of a circular import (the TR modules import this one).
# ---------------------------------------------------------------------------
def registered_trs():
    """{module_name: (module, verb)} for every TR module the API exposes."""
    from . import tr36777, tr38901
    return {
        "tr38901": (tr38901, tr38901.UNIT_KIND),
        "tr36777": (tr36777, tr36777.UNIT_KIND),
    }


def all_units(detail=False, with_values=False):
    """[UnitInfo] across every TR -- the complete self-description of the API."""
    units = []
    for tr_module, (module, verb) in registered_trs().items():
        units += list_units(module._loader, verb, tr_module, detail=detail, with_values=with_values)
    return units


def describe(tr_module, key, with_values=True, version=None):
    """describe_unit by TR *module name* (e.g. 'tr38901') -- the form the CLI uses."""
    from ._loader import SectionNotFoundError
    trs = registered_trs()
    if tr_module not in trs:
        raise SectionNotFoundError(f"No TR module {tr_module!r}. Available: {sorted(trs)}")
    module, verb = trs[tr_module]
    return describe_unit(module._loader, verb, tr_module, key, with_values=with_values, version=version)


def member_data(accessor, member):
    """The raw data behind a member (the whole list/dict/model) -- for `dump`.

    Keeps data access in the API layer so the CLI never reaches into the
    accessor's private `_data`.
    """
    return getattr(accessor._data, member.data_attribute)


def to_jsonable(data_value):
    """Normalize any data value (model / list / dict) to a JSON-serializable structure."""
    from pydantic import BaseModel
    if isinstance(data_value, BaseModel):
        return data_value.model_dump()
    if isinstance(data_value, list):
        return [to_jsonable(x) for x in data_value]
    if isinstance(data_value, dict):
        return {k: to_jsonable(v) for k, v in data_value.items()}
    return data_value


def to_table(data_value):
    """(header, rows) if `data_value` is a flat list of models (the CSV-dumpable
    shape, matching the committed tables/*.csv orientation), else None."""
    from pydantic import BaseModel
    if isinstance(data_value, list) and data_value and all(isinstance(x, BaseModel) for x in data_value):
        header = list(data_value[0].model_dump().keys())
        rows = [[m.model_dump().get(h) for h in header] for m in data_value]
        return header, rows
    return None


def load_accessor(tr_module, key, version=None):
    """The loaded accessor for a (tr_module, key), via the TR's public verb.

    Goes through the real `section()`/`annex()` path -- so anything built on
    this (the CLI's `get`/`dump`) is exercising the same accessors, not a copy.
    """
    trs = registered_trs()
    if tr_module not in trs:
        from ._loader import SectionNotFoundError
        raise SectionNotFoundError(f"No TR module {tr_module!r}. Available: {sorted(trs)}")
    module, verb = trs[tr_module]
    return getattr(module, verb)(key, version)
