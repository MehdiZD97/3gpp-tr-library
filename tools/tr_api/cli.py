"""
`tr-api` -- discover and query this repo's structured 3GPP TR data from a
terminal.

This is a **thin presentation layer over `tr_api.introspect`**: it holds no
section/parameter knowledge of its own. `list`/`describe` render what the
introspection API reports; `get` calls the real accessors; `dump` serializes
what the API hands back. If something needs section knowledge, it belongs in
the introspection layer, not here.

Subcommands:
  list [tr]                     list TRs and their processed sections/annexes
  describe <tr> <key>           show a section/annex's callable parameters + values
  get <tr> <key> <member> ...   perform a lookup and print the result readably
  dump <tr> <key> <member>      dump a whole parameter set as JSON/CSV (for piping)

Machine output (`dump`) goes to stdout only; all human chatter goes to stderr,
so `dump ... --format json | jq` and `dump ... --format csv > out.csv` are clean.
"""
import argparse
import csv
import json
import sys

from . import introspect
from ._loader import ScenarioNotFoundError, SectionNotFoundError


def _eprint(*args):
    print(*args, file=sys.stderr)


def _fmt_available(values, limit=8):
    if values is None:
        return "(depends on data)"
    if len(values) > limit:
        return " | ".join(values[:limit]) + f" | … ({len(values)} total)"
    return " | ".join(values)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------
def cmd_list(args, extras):
    if extras:
        _eprint(f"error: unexpected arguments: {' '.join(extras)}")
        return 2
    units = introspect.all_units()
    trs = introspect.registered_trs()
    wanted = args.tr
    if wanted and wanted not in trs:
        _eprint(f"error: no TR module {wanted!r}. Available: {sorted(trs)}")
        return 2
    shown = [u for u in units if not wanted or u.tr_module == wanted]
    by_tr = {}
    for u in shown:
        by_tr.setdefault(u.tr_module, []).append(u)
    for tr_module, tr_units in by_tr.items():
        first = tr_units[0]
        print(f"{first.tr_label} ({tr_module}) — access via {first.verb}(\"<id>\")")
        width = max(len(u.key) for u in tr_units)
        for u in tr_units:
            print(f"  {u.key:<{width}}  {u.title}")
        print()
    print("Run 'tr-api describe <tr> <id>' to see a section's callable parameters.")
    return 0


# ---------------------------------------------------------------------------
# describe
# ---------------------------------------------------------------------------
def cmd_describe(args, extras):
    if extras:
        _eprint(f"error: unexpected arguments: {' '.join(extras)}")
        return 2
    try:
        unit = introspect.describe(args.tr, args.key, with_values=True)
    except (SectionNotFoundError, ScenarioNotFoundError) as exc:
        _eprint(f"error: {exc}")
        return 2

    print(f"{unit.tr_label} {unit.clause} — {unit.title}  ({unit.version})")
    print(f"Access: {unit.tr_module}.{unit.verb}(\"{unit.key}\")")

    methods = [m for m in unit.members if m.kind == "method"]
    props = [m for m in unit.members if m.kind == "property"]

    if methods:
        print("\nMethods (query with 'get ... --<arg> <value>'):")
        for m in methods:
            arglist = ", ".join(a.name for a in m.args)
            print(f"  {m.name}({arglist}) -> {m.returns}")
            for a in m.args:
                print(f"      {a.name}: {_fmt_available(a.available)}")
    if props:
        print("\nProperties (direct access, whole set — no args):")
        for m in props:
            print(f"  {m.name} -> {m.returns}")

    example = methods[0] if methods else (props[0] if props else None)
    if example is not None:
        if example.kind == "method" and example.args:
            call = " ".join(
                f'--{a.name} "{a.available[0]}"' if a.available else f"--{a.name} <value>"
                for a in example.args
            )
            print(f"\nExample:\n  tr-api get {unit.tr_module} {unit.key} {example.name} {call}")
        else:
            print(f"\nExample:\n  tr-api dump {unit.tr_module} {unit.key} {example.name} --format csv")
    return 0


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------
def _parse_kwargs(extras):
    kwargs = {}
    i = 0
    while i < len(extras):
        tok = extras[i]
        if not tok.startswith("--"):
            raise ValueError(f"unexpected argument {tok!r} (expected --<name> <value>)")
        if "=" in tok:
            key, val = tok[2:].split("=", 1)
            kwargs[key] = val
            i += 1
        else:
            if i + 1 >= len(extras):
                raise ValueError(f"missing value for {tok}")
            kwargs[tok[2:]] = extras[i + 1]
            i += 2
    return kwargs


def _find_member(unit, member_name):
    for m in unit.members:
        if m.name == member_name:
            return m
    return None


def _print_model(model, indent="  "):
    for key, value in model.model_dump().items():
        print(f"{indent}{key}: {value}")


