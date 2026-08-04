"""
Cross-file consistency for TR 38.901 §7.6 (Additional modelling components).

CSV<->YAML agreement for all eleven tables is covered generically by
tools/verify_tables.py's verify_section_7_6() (exercised end-to-end via
test_verify_tables.py). This file closes the triangle by guarding the *inline
Markdown* tables in the section .md against drifting from the CSV/YAML.

Unlike §7.5 -- whose 51-column master table had to be transposed to stay
readable -- every §7.6 table is small enough to keep the same entity-row
orientation in all three formats, so each row reconstructs to an exact inline
row substring. The one representational difference is Table 7.6.3.1-2's empty
`condition` cell (Indoor/InF have no LOS/NLOS/O2I split), rendered as an em
dash in the .md.
"""
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES_DIR = os.path.join(REPO_ROOT, "TR-38.901", "v19.4.0", "07-channel-models", "tables")

# Every in-scope table, in TR order: (table number, YAML key).
TABLE_KEYS = [
    ("7.6.1-1", "oxygen_absorption_loss"),
    ("7.6.3.1-2", "spatial_consistency_correlation_distance"),
    ("7.6.3.4-1", "spatial_consistency_correlation_type"),
    ("7.6.3.4-2", "spatial_consistency_uncorrelated_states"),
    ("7.6.4.1-1", "self_blocking_region"),
    ("7.6.4.1-2", "blocking_region"),
    ("7.6.4.1-3", "blockage_sign_description"),
    ("7.6.4.1-4", "blockage_correlation_distance"),
    ("7.6.4.2-5", "blocker_parameters"),
    ("7.6.8-1", "ground_material_properties"),
    ("7.6.9-1", "absolute_time_of_arrival"),
]

EMPTY_CELL_IN_MD = "—"  # the .md renders an absent condition as an em dash


def _md_row(cells):
    return "| " + " | ".join(c if c else EMPTY_CELL_IN_MD for c in cells) + " |"


# ---------------------------------------------------------------------------
# CSV -> inline Markdown (same orientation, exact rows)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("table_number", [t for t, _ in TABLE_KEYS])
def test_every_csv_row_appears_verbatim_in_markdown(table_number, section_7_6_raw_text):
    from section_utils import read_csv_rows
    header, *rows = read_csv_rows(os.path.join(TABLES_DIR, f"table-{table_number}.csv"))
    assert rows, f"table-{table_number}.csv has no data rows"
    for row in rows:
        assert _md_row(row) in section_7_6_raw_text, (
            f"table-{table_number}.csv row not found verbatim in the inline .md table: {_md_row(row)}"
        )


@pytest.mark.parametrize("table_number", [t for t, _ in TABLE_KEYS])
def test_markdown_declares_each_table_with_its_real_tr_number(table_number, section_7_6_raw_text):
    assert f"Table {table_number}:" in section_7_6_raw_text, f"no heading for Table {table_number}"


# ---------------------------------------------------------------------------
# YAML -> inline Markdown (independently of the CSV, so a coordinated
# CSV+MD drift away from the YAML still fails)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("table_number,yaml_key", TABLE_KEYS)
def test_every_yaml_entry_appears_as_an_inline_markdown_row(table_number, yaml_key,
                                                            section_7_6_yaml_data, section_7_6_raw_text):
    from section_utils import read_csv_rows
    header = read_csv_rows(os.path.join(TABLES_DIR, f"table-{table_number}.csv"))[0]
    entries = section_7_6_yaml_data[yaml_key]
    assert entries, f"{yaml_key} is empty"
    for entry in entries:
        row = _md_row([entry[col] if entry[col] is not None else "" for col in header])
        assert row in section_7_6_raw_text, f"{yaml_key} entry missing from the .md: {row}"


@pytest.mark.parametrize("table_number,yaml_key", TABLE_KEYS)
def test_row_counts_agree_across_csv_yaml_and_markdown(table_number, yaml_key,
                                                       section_7_6_yaml_data, section_7_6_raw_text):
    from section_utils import read_csv_rows
    header, *csv_rows = read_csv_rows(os.path.join(TABLES_DIR, f"table-{table_number}.csv"))
    assert len(csv_rows) == len(section_7_6_yaml_data[yaml_key]), (
        f"table-{table_number}: {len(csv_rows)} CSV rows vs {len(section_7_6_yaml_data[yaml_key])} YAML entries"
    )
    md_rows = sum(1 for r in csv_rows if _md_row(r) in section_7_6_raw_text)
    assert md_rows == len(csv_rows), f"table-{table_number}: only {md_rows}/{len(csv_rows)} rows found in the .md"


