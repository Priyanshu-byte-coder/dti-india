# Digital Task Intensity (DTI) of Indian Occupations — Implementation Plan & Questions for IMNU

*Prepared 17 Oct 2026 · Paper: "Measuring the Digital Task Intensity of Indian Occupations Using Large Language Models: Evidence on Wage Premiums and Labour Market Inequality from PLFS" (Nair, Anand, Shome)*

**Bottom line.** The pipeline has four blocks: (1) score NCO-2015 occupation text with an LLM on five digital dimensions, (2) validate the scores (stability, human coders, O\*NET), (3) map scores onto PLFS workers through NCO codes, (4) estimate a conditional wage premium and its heterogeneity. Blocks 1–2 are mostly our (CSE) side. Blocks 3–4 need decisions from the Management/Economics side. **Section 9 lists the exact questions to settle with the professors**, each with our proposed default so the meeting can go fast.

---

## 1. What the abstract commits us to

| Item | Commitment in abstract | Implication |
|---|---|---|
| RQ1 | Reliable, reproducible DTI from NCO text via LLM | Rubric + repeated runs + human agreement stats |
| RQ2 | Compare India DTI vs O\*NET-transferred DTI | Need NCO ↔ ISCO ↔ SOC crosswalk + gap measure |
| RQ3 | Conditional wage premium of DTI in PLFS | Mincer-type log-wage regression |
| RQ4 | Heterogeneity by gender, education, rural/urban, formality, etc. | Interactions + causal forest / GRF + best linear projection |
| Index | 5 dimensions, ordinal rubric, standardised, equal weights (alternatives as robustness) | Weights and standardisation base must be fixed |
| Claim | "Conditional digital occupational premium", **not** causal | Keep identification language modest; add sensitivity checks |

Equations already in the abstract:

```latex
DTI_j = \sum_{k=1}^{5} w_k D_{jk}
```

```latex
DigitalGap_j = DTI_j^{O*NET} - DTI_j^{NCO\text{-}LLM}
```

```latex
\ln Wage_i = \alpha + \beta\, DTI_{j(i)} + \gamma X_i + \delta_s + \lambda_r + \tau_t + \epsilon_i
```

The five dimensions: (1) basic digital operation, (2) digital information processing, (3) digital communication & collaboration, (4) advanced/specialised digital-tool use, (5) digital problem solving & content creation.

---

## 2. What the reference papers give us

| Paper | What we reuse |
|---|---|
| Vashisht & Dubey (2019), ICRIER WP 355 | O\*NET → NCO-2004 crosswalk at **3-digit** (via SOC); 16 O\*NET task items → 5 task indices; items standardised with **NSS employment weights**, summed, re-standardised. Crosswalk "available on demand" from authors. No wage model. |
| Sharma, Gupta & Estupinan (2020), IGIDR WP-2020-028 | **Closest template for our mapping.** Rated NCO-2015 work activities (511 activities, 436 4-digit occupations) by 4 economists on {0, 0.5, 1}; median rater per activity; averaged to NCO 4-digit and 3-digit; crosswalk NCO-2015 → NCO-2004 to link to PLFS 2018-19 (3-digit NCO-2004). Reported inter-rater reliability. |
| Cirillo et al. (2021), Research Policy — Italian ICP | Two indices: *digital use* (computer + e-mail use, averaged, rescaled 0–100) and *digital task index* (131 of 6,200+ task statements flagged as digital, share per occupation). 4-digit ISCO-type level. |
| Stöllinger & Guarascio (2025), Open Economies Review | O\*NET DTI built by **keyword search on up to 15 core task statements** per occupation; score = share of digital tasks; SOC → ISCO-08 crosswalk, aggregated to ISCO 3-digit. ICP vs O\*NET DTI correlation 0.89. Muro et al. (2017) 2-variable O\*NET index as simpler alternative. |
| Adrjan et al. (2026), ADB WP 850 | LLM (GPT-4.1 mini) classifies job ads into none / basic / intermediate / advanced digital; structured prompt with definitions, examples, reasoning rules and a required justification; validated on **200 ads vs 2 human annotators** (~80% agreement, similar to human–human). Wage premia 4% / 11% / 26% with job-title FE. |
| Sami (2026), IJM — Egypt ELMPS | Econometric menu: Mincer on log **hourly** wage with Female × DSI interaction; quantile regression; Heckman selection (exclusions: household size, household head, children, family obligation); Blau et al. (2024) selection; IV robustness; PCA/MCA index. |

