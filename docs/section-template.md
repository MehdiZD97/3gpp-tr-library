<!-- This is a template to copy when starting a new section file, not a real section. -->
---
tr: TR XX.XXX             # e.g. "TR 38.901" — the TR number as printed on the cover page
version: vX.X.X            # e.g. "v19.4.0" — three-part 3GPP version, matches the source folder under references/
section: "X.X"             # the TR's own section or annex number, kept as a string (e.g. "7.4", "Annex B")
title: Section Title       # short human-readable title, matches (or closely follows) the TR's heading
parent: 0X-chapter-name     # the zero-padded chapter directory this file lives under
summary: One-sentence summary of what this section covers.
depends_on: []              # other section files (by filename stem) this one assumes context from, e.g. ["7.2-coordinate-system"]
source_pdf: https://www.3gpp.org/ftp/Specs/archive/XX_series/XX.XXX/   # exact link to the source document on 3gpp.org
status: planned              # planned | in-progress | verified
verified_against: []         # which references/ formats this section was cross-checked against, e.g. ["pdf", "xml"]
# verification_notes:        # OPTIONAL. Per-entry/per-table granularity where a
#   - applies_to: ...        #   few items are verified at a narrower level than the
#     verified_against: []   #   section-level `verified_against` implies (e.g. a formula
#     note: ...              #   that is OMML-dropped and so PDF-visual single-source).
#                            #   Each item: applies_to (str), verified_against (list of
#                            #   formats — the ACTUAL formats for this item), note (str).
#                            #   Omit the field entirely when the section is uniform.
---

# X.X Section Title

Placeholder prose paragraph summarizing what this section covers, written in plain language rather than copied verbatim from the source.

## Table X.X-1: Placeholder table title

| Parameter | Value | Notes |
|---|---|---|
| — | — | — |

A matching CSV lives at `tables/table-X.X-1.csv`; the CSV is the source of truth for programmatic access, this inline table is for human readability.

## Equations

<!-- Eq. X.X-1 -->
$$y = f(x)$$

## Figures

See Figure X.X-1 in the source TR — figures are referenced, not extracted, unless a downstream use requires the image.
