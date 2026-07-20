"""
tr_api: typed Python access to this repo's structured 3GPP TR data.

    from tr_api import tr38901, tr36777

    # TR 38.901 -- numbered clauses, accessed via section():
    entry = tr38901.section("7.4").pathloss(scenario="UMi-StreetCanyon", condition="NLOS")
    entry.shadow_fading_std_db

    # TR 36.777 -- a lettered annex, accessed via annex():
    b = tr36777.annex("B")
    b.pathloss(scenario="RMa-AV", condition="LOS")   # aerial-UE pathloss deltas

Organized by TR (`tr38901`, `tr36777`) and by version (passed to
`section()` / `annex()`, defaulting to each TR's latest processed version).
The TR-agnostic load/validate/cache machinery lives in `_loader.py` and is
shared by every per-TR module, so adding a further TR is a new thin module
plus its registry, not a copy of the loader.
"""
from . import tr36777, tr38901

__all__ = ["tr38901", "tr36777"]
