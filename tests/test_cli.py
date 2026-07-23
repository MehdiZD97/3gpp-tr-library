"""
Tests for the `tr-api` CLI (Phase 8). Invoked in-process via `cli.main(argv)`.

The load-bearing tests are the ones proving the CLI is a *thin layer*: `get`
returns exactly what a direct `tr_api` call returns, and `dump --format csv`
matches the committed CSV byte-for-byte. Plus: both TRs are reachable, machine
output is clean for piping, and bad input is a helpful message + non-zero exit,
not a traceback.

Requires tr_api installed (`pip install -e tools/tr_api`).
"""
import json
import os

import pytest
from tr_api import cli, introspect, tr36777, tr38901
from tr_api._loader import ScenarioNotFoundError

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(argv, capsys):
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- combinatorial enumeration for the parametrized coverage below ---
_UNITS = introspect.all_units()


def _valid_kwargs(accessor, member):
    data = getattr(accessor._data, member.data_attribute)
    if isinstance(data, dict):  # zsd_zod_offset: scenario is a dict key
        k = sorted(data)[0]
        entry = data[k].entries[0]
        return {a.name: (k if a.field == "@keys" else getattr(entry, a.field)) for a in member.args}
    entry = data[0]
    return {a.name: getattr(entry, a.field) for a in member.args}


def _member_cases():
    cases = []
    for unit in introspect.all_units(detail=True, with_values=True):
        for m in unit.members:
            cases.append(pytest.param(unit.tr_module, unit.key, m.name, id=f"{unit.tr_module}-{unit.key}-{m.name}"))
    return cases


_MEMBER_CASES = _member_cases()


# ---------------------------------------------------------------------------
# list / describe -- both TRs reachable
# ---------------------------------------------------------------------------
def test_list_shows_all_four_units_across_both_trs(capsys):
    code, out, _ = run(["list"], capsys)
    assert code == 0
    assert "TR 38.901" in out and "TR 36.777" in out
    for token in ("7.4", "7.5", "7.9", "Channel modelling details"):
        assert token in out


def test_list_filter_by_tr(capsys):
    code, out, _ = run(["list", "tr36777"], capsys)
    assert code == 0
    assert "TR 36.777" in out and "TR 38.901" not in out


def test_describe_prints_section_params_and_available_values(capsys):
    code, out, _ = run(["describe", "tr38901", "7.9"], capsys)
    assert code == 0
    assert "rcs_model_2(target, scattering_point)" in out
    assert "Vehicle with single scattering point" in out  # an available value


def test_describe_annex_is_first_class(capsys):
    code, out, _ = run(["describe", "tr36777", "B"], capsys)
    assert code == 0
    assert 'tr36777.annex("B")' in out
    assert "alternative_2(scenario, parameter, condition)" in out


# ---------------------------------------------------------------------------
# get -- thin-layer proof: CLI value == direct API value
# ---------------------------------------------------------------------------
def test_get_matches_direct_api_call(capsys):
    code, out, _ = run(
        ["get", "tr38901", "7.4", "pathloss", "--scenario", "InH-Office", "--condition", "LOS"], capsys
    )
    assert code == 0
    direct = tr38901.section("7.4").pathloss(scenario="InH-Office", condition="LOS")
    assert direct.formula in out
    assert f"formula: {direct.formula}" in out


def test_get_annex_lookup_matches_direct_api(capsys):
    code, out, _ = run(
        ["get", "tr36777", "B", "alternative_2", "--scenario", "RMa-AV", "--parameter", "K", "--condition", "LOS"],
        capsys,
    )
    assert code == 0
    direct = tr36777.annex("B").alternative_2(scenario="RMa-AV", parameter="K", condition="LOS")
    assert direct.mu in out


def test_get_list_result_prints_all_entries(capsys):
    code, out, _ = run(["get", "tr36777", "B", "pathloss", "--scenario", "RMa-AV", "--condition", "LOS"], capsys)
    assert code == 0
    assert "2 entries" in out
    assert "According to Table 7.4.1-1" in out and "PL_{RMa-AV-LOS}" in out


def test_get_property_returns_whole_set(capsys):
    code, out, _ = run(["get", "tr38901", "7.5", "notations"], capsys)
    assert code == 0
    assert "16 entries" in out


# ---------------------------------------------------------------------------
# dump -- clean machine output for piping
# ---------------------------------------------------------------------------
def test_dump_json_is_valid_and_matches_api(capsys):
    code, out, err = run(["dump", "tr38901", "7.9", "xpr", "--format", "json"], capsys)
    assert code == 0
    assert err == ""  # nothing on stderr -> clean for piping
    data = json.loads(out)  # valid JSON with no stray lines
    # Round-trips to the same records the public API returns per target.
    section = tr38901.section("7.9")
    expected = [section.xpr(target=t).model_dump() for t in ("UAV", "Human", "Vehicle", "AGV")]
    assert data == expected


def test_dump_csv_matches_committed_file(capsys):
    code, out, _ = run(["dump", "tr38901", "7.5", "channel_model_parameters", "--format", "csv"], capsys)
    assert code == 0
    committed = os.path.join(
        REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", "tables", "table-7.5-6.csv"
    )
    with open(committed, newline="") as f:
        assert out == f.read()


def test_dump_csv_on_non_table_errors_helpfully(capsys):
    code, out, err = run(["dump", "tr38901", "7.4", "o2i_penetration_loss", "--format", "csv"], capsys)
    assert code == 2
    assert out == ""  # nothing on stdout
    assert "json" in err.lower()


