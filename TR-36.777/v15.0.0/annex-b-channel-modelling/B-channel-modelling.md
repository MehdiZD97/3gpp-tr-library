---
tr: TR 36.777
version: v15.0.0
section: "Annex B"
title: Channel modelling details
parent: annex-b-channel-modelling
summary: Aerial-UE (drone) channel model for RMa-AV/UMa-AV/UMi-AV — LOS probability, pathloss, shadow fading, and three fast-fading alternatives, expressed as height-dependent modifications to TR 38.901's terrestrial models.
depends_on: ["TR-38.901:7.4-pathloss", "TR-38.901:7.5-fast-fading"]
source_pdf: https://www.3gpp.org/dynareport/36777.htm
status: verified
verified_against: ["pdf", "html"]
---

# Annex B: Channel modelling details

This annex defines the channel model for **aerial UEs** (airborne/drone UEs) in the *Study on Enhanced LTE Support for Aerial Vehicles*, for three deployment scenarios — **RMa-AV**, **UMa-AV**, and **UMi-AV** (the "-AV" aerial-vehicle variants of TR 38.901's RMa/UMa/UMi). Rather than defining a standalone model, the annex expresses the aerial-UE channel largely as **height-dependent modifications and extensions to TR 38.901's terrestrial models**: for aerial UEs at low heights the ordinary TR 38.901 formulas apply, and above a scenario-specific height threshold (10 m for RMa-AV, 22.5 m for UMa-AV/UMi-AV) the aerial-specific formulas in the tables below take over.

> **On the reference "[4]".** Throughout this annex, "[4]" is **TR 38.901 V14.0.0** (2017) — an earlier version than the **v19.4.0** processed elsewhere in this repository. Baseline references such as *Table 7.4.1-1 of [4]*, *Table 7.4.2-1 of [4]*, and *Section 7.5 of [4]* map cleanly onto this repo's processed [§7.4](../../../TR-38.901/v19.4.0/07-channel-models/7.4-pathloss.md) and [§7.5](../../../TR-38.901/v19.4.0/07-channel-models/7.5-fast-fading.md) (those clause/table numbers are stable across the two TR 38.901 versions). References to *Section 7.7.x of [4]* (in Alternative 1's procedure) reflect v14.0.0's numbering for the detailed channel-coefficient-generation steps; that content lives under §7.5 in v19.4.0. All references below are reproduced **exactly as the annex states them**, not renumbered.

The distance definitions ($d_{2D}$, $d_{3D}$, with UT height $h_{UT}$ that may be larger, equal to, or smaller than the BS height $h_{BS}$) follow Figure B-1 in the source TR.

## Table B-1: LOS probability

LOS probability for aerial UEs, as a delta to TR 38.901's Table 7.4.2-1. Below the height threshold, the terrestrial LOS-probability formula of the corresponding scenario applies; in a middle band an aerial-specific formula with height-dependent parameters $p_1$, $d_1$ applies; above an upper threshold LOS is guaranteed (100%).

_A matching CSV lives at `tables/table-B-1.csv`; the machine-readable YAML entry is under `los_probability` in `B-channel-modelling.yaml`._

