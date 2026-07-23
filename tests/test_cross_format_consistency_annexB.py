"""
Cross-file consistency for TR 36.777 Annex B. CSV<->YAML agreement for every
table is covered generically by tools/verify_tables.py's verify_annex_b()
(exercised end-to-end via test_verify_tables.py). This file covers the
inline Markdown tables in the section .md, which -- unlike §7.5-6 -- are in
the *same* orientation as the CSVs, so a straightforward row-presence check
guards against the human-readable and machine-readable copies drifting apart.
"""


def _md_rows_containing(body, needle):
    return [line for line in body.splitlines() if line.startswith("|") and needle in line]


def test_inline_alt2_formulas_present_in_markdown(annex_b_raw_text, annex_b_yaml_data):
    # Every Alternative 2 mu/sigma formula in the YAML must appear verbatim in
    # the section .md's inline tables (catches a hand-edit to one but not the
    # other).
    for entry in annex_b_yaml_data["alternative_2_modified_parameters"]:
        assert entry["mu"] in annex_b_raw_text, f"mu missing from .md: {entry['mu']}"
        assert entry["sigma"] in annex_b_raw_text, f"sigma missing from .md: {entry['sigma']}"


def test_inline_alt1_values_present_in_markdown(annex_b_raw_text, annex_b_yaml_data):
    for entry in annex_b_yaml_data["alternative_1_desired_parameters"]:
        row = _md_rows_containing(annex_b_raw_text, f"{entry['scenario']} {entry['condition']} |")
        # At least one inline row for this scenario/condition must carry its
        # desired-K and desired-DS values.
        assert any(f"{entry['desired_k_db']} dB" in r and f"{entry['desired_ds_ns']} ns" in r for r in row), (
            f"{entry['scenario']} {entry['condition']}: desired K/DS not found together in an inline row"
        )


def test_inline_pathloss_formulas_present_in_markdown(annex_b_raw_text, annex_b_yaml_data):
    for entry in annex_b_yaml_data["pathloss"]:
        assert entry["pathloss"] in annex_b_raw_text, f"pathloss cell missing from .md: {entry['pathloss'][:50]}"
