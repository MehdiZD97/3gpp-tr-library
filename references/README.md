# references/

Local source documents used to produce the structured content in this repository. This folder is gitignored — except for the README.md in each document folder below — and is not part of the public repo.

## Contents

### [`3gpp-tr38901/v19.4.0/`](3gpp-tr38901/v19.4.0/README.md)

TR 38.901, *Study on channel model for frequencies from 0.5 to 100 GHz*, Release 19. The core document for this library — the primary source for the channel-modelling sections (§7.4 pathloss, §7.5 fast fading processed; §7.6 spatial consistency planned).

### [`3gpp-tr36777/v15.0.0/`](3gpp-tr36777/v15.0.0/README.md)

TR 36.777, *Study on Enhanced LTE Support for Aerial Vehicles*, Release 15. Processed specifically for Annex B (channel modelling details) — the aerial-UE (drone) channel model.

### [`3gpp-R1-2509126/`](3gpp-R1-2509126/README.md)

A 3GPP RAN1 #123 meeting contribution, *Revised ISAC channel model calibration results* — not a formal Technical Report, but a single snapshot document with large-scale and full-scale ISAC calibration results from 25+ participating companies. Kept as reference material only, not run through the structured TR pipeline.

## Why this folder isn't tracked

These are large, third-party source documents owned by 3GPP. This repository redistributes structured *extracts* — hand-verified Markdown, CSV, and YAML — not the original files. Each document folder linked above has its own README.md with release details and a link to the canonical source on [3gpp.org](https://www.3gpp.org/).
