"""
tr_api: typed Python access to this repo's structured 3GPP TR data.

    from tr_api import tr38901

    entry = tr38901.section("7.4").pathloss(scenario="UMi-StreetCanyon", condition="NLOS")
    entry.shadow_fading_std_db

Organized by TR (`tr38901`, with `tr36777` a natural future sibling) and by
version (passed to `section()`, defaulting to the latest processed version)
so the package still makes sense once a second TR or a second version of
TR 38.901 exists.
"""
from . import tr38901

__all__ = ["tr38901"]