---

## 3. Pipeline overview

1. **Collect text** — NCO-2015 Vol. I (division → family descriptions + tasks) and Vol. II (8-digit occupation descriptions). Parse PDFs into a table: `nco2015_code, level, title, description, tasks`.
2. **Rubric** — 5 dimensions × ordinal scale (proposed 0–4) with written anchors and Indian examples. Signed off by Prof. Anand.
3. **LLM scoring** — fixed prompt, temperature 0, structured JSON output with a score, a text quote as evidence, and a confidence flag per dimension. R repeated runs (proposed 5) and at least 2 model families.
4. **Reliability** — intra-model stability (SD across runs, ICC); flag high-variance occupations for manual review.
5. **Human validation** — stratified sample coded by ≥2 humans blind to LLM scores; Krippendorff's α (ordinal) and quadratic-weighted κ.
6. **O\*NET benchmark** — O\*NET-SOC → ISCO-08 → NCO-2015 3-/4-digit; build O\*NET DTI; compute rank correlation and `DigitalGap_j`.
7. **Aggregate to PLFS level** — 8-digit/4-digit scores → NCO-2015 3-digit (the PLFS code level).
8. **Merge with PLFS** — on 3-digit occupation code; construct wages, hours, controls, formality.
9. **Estimate** — baseline OLS, robustness, distributional models, heterogeneity (interactions + GRF).
10. **Write-up** — tables, DTI ranking, gap analysis, policy section.

---

## 4. Data sources

| Source | Version / rounds | Level | Access |
|---|---|---|---|
| NCO-2015 (Ministry of Labour & Employment / DGE) | 2015 edition, Vol. I & II | 1/2/3/4/8-digit; 4-digit family ≈ ISCO-08 unit group | Public PDF; needs parsing |
| PLFS unit-level data (MoSPI) | Proposed: 2022-23 and 2023-24 annual; optional 2021-22 and 2025 (new design) | Occupation **3-digit NCO-2015** from July 2021; NCO-2004 3-digit before that | microdata.gov.in (free registration) |
| O\*NET | Latest release (e.g. 29.x/30.x) | O\*NET-SOC 2019 (8-digit) | Free download |
| SOC ↔ ISCO-08 crosswalk | BLS crosswalk | SOC 2010/2018 ↔ ISCO-08 4-digit | Free |
| US employment weights | BLS OEWS | SOC 6-digit | Free; used to weight SOC → ISCO aggregation |
| Vashisht & Dubey crosswalk (optional) | SOC → NCO-2004 3-digit | 3-digit | Request from authors |
| CPI deflators | CPI-AL/RL (rural), CPI-IW or CPI-Urban | State × year/quarter | Labour Bureau / MoSPI |

**Verify before building:** the exact occupation field and code version in each PLFS file we download (MoSPI states NCO-2015 3-digit from July 2021; the 2025 redesign keeps NCO-2015 3-digit).

---

## 5. Data mapping plan

### 5a. India side (main DTI)

```
NCO-2015 8-digit occupation text  ──LLM──►  D_jk (8-digit)
        │ aggregate (mean / median / max — to decide)
        ▼
NCO-2015 4-digit family  ──►  NCO-2015 3-digit group  ──merge──►  PLFS worker (3-digit NCO-2015)
```

- PLFS only has 3-digit codes (~130 groups). All within-group variation in DTI is lost at merge. This is the single most important mapping constraint.
- No official employment counts exist at 8-digit or 4-digit, so aggregation weights within a 3-digit group are a decision (Q-C2).
- Alternative: score the 3-digit and 4-digit group descriptions directly and compare with the bottom-up aggregate (a useful robustness check).
- If pre-2021 PLFS rounds are used, an NCO-2015 → NCO-2004 crosswalk is needed (the IGIDR paper did this). Recommended: avoid by using only July-2021+ rounds.

