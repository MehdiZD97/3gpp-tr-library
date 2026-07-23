"""
Tests for tr_api's introspection layer (Phase 8) -- the self-describing surface
the CLI renders. Two things matter most here: it describes the *actual*
accessor surface (both the section() and annex() worlds, symmetrically), and it
can't silently diverge from the accessors (the drift guard).

Requires tr_api installed (`pip install -e tools/tr_api`).
"""
import inspect

import pytest
from tr_api import introspect, tr36777, tr38901


# ---------------------------------------------------------------------------
# list / discovery -- both TRs, symmetric
# ---------------------------------------------------------------------------
def test_all_units_covers_both_trs():
    units = introspect.all_units()
    keys = {(u.tr_module, u.key) for u in units}
    assert keys == {("tr38901", "7.4"), ("tr38901", "7.5"), ("tr38901", "7.9"), ("tr36777", "B")}


def test_section_titles_come_from_front_matter():
    by_key = {u.key: u for u in tr38901.list_sections()}
    assert by_key["7.4"].title == "Pathloss, LOS probability and penetration modelling"
    assert by_key["7.5"].title == "Fast fading model"
    assert by_key["7.9"].title == "Channel model(s) for ISAC"
    assert all(u.verb == "section" for u in by_key.values())


def test_annex_is_first_class_with_its_own_verb():
    units = tr36777.list_annexes()
    assert len(units) == 1
    b = units[0]
    assert b.key == "B" and b.clause == "Annex B" and b.verb == "annex"
    assert b.title == "Channel modelling details"


# ---------------------------------------------------------------------------
# describe -- the actual callable surface, per shape
# ---------------------------------------------------------------------------
def test_describe_reports_section_79_new_shape_accurately():
    unit = tr38901.describe("7.9")
    members = {m.name: m for m in unit.members}
    # §7.9's distinct shape must be described, not special-cased.
    rcs2 = members["rcs_model_2"]
    assert rcs2.kind == "method"
    assert [a.name for a in rcs2.args] == ["target", "scattering_point"]
    assert rcs2.returns == "RcsModel2Entry" and rcs2.returns_list is False
    # a list-returning method and a property
    assert members["calibration"].returns_list is True
    assert members["sensing_scenarios"].kind == "property"
    assert members["sensing_scenarios"].returns == "list[SensingScenarioParameter]"


def test_describe_available_values_from_data():
    members = {m.name: m for m in tr38901.describe("7.9").members}
    rcs2 = members["rcs_model_2"]
    target_arg = next(a for a in rcs2.args if a.name == "target")
    sp_arg = next(a for a in rcs2.args if a.name == "scattering_point")
    assert "Vehicle with single scattering point" in target_arg.available
    assert set(sp_arg.available) >= {"Front", "Left", "Back", "Right", "Roof"}
    # xpr targets come from the data, not a signature
    xpr_target = tr38901.describe("7.9").members
    xpr = next(m for m in xpr_target if m.name == "xpr")
    assert set(xpr.args[0].available) == {"UAV", "Human", "Vehicle", "AGV"}


def test_describe_handles_dict_based_available_values():
    # §7.5's zsd_zod_offset reads a dict, not a flat list -- scenario values
    # are the dict keys, conditions come from the nested entries.
    z = next(m for m in tr38901.describe("7.5").members if m.name == "zsd_zod_offset")
    scenario = next(a for a in z.args if a.name == "scenario")
    condition = next(a for a in z.args if a.name == "condition")
    assert "UMa" in scenario.available and "SMa" in scenario.available
    assert set(condition.available) == {"LOS", "NLOS", "O2I"}


def test_describe_rcs_model_1_arg_field_mismatch():
    # rcs_model_1's `target` arg maps to the `sensing_target` field -- the
    # available values must still resolve (proving the explicit mapping works).
    m = next(m for m in tr38901.describe("7.9").members if m.name == "rcs_model_1")
    assert m.args[0].name == "target"
    assert set(m.args[0].available) == {"UAV with small size", "Human with RCS model 1"}


def test_describe_annex_b_multi_arg_method():
    m = {x.name: x for x in tr36777.describe("B").members}["alternative_2"]
    assert [a.name for a in m.args] == ["scenario", "parameter", "condition"]
    assert set(next(a for a in m.args if a.name == "parameter").available) == {"DS", "ASA", "ASD", "ZSA", "ZSD", "K"}


def test_every_method_arg_has_non_empty_available_values():
    # A functional drift check: if a _QUERYABLE field mapping were wrong, the
    # computed available list would be empty. Every current lookup arg has
    # values, across every section/annex.
    for unit in introspect.all_units(detail=True, with_values=True):
        for member in unit.members:
            if member.kind != "method":
                continue
            for arg in member.args:
                assert arg.available, f"{unit.tr_module} {unit.key} {member.name}({arg.name}): no available values"


# ---------------------------------------------------------------------------
# Drift guard: _QUERYABLE must stay in lockstep with the real methods.
# ---------------------------------------------------------------------------
def _accessor_classes():
    classes = [v[2] for v in tr38901._SECTION_REGISTRY.values()]
    classes += [v[2] for v in tr36777._ANNEX_REGISTRY.values()]
    # de-dupe while preserving identity
    seen, out = set(), []
    for c in classes:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


@pytest.mark.parametrize("accessor_cls", _accessor_classes(), ids=lambda c: c.__name__)
def test_queryable_matches_real_methods(accessor_cls):
    queryable = getattr(accessor_cls, "_QUERYABLE", {})
    method_names = {
        name for name in dir(accessor_cls)
        if not name.startswith("_") and inspect.isfunction(inspect.getattr_static(accessor_cls, name))
    }
    # Every lookup method is declared in _QUERYABLE, and no stale entries.
    assert set(queryable) == method_names, (
        f"{accessor_cls.__name__}: _QUERYABLE keys {set(queryable)} != methods {method_names}"
    )
    # Every keyword arg of every method is mapped to a field.
    for name in method_names:
        sig = inspect.signature(inspect.getattr_static(accessor_cls, name))
        args = [p for p in sig.parameters if p != "self"]
        _data_attr, arg_fields = queryable[name]
        assert set(args) == set(arg_fields), (
            f"{accessor_cls.__name__}.{name}: args {args} != _QUERYABLE arg map {set(arg_fields)}"
        )