| Scenario | LOS probability (distance in meters) | Applicability (aerial UE height) | Notes |
|---|---|---|---|
| RMa-AV | According to Table 7.4.2-1 of [4] using the $Pr_{LOS}$ formula of RMa | 1.5m <= hUT <= 10m | — |
| RMa-AV | $Pr_{LOS} = \begin{cases} 1 & d_{2D} \le d_1 \\ \dfrac{d_1}{d_{2D}} + \exp\left(\dfrac{-d_{2D}}{p_1}\right)\left(1 - \dfrac{d_1}{d_{2D}}\right) & d_{2D} > d_1 \end{cases}; \quad p_1 = \max(15021\log_{10}(h_{UT}) - 16053, 1000); \quad d_1 = \max(1350.8\log_{10}(h_{UT}) - 1602, 18)$ | 10m < hUT <= 40m | Note 1; Note 2 |
| RMa-AV | 100% | 40m < hUT <= 300m | — |
| UMa-AV | According to Table 7.4.2-1 of [4] using the $Pr_{LOS}$ formula of UMa | 1.5m <= hUT <= 22.5m | — |
| UMa-AV | $Pr_{LOS} = \begin{cases} 1 & d_{2D} \le d_1 \\ \dfrac{d_1}{d_{2D}} + \exp\left(\dfrac{-d_{2D}}{p_1}\right)\left(1 - \dfrac{d_1}{d_{2D}}\right) & d_{2D} > d_1 \end{cases}; \quad p_1 = 4300\log_{10}(h_{UT}) - 3800; \quad d_1 = \max(460\log_{10}(h_{UT}) - 700, 18)$ | 22.5m < hUT <= 100m | Note 1; Note 2 |
| UMa-AV | 100% | 100m < hUT <= 300m | — |
| UMi-AV | According to Table 7.4.2-1 of [4] using the $Pr_{LOS}$ formula of UMi | 1.5m <= hUT <= 22.5m | — |
| UMi-AV | $Pr_{LOS} = \begin{cases} 1 & d_{2D} \le d_1 \\ \dfrac{d_1}{d_{2D}} + \exp\left(\dfrac{-d_{2D}}{p_1}\right)\left(1 - \dfrac{d_1}{d_{2D}}\right) & d_{2D} > d_1 \end{cases}; \quad p_1 = 233.98\log_{10}(h_{UT}) - 0.95; \quad d_1 = \max(294.05\log_{10}(h_{UT}) - 432.94, 18)$ | 22.5m < hUT <= 300m | Note 1; Note 2 |

- **Note 1:** The LOS probability is derived assuming antenna heights of 35 m for RMa-AV, 25 m for UMa-AV, and 10 m for UMi-AV.
- **Note 2:** $d_1$ is given in units of meters.

## Table B-2: Pathloss models

Aerial-UE pathloss, as a delta to TR 38.901's Table 7.4.1-1. Below the height threshold the terrestrial pathloss formula applies; above it, the aerial-specific formulas below apply.

_A matching CSV lives at `tables/table-B-2.csv`; YAML key `pathloss`._