### 5b. O\*NET side (validation and gap)

```
O*NET-SOC 2019 (8-digit) ─► SOC 2018 6-digit ─► SOC 2010 ─BLS─► ISCO-08 4-digit = NCO-2015 4-digit ─► 3-digit
```

- Many-to-many links at each step. Proposed rule: SOC → ISCO split weighted by US OEWS employment; ISCO 4-digit → 3-digit weighted by OEWS employment (or PLFS employment, Q-C5).
- Two O\*NET measures, both reported:
    1. **Same-instrument measure:** run our LLM rubric on O\*NET task statements. Then the gap reflects *description differences*, not instrument differences. This is the cleanest test for RQ2.
    2. **Conventional measure:** Stöllinger–Guarascio keyword share on core task statements, plus O\*NET "Working with Computers" (work activity), "Computers and Electronics" (knowledge) and the e-mail work-context item (Muro et al.-style).
- Gap requires a common scale: z-scores standardised with the same PLFS employment weights, or percentile ranks.

### 5c. PLFS variables needed

| Construct | PLFS source (verify in instruction manual) |
|---|---|
| Earnings — regular wage/salaried | Earnings for last calendar month (CWS block) |
| Earnings — casual labour | Daily earnings for each day of the reference week |
| Earnings — self-employed | Gross earnings in last 30 days (includes returns to capital) |
| Hours | Hours actually worked per day in reference week (CWS) |
| Occupation / industry | NCO-2015 3-digit / NIC-2008 (2- or 5-digit) |
| Formality (regular wage workers only) | Written job contract, paid leave, social-security eligibility |
| Controls | Age, sex, education level and years, marital status, social group, religion, state, district, rural/urban, quarter, enterprise type and size |
| Selection instruments (if Heckman) | Household size, number of children under 5/under 15, household head, land owned, other members' income |
| Design | Multiplier (weight), FSU (cluster), stratum, sub-stratum, visit number |

---

## 6. DTI construction — design decisions on our side

- **Prompt contents:** rubric text (fixed), occupation title + description + tasks verbatim, instruction to score *only from the text* (see Q-B3), JSON schema with per-dimension `score`, `evidence_quote`, `confidence`.
- **Models:** one closed (e.g. GPT/Claude/Gemini) plus one open-weight (e.g. Llama/Qwen) for reproducibility; temperature 0; model version and date logged.
- **Runs:** 5 runs per occupation per model; final score = median; report SD and ICC.
- **Standardisation:** z-score each dimension using PLFS employment weights (as Vashisht & Dubey), sum with `w_k = 1/5`, re-standardise. Robustness: PCA weights, expert weights, min–max 0–100 (Cirillo et al.).
- **Prompt engineering protocol:** iterate on a 30–50 occupation development set, freeze prompt, then score all — dev set excluded from human-validation sample.

---

## 7. Validation plan

| Test | Method | Pass threshold (proposed) |
|---|---|---|
| Intra-model stability | SD across 5 runs; ICC(2,1) | ICC ≥ 0.9; manual review if SD > 0.5 |
| Cross-model agreement | Spearman ρ, weighted κ between model families | ρ ≥ 0.8 |
| Human–LLM agreement | Krippendorff's α (ordinal), quadratic-weighted κ; compare with human–human | α ≥ 0.667 (tentative), ≥ 0.8 (strong) |
| External (O\*NET) | Pearson/Spearman at 3-digit; scatter; top/bottom-10 lists | No threshold — gap is a result |
| Face validity | Top/bottom occupations by DTI; DTI by NCO skill level 1–4 | Monotone rise with skill level expected |

---

## 8. Econometric plan (proposed — to be confirmed in Section 9A)

**Baseline (RQ3):** OLS of log real hourly wage on standardised DTI with individual controls, NIC 2-digit FE, state (or district) FE, rural/urban, quarter × year FE; PLFS weights; SEs clustered at **3-digit occupation** (the level where DTI varies).