# ---------------------------------------------------------------------------
# Equations live only in the .md (per convention) -- confirm every in-scope
# numbered equation is present and its $$ block isn't blank.
# ---------------------------------------------------------------------------
EXPECTED_EQUATIONS = (
    ["7.6-1", "7.6-2"]                                                  # 7.6.1
    + ["7.6-9", "7.6-10", "7.6-10aa", "7.6-10a", "7.6-10b", "7.6-10c"]  # 7.6.3.2 Procedure A
    + [f"7.6-{n}" for n in range(11, 18)]                                # 7.6-11 .. 7.6-17
    + ["7.6-17a", "7.6-17b", "7.6-17c", "7.6-17d", "7.6-17e", "7.6-17f"]
    + ["7.6-18", "7.6-19"]                                              # 7.6.3.3
    + [f"7.6-{n}" for n in range(20, 31)]                                # 7.6.4 (7.6-20 .. 7.6-30)
    + [f"7.6-{n}" for n in range(32, 38)]                                # 7.6.8 (7.6-32 .. 7.6-37)
    + ["7.6-37a", "7.6-37b", "7.6-37c", "7.6-37d"]
    + [f"7.6-{n}" for n in range(38, 43)]                                # 7.6-38 .. 7.6-42
    + ["7.6-43", "7.6-44", "7.6-44a"]                                   # 7.6.9
    + ["7.6-45", "7.6-46"]                                              # 7.6.10
)


def test_expected_equation_count():
    # 54 numbered equations across the in-scope sub-clauses (7.6.2/7.6.5-7.6.7
    # and 7.6.11-7.6.16 are not processed, so 7.6-3..7.6-8 and 7.6-31 are absent).
    assert len(EXPECTED_EQUATIONS) == len(set(EXPECTED_EQUATIONS)) == 54


@pytest.mark.parametrize("eq", EXPECTED_EQUATIONS)
def test_equation_present_with_non_empty_display_block(eq, section_7_6_raw_text):
    marker = f"<!-- Eq. {eq} -->"
    assert marker in section_7_6_raw_text, f"missing equation comment {eq}"
    after = section_7_6_raw_text.split(marker, 1)[1].lstrip()
    assert after.startswith("$$"), f"{eq}: comment not followed by a $$ block"
    body = after[2:].split("$$", 1)[0].strip()
    assert len(body) > 5, f"{eq}: display block looks empty ({body!r})"


def test_out_of_scope_equations_are_not_claimed(section_7_6_raw_text):
    # 7.6-3..7.6-8 (7.6.2) and 7.6-31 (7.6.6) belong to unprocessed sub-clauses
    # and must not appear as equation comments here.
    for n in list(range(3, 9)) + [31]:
        assert f"<!-- Eq. 7.6-{n} -->" not in section_7_6_raw_text, f"7.6-{n} is out of scope"


def test_distinctive_equation_fragments_present(section_7_6_raw_text):
    # Guards against a blanked/garbled $$ block at a few load-bearing points.
    assert r"\frac{\alpha(f_c)}{1000}" in section_7_6_raw_text            # Eq. 7.6-1
    assert r"-20\log_{10}" in section_7_6_raw_text                        # Eq. 7.6-22 / 7.6-29
    assert r"\varepsilon_r - j\," in section_7_6_raw_text                 # Eq. 7.6-40
    assert r"a_\varepsilon\cdot" in section_7_6_raw_text                  # Eq. 7.6-41
    assert r"c_\sigma\cdot" in section_7_6_raw_text                       # Eq. 7.6-42
    assert r"2\alpha_{n,m}D_{n,m}" in section_7_6_raw_text                # Eq. 7.6-46


# ---------------------------------------------------------------------------
# Scope boundary: the .md must be explicit about what it does and doesn't cover
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("subclause", ["7.6.0", "7.6.1", "7.6.3", "7.6.4", "7.6.8", "7.6.9", "7.6.10"])
def test_in_scope_subclauses_have_a_heading(subclause, section_7_6_raw_text):
    assert f"## {subclause} " in section_7_6_raw_text, f"no heading for in-scope {subclause}"


@pytest.mark.parametrize("subclause", ["7.6.2", "7.6.5", "7.6.6", "7.6.7", "7.6.11",
                                       "7.6.12", "7.6.13", "7.6.14", "7.6.15", "7.6.16"])
def test_out_of_scope_subclauses_are_listed_but_not_transcribed(subclause, section_7_6_raw_text):
    # Named in the scope table (so a reader knows what's missing) but given no
    # content heading of their own.
    assert subclause in section_7_6_raw_text, f"{subclause} not acknowledged in the scope table"
    assert f"## {subclause} " not in section_7_6_raw_text, f"{subclause} has a content heading but is out of scope"