def cmd_get(args, extras):
    try:
        accessor = introspect.load_accessor(args.tr, args.key)
    except (SectionNotFoundError, ScenarioNotFoundError) as exc:
        _eprint(f"error: {exc}")
        return 2
    unit = introspect.describe(args.tr, args.key, with_values=True)
    member = _find_member(unit, args.member)
    if member is None:
        names = ", ".join(m.name for m in unit.members)
        _eprint(f"error: no parameter {args.member!r} on {args.tr} {args.key}. Available: {names}")
        return 2

    if member.kind == "property":
        if extras:
            _eprint(f"error: {member.name} is a property (no arguments); got {' '.join(extras)}")
            return 2
        result = getattr(accessor, member.name)
    else:
        try:
            kwargs = _parse_kwargs(extras)
        except ValueError as exc:
            _eprint(f"error: {exc}")
            return 2
        method = getattr(accessor, member.name)
        try:
            result = method(**kwargs)
        except (ScenarioNotFoundError, SectionNotFoundError) as exc:
            _eprint(f"error: {exc}")
            return 2
        except TypeError:
            need = ", ".join(f"--{a.name}" for a in member.args)
            _eprint(f"error: {member.name} takes: {need}")
            for a in member.args:
                _eprint(f"    {a.name}: {_fmt_available(a.available)}")
            return 2

    if isinstance(result, list):
        print(f"{len(result)} entr{'y' if len(result) == 1 else 'ies'}:")
        for i, entry in enumerate(result):
            print(f"\n[{i}]")
            _print_model(entry)
    else:
        _print_model(result)
    return 0


# ---------------------------------------------------------------------------
# dump
# ---------------------------------------------------------------------------
def cmd_dump(args, extras):
    if extras:
        _eprint(f"error: unexpected arguments: {' '.join(extras)}")
        return 2
    try:
        accessor = introspect.load_accessor(args.tr, args.key)
    except (SectionNotFoundError, ScenarioNotFoundError) as exc:
        _eprint(f"error: {exc}")
        return 2
    unit = introspect.describe(args.tr, args.key, with_values=False)
    member = _find_member(unit, args.member)
    if member is None:
        names = ", ".join(m.name for m in unit.members)
        _eprint(f"error: no parameter {args.member!r} on {args.tr} {args.key}. Available: {names}")
        return 2

    data_value = introspect.member_data(accessor, member)

    if args.format == "json":
        json.dump(introspect.to_jsonable(data_value), sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return 0

    # CSV: only the flat-list shape is a table (matches the committed tables/*.csv).
    table = introspect.to_table(data_value)
    if table is None:
        _eprint(f"error: {member.name} isn't a flat table; CSV is unavailable. "
                f"Use --format json (its return type is {member.returns or 'a nested structure'}).")
        return 2
    header, rows = table
    writer = csv.writer(sys.stdout)
    writer.writerow(header)
    writer.writerows(rows)
    return 0


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="tr-api",
        description="Discover and query 3gpp-tr-library's structured 3GPP TR data. "
                    "Start with 'tr-api list', then 'tr-api describe <tr> <id>'.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="{list,describe,get,dump}")

    p_list = sub.add_parser("list", help="list TRs and their processed sections/annexes")
    p_list.add_argument("tr", nargs="?", help="optional TR module to filter (tr38901 | tr36777)")

    p_desc = sub.add_parser("describe", help="show a section/annex's callable parameters and available values")
    p_desc.add_argument("tr", help="TR module, e.g. tr38901")
    p_desc.add_argument("key", help="section/annex id, e.g. 7.9 or B")

    p_get = sub.add_parser(
        "get", help="perform a lookup and print the result",
        description="Perform a lookup, e.g.: tr-api get tr38901 7.4 pathloss --scenario UMi-StreetCanyon --condition NLOS",
    )
    p_get.add_argument("tr")
    p_get.add_argument("key")
    p_get.add_argument("member", help="the parameter name (see 'describe')")

    p_dump = sub.add_parser(
        "dump", help="dump a whole parameter set as JSON or CSV (for piping)",
        description="e.g.: tr-api dump tr38901 7.5 channel_model_parameters --format json | jq",
    )
    p_dump.add_argument("tr")
    p_dump.add_argument("key")
    p_dump.add_argument("member")
    p_dump.add_argument("--format", choices=["json", "csv"], default="json", help="output format (default: json)")

    return parser


_HANDLERS = {"list": cmd_list, "describe": cmd_describe, "get": cmd_get, "dump": cmd_dump}


def main(argv=None):
    parser = build_parser()
    args, extras = parser.parse_known_args(argv)
    return _HANDLERS[args.command](args, extras)


if __name__ == "__main__":
    sys.exit(main())
