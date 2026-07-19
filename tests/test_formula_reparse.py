"""
Genuine automated drift detection for formula *content* (test_source_reparse.py
covers structure). Promoted from the ad hoc cross-check first done in
_scratch/extract_full.py during Phase 2: tag-strip the HTML export's OMML
equation markup and confirm every numeric constant in the committed pathloss
formulas is still present.

Scoped to Table 7.4.1-1 (`pathloss`) only -- confirmed by direct inspection
that its formulas are uniformly genuine OMML text in the HTML (0 OLEObject /
324 m:oMath in that region), unlike Table 7.4.2-1 (`los_probability`), which
mixes text-recoverable and image-embedded (OLEObject/.wmz) equations. See
`tools/verify_tables.py`'s comment on this for the full reasoning, and
CLAUDE.md / the Phase 3 completion report for the finding that three
los_probability entries currently have single-source (PDF visual) coverage
only.

Skips cleanly if the (gitignored, not-committed) reference source isn't
present, since references/ is never available in a fresh clone or CI.
"""
import os
import sys

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_HTML = os.path.join(REPO_ROOT, "references", "3gpp-tr38901", "v19.4.0", "38901-j40.html")

pytestmark = pytest.mark.skipif(
    not os.path.isfile(SOURCE_HTML),
    reason="references/ source document not present (gitignored, local-only)",
)

sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))


def test_pathloss_formulas_confirmed_in_html_export(section_7_4_yaml_path):
    from verify_tables import check_formulas_against_html

    with open(section_7_4_yaml_path) as f:
        data = yaml.safe_load(f)

    formulas = [row["formula"] for row in data["pathloss"]]
    mismatches = check_formulas_against_html(
        SOURCE_HTML,
        start_text="Pathloss, LOS probability and penetration modelling",
        end_text="Fast fading model",
        formulas=formulas,
    )
    assert not mismatches, "\n".join(
        f"{formula!r}: missing numbers {missing}" for formula, missing in mismatches
    )