**Central identification issue.** DTI varies only across ~130 occupation groups, so 3-digit occupation FE cannot be included and β partly captures everything else that differs across occupations (skill level, cognitive content, unions, public sector). Proposed handling:

- Add NCO 1-digit division FE or NCO skill-level FE, so β is identified *within* broad occupation groups.
- Optionally control for non-digital task content (Vashisht–Dubey cognitive/routine indices) to separate "digital" from "cognitive".
- Oster (2019) coefficient-stability bounds to show how strong unobserved selection must be to remove β.
- Few-cluster inference: wild cluster bootstrap (occupation clusters).
- **Heterogeneity interactions (DTI × female, DTI × education, DTI × rural) are identified even with full 3-digit occupation FE.** That makes RQ4 more credible than RQ3 — a selling point.

**Robustness and extensions:**

- Wage measures: hourly vs monthly; regular wage workers only vs regular + casual; self-employed as separate sample.
- Treatment form: continuous z-score vs DTI terciles/quintiles vs high-DTI dummy.
- Selection: Heckman (employment or wage-employment participation, especially women) or Blau et al. (2024).
- Distribution: conditional quantile regression and/or RIF unconditional quantile regression (Firpo–Fortin–Lemieux).
- Decomposition: Oaxaca–Blinder (or Gelbach) to show how much of the gender/rural wage gap runs through DTI.
- Alternative DTIs: each dimension separately, alternative weights, O\*NET DTI in place of NCO-LLM DTI (direct RQ2 payoff: does the premium change?).

**Heterogeneity (RQ4):** subgroup regressions and interactions first; then GRF causal forest with continuous treatment (DTI), clustered by occupation, honest splitting; summarise with best linear projection on pre-specified covariates (gender, education, rural/urban, formality, age group, sector, social group); report calibration test and overlap diagnostics. Double/debiased ML partially linear model as a check on the average effect.

---

## 9. Questions for the professors (with our proposed default)

### A. Econometrics — mainly Prof. Samik Shome

| # | Question | Our proposed default |
|---|---|---|
| A1 | Primary outcome: log **hourly** or log **monthly/weekly** real earnings? | Log real hourly; monthly as robustness |
| A2 | Primary sample: regular wage/salaried only, regular + casual, or also self-employed? | Regular + casual; self-employed separate (their earnings include capital returns) |
| A3 | Age band and status concept: 15–59 or 15–64; CWS or usual principal status? | 15–64; CWS (wages are recorded in CWS) |
| A4 | Which PLFS rounds — single year, or pooled 2022-23 + 2023-24 with year FE? Include 2025 new-design data? | Pool 2022-23 + 2023-24; 2025 as replication |
| A5 | Occupation controls: since DTI varies only across ~130 groups, do we include NCO 1-digit FE, skill-level FE, or none in the baseline? | 1-digit FE in preferred spec; none and skill-level as alternates |
| A6 | Should we control for other O\*NET task contents (cognitive, routine) to isolate "digital", or does that dilute the India-specific story? | Robustness only |
| A7 | Standard errors: cluster by occupation (~130 clusters), two-way occupation × state, or FSU (survey design)? Wild bootstrap needed? | Cluster by 3-digit occupation; wild cluster bootstrap as check |
| A8 | Survey weights in regressions — weighted or unweighted (Solon–Haider–Wooldridge)? | Weighted main, unweighted robustness |
| A9 | Selection correction: is Heckman needed (esp. for women)? Which exclusion restrictions are defensible in PLFS? Or Blau et al. (2024)? | Heckman for wage-employment participation; exclusions: children under 5, household size, household head |
| A10 | Endogeneity: is "conditional premium" + Oster bounds enough, or will reviewers expect an IV? Any India-specific instrument in mind? | No IV; Oster bounds + clear non-causal framing |
| A11 | Distributional analysis: conditional quantile regression, RIF-UQR, or both? Oaxaca–Blinder decomposition of gender/rural gap? | RIF-UQR + Oaxaca–Blinder on gender |
| A12 | Is GRF/causal forest acceptable to the economics audience with an occupation-level continuous treatment, or keep interactions as the main RQ4 evidence and GRF as supplementary? | Interactions main; GRF + BLP supplementary |
| A13 | Which heterogeneity covariates do we **pre-specify** (to avoid fishing)? | Gender, education level, rural/urban, formality, age group, sector, social group |
| A14 | Treatment form: continuous standardised DTI, quintiles, or high-DTI dummy (what threshold)? | Continuous main; quintiles for non-linearity |
| A15 | Deflator: CPI-AL/RL for rural and CPI-IW/Urban for urban, by state? Base year? | State-level CPI-Rural/Urban, base 2012 = 100 |