# ---------------------------------------------------------------------------
# errors -- helpful text + non-zero exit, no traceback
# ---------------------------------------------------------------------------
def test_unknown_scenario_prints_available_and_exits_nonzero(capsys):
    code, out, err = run(
        ["get", "tr38901", "7.4", "pathloss", "--scenario", "Mars", "--condition", "LOS"], capsys
    )
    assert code == 2
    assert out == ""
    assert "Available" in err and "Mars" in err


def test_unknown_member_lists_available_members(capsys):
    code, _out, err = run(["get", "tr38901", "7.9", "nonsense"], capsys)
    assert code == 2
    assert "rcs_model_2" in err  # lists real members


def test_unknown_section_exits_nonzero(capsys):
    code, _out, err = run(["describe", "tr38901", "7.6"], capsys)
    assert code == 2
    assert "7.6" in err


# ---------------------------------------------------------------------------
# Combinatorial coverage: describe / get / dump across EVERY unit and member.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("unit", _UNITS, ids=[f"{u.tr_module}-{u.key}" for u in _UNITS])
def test_describe_every_unit_exits_zero_and_mentions_title(unit, capsys):
    code, out, _ = run(["describe", unit.tr_module, unit.key], capsys)
    assert code == 0
    assert unit.title in out
    # every described member name appears in the output
    for member in introspect.describe(unit.tr_module, unit.key, with_values=False).members:
        assert member.name in out


@pytest.mark.parametrize("tr_module,key,member_name", _MEMBER_CASES)
def test_get_every_member_matches_direct_api(tr_module, key, member_name, capsys):
    accessor = introspect.load_accessor(tr_module, key)
    member = next(m for m in introspect.describe(tr_module, key).members if m.name == member_name)
    if member.kind == "method":
        # Drop optional args that are None on this row (e.g. pathloss variant) --
        # a real user omits them; passing "--variant None" would be a string.
        kwargs = {k: v for k, v in _valid_kwargs(accessor, member).items() if v is not None}
        argv = ["get", tr_module, key, member_name]
        for name, value in kwargs.items():
            argv += [f"--{name}", str(value)]
        expected = getattr(accessor, member_name)(**kwargs)
    else:
        argv = ["get", tr_module, key, member_name]
        expected = getattr(accessor, member_name)

    code, out, _ = run(argv, capsys)
    assert code == 0
    # Thin-layer proof: every field/value the direct API returns is in the CLI output.
    entries = expected if isinstance(expected, list) else [expected]
    for entry in entries:
        for field, value in entry.model_dump().items():
            assert f"{field}: {value}" in out, f"{member_name}: '{field}: {value}' missing from get output"


@pytest.mark.parametrize("tr_module,key,member_name", _MEMBER_CASES)
def test_dump_json_every_member_is_clean_and_roundtrips(tr_module, key, member_name, capsys):
    code, out, err = run(["dump", tr_module, key, member_name, "--format", "json"], capsys)
    assert code == 0
    assert err == ""  # stdout-only -> safe to pipe
    parsed = json.loads(out)  # valid JSON, no stray lines
    # round-trips to the same jsonable structure the API hands back
    accessor = introspect.load_accessor(tr_module, key)
    member = next(m for m in introspect.describe(tr_module, key, with_values=False).members if m.name == member_name)
    assert parsed == introspect.to_jsonable(introspect.member_data(accessor, member))


@pytest.mark.parametrize("tr_module,key,member_name", _MEMBER_CASES)
def test_dump_csv_every_flat_list_member_parses(tr_module, key, member_name, capsys):
    import csv
    import io

    accessor = introspect.load_accessor(tr_module, key)
    member = next(m for m in introspect.describe(tr_module, key, with_values=False).members if m.name == member_name)
    data = introspect.member_data(accessor, member)
    is_flat_list = introspect.to_table(data) is not None

    code, out, err = run(["dump", tr_module, key, member_name, "--format", "csv"], capsys)
    if is_flat_list:
        assert code == 0
        parsed = list(csv.reader(io.StringIO(out)))
        assert len(parsed) == len(data) + 1  # header + one row per entry
    else:
        assert code == 2  # non-tabular -> helpful error, not broken CSV
        assert out == "" and "json" in err.lower()


# ---------------------------------------------------------------------------
# Error matrix + help + stdout discipline
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("argv,needle", [
    (["describe", "trNOPE", "7.4"], "trNOPE"),
    (["describe", "tr38901", "9.9"], "9.9"),
    (["get", "tr36777", "Z", "pathloss"], "Z"),
    (["get", "tr38901", "7.9", "no_such_member"], "no_such_member"),
    (["get", "tr38901", "7.9", "xpr", "--target", "Spaceship"], "Available"),
    (["dump", "tr38901", "7.4", "o2i_penetration_loss", "--format", "csv"], "json"),  # nested -> csv unavailable
])
def test_bad_input_helpful_and_nonzero_with_clean_stdout(argv, needle, capsys):
    code, out, err = run(argv, capsys)
    assert code != 0
    assert out == ""             # never a partial/broken payload on stdout
    assert needle in err         # helpful pointer on stderr


@pytest.mark.parametrize("argv", [["--help"], ["list", "--help"], ["describe", "--help"],
                                  ["get", "--help"], ["dump", "--help"]])
def test_help_exits_zero_and_mentions_subcommands(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "usage" in out.lower()