| Scenario | Condition | Pathloss [dB] ($f_c$ in GHz, distance in meters) | Applicability | Notes |
|---|---|---|---|---|
| RMa-AV | LOS | According to Table 7.4.1-1 of [4] using the $PL_{RMa-LOS}$ formula | 1.5m <= hUT <= 10m | — |
| RMa-AV | LOS | $PL_{RMa-AV-LOS} = \max(23.9 - 1.8\log_{10}(h_{UT}), 20)\log_{10}(d_{3D}) + 20\log_{10}\left(\dfrac{40\pi f_c}{3}\right)$ | 10m < hUT <= 300m, d2D <= 10km | — |
| RMa-AV | NLOS | According to Table 7.4.1-1 of [4] using the $PL_{RMa-NLOS}$ formula | 1.5m <= hUT <= 10m | — |
| RMa-AV | NLOS | $PL_{RMa-AV-NLOS} = \max\left(PL_{RMa-AV-LOS},\; -12 + (35 - 5.3\log_{10}(h_{UT}))\log_{10}(d_{3D}) + 20\log_{10}\left(\dfrac{40\pi f_c}{3}\right)\right)$ | 10m < hUT <= 300m, d2D <= 10km | Note 2 |
| UMa-AV | LOS | According to Table 7.4.1-1 of [4] using the $PL_{UMa-LOS}$ formula | 1.5m <= hUT <= 22.5m | — |
| UMa-AV | LOS | $PL_{UMa-AV-LOS} = 28.0 + 22\log_{10}(d_{3D}) + 20\log_{10}(f_c)$ | 22.5m < hUT <= 300m, d2D <= 4km | Note 1 |
| UMa-AV | NLOS | According to Table 7.4.1-1 of [4] using the $PL_{UMa-NLOS}$ formula | 1.5m <= hUT <= 22.5m | — |
| UMa-AV | NLOS | $PL_{UMa-AV-NLOS} = -17.5 + (46 - 7\log_{10}(h_{UT}))\log_{10}(d_{3D}) + 20\log_{10}\left(\dfrac{40\pi f_c}{3}\right)$ | 10m < hUT <= 100m, d2D <= 4km | — |
| UMi-AV | LOS | According to Table 7.4.1-1 of [4] using the $PL_{UMi-LOS}$ formula | 1.5m <= hUT <= 22.5m | — |
| UMi-AV | LOS | $PL_{UMi-AV-LOS} = \max\{PL',\; 30.9 + (22.25 - 0.5\log_{10}(h_{UT}))\log_{10}(d_{3D}) + 20\log_{10}(f_c)\}$ | 22.5m < hUT <= 300m, d2D <= 4km | Note 3 |
| UMi-AV | NLOS | According to Table 7.4.1-1 of [4] using the $PL_{UMi-NLOS}$ formula | 1.5m <= hUT <= 22.5m | — |
| UMi-AV | NLOS | $PL_{UMi-AV-NLOS} = \max\{PL_{UMi-AV-LOS},\; 32.4 + (43.2 - 7.6\log_{10}(h_{UT}))\log_{10}(d_{3D}) + 20\log_{10}(f_c)\}$ | 22.5m < hUT <= 300m, d2D <= 4km | Note 4 |

- **Note 1:** For UMa-AV LOS, breakpoint distance is not observed for the aerial UE height range 22.5m <= hUT <= 300m and 2D distance range d2D <= 4km.
- **Note 2:** In this expression, $PL_{RMa-AV-LOS}$ is the RMa-AV LOS pathloss of aerial UEs with height range 10m <= hUT <= 300m and 2D distance range d2D <= 10km.
- **Note 3:** In this expression, $PL'$ represents the free space path loss.
- **Note 4:** In this expression, $PL_{UMi-AV-LOS}$ is the UMi-AV LOS pathloss of aerial UEs with height range 22.5m < hUT <= 300m and 2D distance range d2D <= 4km.

## Table B-3: Shadow fading standard deviation

Log-normal shadow fading std for aerial UEs, again a delta to TR 38.901's Table 7.4.1-1 below the height threshold and an aerial-specific (height-dependent, or constant) value above it. Time-varying shadow fading for a moving UE is modelled by recalculating the SF value from this std after the UE has travelled 25 m.

_A matching CSV lives at `tables/table-B-3.csv`; YAML key `shadow_fading_std`._

| Scenario | Condition | Shadow fading std [dB] | Applicability |
|---|---|---|---|
| RMa-AV | LOS | According to Table 7.4.1-1 of [4] | 1.5m <= hUT <= 10m |
| RMa-AV | LOS | $\sigma_{SF} = 4.2\exp(-0.0046 h_{UT})$ | 10m < hUT <= 300m |
| RMa-AV | NLOS | According to Table 7.4.1-1 of [4] | 1.5m <= hUT <= 10m |
| RMa-AV | NLOS | $\sigma_{SF} = 6$ | 10m < hUT <= 40m |
| UMa-AV | LOS | According to Table 7.4.1-1 of [4] | 1.5m <= hUT <= 22.5m |
| UMa-AV | LOS | $\sigma_{SF} = 4.64\exp(-0.0066 h_{UT})$ | 22.5m < hUT <= 300m |
| UMa-AV | NLOS | According to Table 7.4.1-1 of [4] | 1.5m <= hUT <= 22.5m |
| UMa-AV | NLOS | $\sigma_{SF} = 6$ | 22.5m < hUT <= 100m |
| UMi-AV | LOS | According to Table 7.4.1-1 of [4] | 1.5m <= hUT <= 22.5m |
| UMi-AV | LOS | $\sigma_{SF} = \max(5\exp(-0.01 h_{UT}), 2)$ | 22.5m < hUT <= 300m |
| UMi-AV | NLOS | According to Table 7.4.1-1 of [4] | 1.5m <= hUT <= 22.5m |
| UMi-AV | NLOS | $\sigma_{SF} = 8$ | 22.5m < hUT <= 300m |

## Table B-4: Fast fading model selection

Which fast-fading model applies, by scenario and height: the ordinary TR 38.901 §7.5 model below the height threshold, and one of the aerial-specific alternatives in §B.1 above it.

_A matching CSV lives at `tables/table-B-4.csv`; YAML key `fast_fading_model_selection`._

| Scenario | Fast fading model | Applicability |
|---|---|---|
| RMa-AV | According to Section 7.5 of [4] | 1.5m <= hUT <= 10m |
| RMa-AV | According to Annex B.1 | 10m < hUT <= 300m |
| UMa-AV | According to Section 7.5 of [4] | 1.5m <= hUT <= 22.5m |
| UMa-AV | According to Annex B.1 | 22.5m < hUT <= 300m |
| UMi-AV | According to Section 7.5 of [4] | 1.5m <= hUT <= 22.5m |
| UMi-AV | According to Annex B.1 | 22.5m < hUT <= 300m |

## B.1 Fast fading models for Aerial UEs

For aerial UEs above the height thresholds (RMa-AV 10–300 m; UMa-AV/UMi-AV 22.5–300 m), one of **three interchangeable alternatives** may be used to evaluate the scenarios with 2Tx–2Rx at the base station and 1/2Tx–2Rx at the user terminal.

### B.1.1 Alternative 1 (CDL-D based)

For RMa-AV and UMa-AV aerial UEs, a **CDL-D based** fast fading model is used via the following procedure:

- **Step 1:** Follow steps 1–3 in Section 7.5 of [4] for UE dropping, LOS/NLOS assignment and pathloss calculation; for LOS/NLOS assignment and pathloss, Tables B-1, B-2, and B-3 are used.
- **Step 2:** Continue with steps 1–4 in Section 7.7.1 of [4] with parameters defined in Table 7.7.1-4 of [4] for channel coefficient generation.
- **Step 3:** The angle values are scaled according to Section 7.7.5.1 of [4] with the dropped aerial UE's actual LOS AOA/AOD/ZOA/ZOD as the desired mean AOA/AOD/ZOA/ZOD; the desired angular spreads ($AS_{desired}$ in Equation 7.7-5 of [4]) for RMa-AV and UMa-AV are given in Tables B.1.1-1 and B.1.1-2 respectively. Angular scaling is applied to ray angles ($\phi_{n,m,AOA}$ etc.) as in Step 1 of Section 7.7.1 in [4].
- **Step 4:** The CDL-D K-factor is scaled to a desired K-factor per Section 7.7.6 of [4], and the delay spread per Section 7.7.3 of [4] with a desired delay spread value. The desired K-factor and delay spread for RMa-AV and UMa-AV are in Tables B.1.1-1 and B.1.1-2.
- **Step 5:** For ZOD in LOS conditions, an offset angle is added only to the non-direct paths (all Laplacian clusters in CDL-D) after angle scaling. This offset is determined geometrically assuming specular reflection on the ground (RMa-AV) or the building roof (UMa-AV); the determined offsets are given by (B.1.1-1) and (B.1.1-2) respectively (see Figures B.1.1-1 and B.1.1-2 in the source TR).
- **Step 6:** For ZOD in NLOS conditions, $\mu_{ZOD,offset} = 0$ for both RMa-AV and UMa-AV.

<!-- Eq. B.1.1-1 -->
$$\mu_{ZOD,offset} = \theta_1 + \theta_2 = \arctan\left(\frac{h_{BS} + h_{UT}}{d_{2D}}\right) + \arctan\left(\frac{h_{UT} - h_{BS}}{d_{2D}}\right) \quad \text{(RMa-AV)}$$

<!-- Eq. B.1.1-2 -->
$$\mu_{ZOD,offset} = \theta_1 + \theta_2 = \arctan\left(\frac{h_{BS} + h_{UT} - 2h}{d_{2D}}\right) + \arctan\left(\frac{h_{UT} - h_{BS}}{d_{2D}}\right) \quad \text{(UMa-AV)}$$

For **UMi-AV** aerial UEs, Alternative 1 instead reuses the §7.5 fast fading model based on the *'reverse' UMa* scenario — the base station is below average rooftop height and the UE well above rooftop — with the angular spreads at the base station and UE interchanged.

The desired angular spreads, delay spread, and K-factor scaling targets:

_Matching CSVs live at `tables/table-B.1.1-1.csv` (RMa-AV) and `table-B.1.1-2.csv` (UMa-AV); YAML key `alternative_1_desired_parameters`._

**Table B.1.1-1: Desired angular spreads, delay spreads, and K-factor for RMa-AV**

| Scenario | ASA | ASD | ZSA | ZSD | Desired K | Desired DS |
|---|---|---|---|---|---|---|
| RMa-AV LOS | 0.2° | 0.2° | 0.1° | 0.1° | 20 dB | 10 ns |
| RMa-AV NLOS | 0.5° | 0.5° | 0.2° | 0.2° | 10 dB | 30 ns |

**Table B.1.1-2: Desired angular spreads, delay spreads, and K-factor for UMa-AV**

| Scenario | ASA | ASD | ZSA | ZSD | Desired K | Desired DS |
|---|---|---|---|---|---|---|
| UMa-AV LOS | 0.5° | 0.5° | 0.1° | 0.1° | 20 dB | 10 ns |
| UMa-AV NLOS | 1° | 1° | 0.3° | 0.3° | 10 dB | 30 ns |

### B.1.2 Alternative 2 (modified large-scale parameters)

For RMa-AV and UMa-AV aerial UEs, the §7.5 fast fading model is used with the DS, ASA, ASD, ZSA, ZSD, and K parameters modified (as height-dependent $\mu$/$\sigma$ formulas below). For UMi-AV aerial UEs, the §7.5 model is used with those parameters modified according to [9], and the number of clusters modelled as in [9]. All remaining parameters — cross-correlations among LSPs, delay scaling factor, XPR, number of clusters, cluster delay/angular spreads, per-cluster shadowing, and LSP autocorrelation distances — are reused from [4].

_Matching CSVs live at `tables/table-B.1.2-1.csv` (RMa-AV) and `table-B.1.2-2.csv` (UMa-AV); YAML key `alternative_2_modified_parameters`._

**Table B.1.2-1: Modified DS, ASA, ASD, ZSA, ZSD and K parameters for RMa-AV**

| Parameter | Scenario | $\mu$ | $\sigma$ |
|---|---|---|---|
| DS | RMa-AV LOS | $0.0549\log_{10}(h_{UT}) - 8.0945$ | $1.1879\exp(-0.0086 h_{UT})$ |
| DS | RMa-AV NLOS | $-1.3465\log_{10}(h_{UT}) - 7.0805$ | $1.5546\exp(0.0043 h_{UT})$ |
| ASA | RMa-AV LOS | $-2.214\log_{10}(h_{UT}) - 1.1645$ | $2.5622\exp(-0.00251 h_{UT})$ |
| ASA | RMa-AV NLOS | $-1.602\log_{10}(h_{UT}) + 1.439$ | $1.5316\exp(-0.0056 h_{UT})$ |
| ASD | RMa-AV LOS | $-1.431\log_{10}(h_{UT}) - 0.89$ | $2.2056\exp(0.0008 h_{UT})$ |
| ASD | RMa-AV NLOS | $-1.4633\log_{10}(h_{UT}) + 0.5212$ | $1.357\exp(0.0018 h_{UT})$ |
| ZSA | RMa-AV LOS | $-0.2409\log_{10}(h_{UT}) - 0.1569$ | $0.7579\exp(-0.0069 h_{UT})$ |
| ZSA | RMa-AV NLOS | $-1.097\log_{10}(h_{UT}) + 0.3287$ | $1.631\exp(-0.0087 h_{UT})$ |
| ZSD | RMa-AV LOS | $0.8105\log_{10}(h_{UT}) - 0.9774$ | $0.7106\exp(-0.0068 h_{UT})$ |
| ZSD | RMa-AV NLOS | $-0.869\log_{10}(h_{UT}) - 1.2355$ | $1.5851\exp(-0.0079 h_{UT})$ |
| K | RMa-AV LOS | $22.55\log_{10}(h_{UT}) - 4.72$ | $6.988\exp(0.01659 h_{UT})$ |

**Table B.1.2-2: Modified DS, ASA, ASD, ZSA, ZSD and K parameters for UMa-AV**

| Parameter | Scenario | $\mu$ | $\sigma$ |
|---|---|---|---|
| DS | UMa-AV LOS | $-0.31\log_{10}(h_{UT}) - 6.845$ | $0.7294\exp(0.0014 h_{UT})$ |
| DS | UMa-AV NLOS | $0.0965\log_{10}(h_{UT}) - 7.503$ | $0.9745\exp(-0.0045 h_{UT})$ |
| ASA | UMa-AV LOS | $-2.4985\log_{10}(h_{UT}) - 1.602$ | $1.0389\exp(0.0085 h_{UT})$ |
| ASA | UMa-AV NLOS | $-2.266\log_{10}(h_{UT}) - 2.666$ | $1.022\exp(0.009944 h_{UT})$ |
| ASD | UMa-AV LOS | $-0.0135\log_{10}(h_{UT}) + 1.345$ | $1.0188\exp(-0.0001 h_{UT})$ |
| ASD | UMa-AV NLOS | $1.17\log_{10}(h_{UT}) - 0.665$ | $1.2387\exp(-0.0046 h_{UT})$ |
| ZSA | UMa-AV LOS | $-0.2895\log_{10}(h_{UT}) + 0.225$ | $0.9576\exp(-0.0018 h_{UT})$ |
| ZSA | UMa-AV NLOS | $-0.0005\log_{10}(h_{UT}) - 0.4695$ | $1.6237\exp(-0.0076 h_{UT})$ |
| ZSD | UMa-AV LOS | $-0.2975\log_{10}(h_{UT}) - 0.5798$ | $1.0757\exp(0.0059 h_{UT})$ |
| ZSD | UMa-AV NLOS | $0.925\log_{10}(h_{UT}) - 2.725$ | $1.6421\exp(-0.0092 h_{UT})$ |
| K | UMa-AV LOS | $4.217\log_{10}(h_{UT}) + 5.787$ | $8.158\exp(0.0046 h_{UT})$ |

### B.1.3 Alternative 3 (constant K-factor)

For RMa-AV, UMa-AV, and UMi-AV aerial UEs, the §7.5 fast fading model is used with **K = 15 dB**. All remaining parameters — delay and angular spreads, cross-correlations among LSPs, delay scaling factor, XPR, number of clusters, cluster delay/angular spreads, per-cluster shadowing, and LSP autocorrelation distances — are reused from [4]. This alternative carries no parameter table of its own.

## Figures

See Figure B-1 ("Definition of 2D and 3D distances for aerial UEs"), Figure B.1.1-1 ("Geometry based ZOD offset angle determination for RMa-AV"), and Figure B.1.1-2 ("Geometry based ZOD offset angle determination for UMa-AV") in TR 36.777 Annex B.

## Verification note

TR 36.777 is a 2017 document whose equations are rendered as **embedded images** in every machine-readable format (the HTML export has 0 OMML equations and 365 image references; the PDF text layer likewise does not carry the formula digits). The HTML tag-strip formula-recovery cross-check that gave TR 38.901 a second independent formula source therefore does **not** apply here. Accordingly:

- **Simple-value content** — the Tables B.1.1-1/B.1.1-2 desired-parameter values, plus all scenario labels, applicability ranges, and "According to … of [4]" references — is **two-source verified** (PDF text extraction + PDF visual read; both independent of each other).
- **Formula content** — the piecewise LOS-probability formulas (B-1), pathloss expressions (B-2), shadow-fading formulas (B-3), the modified $\mu$/$\sigma$ formulas (B.1.2-1/B.1.2-2), and the ZOD-offset equations (B.1.1-1/B.1.1-2) — is **PDF-visual single-source**: the values below were read carefully off the rendered PDF, which is the only source that carries them. This is the same honest single-source handling used for TR 38.901 §7.5's procedural equations. The section-level `verified_against: ["pdf", "html"]` reflects that both formats were consulted (HTML for prose/structure, PDF for everything including formulas), not that every formula was cross-checked against two independent parses.