### B. Domain-specific inputs — mainly Prof. Gunjan Anand

| # | Question | Our proposed default |
|---|---|---|
| B1 | Are the five dimensions final? Should they align formally to DigComp 2.2 / ESCO digital skills, and are any missing (e.g. digital safety/security, digital payments)? | Keep five; map each to DigComp 2.2 areas in an appendix |
| B2 | Scale and anchors: 0–4 per dimension? Can you provide or review the written anchor for each level, with Indian occupation examples (UPI/POS for shop staff, GeM for procurement, Tally for accountants, CNC for machinists)? | 0–4 (none, incidental, regular basic, regular advanced, core/specialist) |
| B3 | Text-only vs world knowledge: must the LLM score **only what the NCO text says**, or may it infer typical current practice? NCO-2015 text may be dated or sparse. | Text-grounded main score with evidence quote; "knowledge-allowed" score as robustness |
| B4 | Boundary cases: does operating automated machinery (CNC, PLC, ATM servicing) count as "advanced digital tool use"? Do phone/WhatsApp-based coordination count as "digital communication"? | Need a written ruling for each |
| B5 | Human coders: who (faculty, PhD scholars, HR practitioners), how many (≥2, ideally 3), and is there time/budget to pay them? | 3 coders: 1 HR faculty + 2 trained research assistants |
| B6 | Validation sample size and strata: how many occupations, stratified by NCO skill level (1–4) and division? | 200 occupations (~6% of 3,600), stratified by skill level × division |
| B7 | Coder protocol: training round, calibration set, blind to LLM output, disagreement resolution (median vs discussion)? | 30-occupation calibration; blind coding; median for final; discussion only for reporting |
| B8 | Acceptable agreement threshold for Krippendorff's α to claim reliability? | α ≥ 0.667 acceptable, ≥ 0.8 good |
| B9 | Aggregation weights: equal weights only, or should we also collect **expert weights** (e.g. AHP survey of HR experts) as a robustness index? | Equal main; PCA + expert weights as robustness |
| B10 | Supplementary text: should we add NSQF Qualification Packs / Skill India job roles where NCO text is thin, or keep NCO text only for purity? | NCO only main; QP-augmented as robustness |
| B11 | Formality definition: NCEUS (no written contract, no paid leave, no social security) for regular wage workers? How to treat casual workers (all informal)? | NCEUS definition; casual = informal |
| B12 | Which policy angles matter most for the conference (skilling schemes, women's work, informality)? Shapes which heterogeneity results we foreground. | Digital-skills gap vs digital-returns gap framing |

### C. Data mapping — both professors

| # | Question | Our proposed default |
|---|---|---|
| C1 | Score at **8-digit** NCO occupations (~3,600 texts) or at **4-digit** family level? | Score 8-digit; also score 4-digit and 3-digit descriptions directly for comparison |
| C2 | Aggregating 8-digit → 3-digit with no employment counts: simple mean, median, or max? | Simple mean main; median as robustness |
| C3 | Use only July-2021+ PLFS (NCO-2015 3-digit, no crosswalk) or also older rounds (NCO-2004, needs NCO-2015 → NCO-2004 crosswalk)? | July-2021+ only |
| C4 | O\*NET path: BLS SOC → ISCO-08 crosswalk with OEWS weights — acceptable? Should we request Vashisht & Dubey's SOC → NCO-2004 crosswalk for comparability with their work? | BLS + OEWS; request V&D crosswalk as a cross-check |
| C5 | Weights for standardising DTI and aggregating O\*NET to 3-digit: PLFS (Indian) employment or US OEWS employment? | PLFS employment for standardisation; OEWS within SOC → ISCO splits |
| C6 | Which O\*NET benchmark is primary: same-LLM-rubric on O\*NET tasks, keyword share (Stöllinger–Guarascio), or "Working with Computers" item? | Same-rubric primary; others reported |
| C7 | Gap scale: z-scores or percentile ranks? Report gap by NCO division and skill level? | Percentile ranks; gap by division and skill level |
| C8 | Occupations with no O\*NET match or unclassifiable codes (armed forces, "not elsewhere classified"): drop or keep in wage models? | Keep in wage models; drop from gap analysis |
| C9 | Any external Indian validation data — e.g. NSS 78th round / CAMS ICT-skill items, or Naukri/LinkedIn job-ad text — worth adding as extra validation? | Optional, if time allows |

### D. Logistics

| # | Question |
|---|---|
| D1 | Full-paper deadline for the SAU conference, and target journal after it? |
| D2 | LLM API budget and whether open-weight models are required for reproducibility (data/code release)? |
| D3 | Who downloads and holds PLFS microdata (MoSPI registration in whose name)? |
| D4 | Software for econometrics: Stata (`reghdfe`, `oaxaca`, `rifhdreg`, `boottest`) or R/Python (`fixest`, `grf`, `DoubleML`)? |
| D5 | Work split: CSE side = NCO parsing, rubric prompts, LLM scoring, reliability, O\*NET mapping; Management side = rubric anchors, human coding, PLFS cleaning, econometrics, write-up — agreed? |

---

## 10. Proposed work sequence

| Phase | Output | Owner | Depends on |
|---|---|---|---|
| 1 | NCO-2015 text parsed into table | CSE | — |
| 2 | Rubric v1 with anchors | HRM (B1–B4) | Meeting |
| 3 | Prompt dev on 30–50 occupations; freeze | CSE | Phase 1, 2 |
| 4 | Full LLM scoring, 5 runs × 2 models | CSE | Phase 3, D2 |
| 5 | Human coding of 200 occupations; α/κ | HRM + RAs | Phase 2 (B5–B8) |
| 6 | O\*NET DTI + crosswalk + gap | CSE | C4–C7 |
| 7 | PLFS cleaning, wages, merge on 3-digit | Econ | A1–A4, C1–C3 |
| 8 | Baseline + robustness models | Econ | Phase 4, 7 |
| 9 | Heterogeneity: interactions, GRF, BLP | Econ + CSE | Phase 8 |
| 10 | Draft paper | All | Phase 5–9 |

Phases 1, 6 and 7 can run in parallel right after the meeting.

---

## Sources

- Extended abstract (this folder): *Extended Abstract (Digital Task Intensity of Indian Occupations) (1).docx*
- [Vashisht & Dubey (2019), ICRIER Working Paper 355](https://icrier.org/pdf/Working_Paper_355.pdf)
- [Sharma, Gupta & Estupinan (2020), IGIDR WP-2020-028](http://www.igidr.ac.in/pdf/publication/WP-2020-028.pdf)
- Cirillo, Evangelista, Guarascio & Sostero (2021), *Research Policy* 50, 104079 (this folder)
- Stöllinger & Guarascio (2025), *Open Economies Review* 36, 329–371 (this folder)
- Adrjan et al. (2026), ADB Economics Working Paper 850 (this folder)
- Sami (2026), *International Journal of Manpower* 47(2), 283–305 (this folder)
- [MoSPI — Changes in PLFS from 2025](https://www.mospi.gov.in/sites/default/files/publication_reports/PLFS_Changes-in-2025_rev.pdf) (occupation recorded as 3-digit NCO-2015)
- [IMF DQAF — India wages/earnings](https://dsbb.imf.org/sdds/dqaf-base/country/IND/category/WOE00) ("From July 2021, NCO-2015 is being used in PLFS")
- [PLFS microdata portal](https://microdata.gov.in/NADA/index.php/catalog/PLFS)
