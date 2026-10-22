# Implementation — how the study was built and run

Complete technical description of the pipeline behind "Measuring the Digital Task Intensity of Indian
Occupations Using Large Language Models: Evidence on Wage Premiums and Labour Market Inequality from PLFS"
(Nair, Anand & Shome, Nirma University). Written so that the Methods section of the paper can be drafted from
it and the study can be reproduced. Results and their meaning are in [RESULTS.md](RESULTS.md); design choices
and who made them are in [decisions.md](decisions.md).

---

## 1. Overview

```
NCO-2015 Vol II text (3,450 occupations)            O*NET 31.0 text (923 occupations)
        │                                                   │
        ▼                                                   ▼
  LLM coding with a fixed rubric  ── same prompt ──  LLM coding with the same rubric
  (Qwen2.5-14B main, Llama-3.1-8B check;              (Qwen2.5-14B)
   5 runs each, evidence quotes, JSON schema)               │
        │                                                   ▼
        ▼                                           SOC 2019→2010→ISCO-08 (BLS) → NCO families
  consensus (median of 5 runs) → 5 dimension scores         │
        │                                                   │
        ▼                                                   ▼
  DTI = equal-weight sum of z-scored dimensions     RQ2: correlation + DigitalGap by family
        │
        ├── RQ1: run stability, cross-model agreement, grounding, (human validation)
        ▼
  aggregate to 4-digit families / 3-digit groups (NCO-2015) and NCO-2004 3-digit groups
        │
        ▼
  merge onto PLFS 2017-18 … 2023-24 workers by occupation code
        │
        ▼
  RQ3: wage regressions (FE ladder, robustness, Oster, Heckman)
  RQ4: RIF/quantile, interactions, subgroups, Oaxaca–Blinder, DoubleML (4 learners)
```

All code is in the private repository `Priyanshu-byte-coder/dti-india` (Python package `dti`, command `dti`).
Every number in the paper is produced by a command; nothing is typed by hand.

## 2. Data sources

| Source | Content used | Version / access | Notes |
|---|---|---|---|
| **NCO-2015** (Ministry of Labour & Employment, DGE), Vol I and Vol II-A/II-B | Title and description of every 8-digit occupation (3,450); hierarchy (division, sub-division, group, family); NCO-2004 concordance codes | Machine-readable table checked against the official PDFs (median 100% word overlap); 2 duplicates removed, 3 missing and 4 cut-off descriptions restored from Vol II | Division 0 (armed forces) has no descriptions and is excluded |
| **PLFS** (MoSPI), first-visit person and household files | Seven annual July–June rounds: 2017-18, 2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24 | microdata.gov.in; CSV | Rounds up to 2020-21 code occupation in NCO-2004, from 2021-22 in NCO-2015 (3-digit). **Not redistributed** (MoSPI terms) |
| **O*NET 31.0** (US DoL) | Occupation descriptions, core task statements, Work Activities, Knowledge, Work Context | onetcenter.org, CC BY 4.0 | 923 O*NET-SOC 2019 occupations with text |
| **O*NET-SOC 2019 ↔ 2010 crosswalk**, **BLS ISCO-08 ↔ SOC 2010 crosswalk**, **BLS OEWS May 2025 national** | Linking US occupations to ISCO-08 (= NCO-2015 at 4 digits); US employment weights | bls.gov, onetcenter.org | 910 O*NET occupations → 419 ISCO-08 groups |

## 3. The measure: Digital Task Intensity (DTI)

### 3.1 Dimensions

Five dimensions, each scored on the same 0–4 scale (`configs/rubric_strict.yaml`; identical to the human coder form):

| Dim. | Form item | Name | Covers |
|---|---|---|---|
| D1 | Q2 | Basic digital operation | Routine use of computers, phones, tablets, POS/billing machines, standard software |
| D2 | Q3 | Digital information processing | Searching, recording, managing, interpreting or analysing digital information |
| D3 | Q4 | Digital communication & collaboration | E-mail, messaging, video calls, platforms (CRM, ticketing, e-commerce, gig apps, government portals); voice calls excluded |
| D4 | Q5 | Advanced / specialised digital tools | Occupation-specific software, programming, CAD, GIS, analytics, CNC/PLC, medical imaging, automated systems |
| D5 | Q6 | Digital problem solving & content creation | Creating digital content or solving non-routine problems with digital tools |

Scale: 0 none · 1 incidental · 2 regular, basic · 3 regular, advanced / job-specific · 4 core (the main work). Each
dimension has anchor examples for every level (see `example_prompt.txt` in this folder).

Additional items per occupation: Q1 is the description detailed enough (Yes/Partly/No); Q7 evidence — exact words from
the description supporting each non-zero score; Q8 confidence 1–3 per dimension; Q9 holistic digital intensity 0–10;
Q10 digital work Core / Supporting / Not relevant; Q11 in India today, more / same / less digital than the text suggests
(the only item allowed to use general knowledge); Q12 comment.

### 3.2 Rubric reading ("text only")

The professors decided that the LLM scores **only from the NCO text, with no external sources**. Two readings were
piloted: *strict* (v1.0: score only digital work the text names; silent → 0) and *described-task* (v1.1: also tasks the
text describes that are normally done digitally, still quoting the text). The pilot (Section 6) selected **strict** as
the main measure. Prompt hash of the strict rubric: **46a323537a** (every output records it, so runs with different
prompts can never be mixed).

### 3.3 From scores to the index

1. Five independent runs per occupation (seeds 0–4, temperature 0.7) → **median** per dimension = consensus score
   (run-to-run SD kept per dimension; occupations with SD > 0.5 on any dimension are flagged).
2. Each consensus dimension is z-scored across the 3,450 occupations.
3. **DTI = equal-weight sum of the five z-scores, re-standardised** (abstract eq. 1). Also stored: `dti_0_100`
   (min–max rescaled) and `dti_mean_score` (plain mean of the five 0–4 scores, for readability).
4. Aggregation to 4-digit families and 3-digit groups: **mean** of member occupations (equal weights; no employment
   counts exist below 3 digits), median as robustness.
5. **NCO-2015 → NCO-2004** for the 2017-21 PLFS rounds: 2,657 occupations carry a direct NCO-2004 concordance code (Vol I);
   759 new occupations take the most common NCO-2004 code in their family, 32 in their group, 2 have no link.
   Result: 112 NCO-2004 3-digit groups; `share_direct_link` records how much of each rests on direct links.
6. In the wage models DTI is re-standardised across workers in the estimation sample (`dti_std`), so coefficients are
   per 1 SD of worker-level DTI.

## 4. LLM scoring

### 4.1 Models

| Role | Model | Quantisation | Why |
|---|---|---|---|
| Main instrument | **Qwen2.5-14B-Instruct** (Alibaba) | GGUF Q4_K_M (9.0 GB) | Largest model that fits the 16 GB GPU; more stable and better grounded in the pilot |
| Second family (cross-check) | **Llama-3.1-8B-Instruct** (Meta) | GGUF Q8_0 (8.5 GB) | Different developer and training data; tests that results do not depend on one model |

Open-weight models run locally: no occupation text or data leaves the university server; exact model files are
fixed (SHA-256 verified), so the runs are reproducible.

### 4.2 Hardware and serving

- **PARAM Shavak** (Nirma University): NVIDIA **Quadro GP100 16 GB** (Pascal, compute 6.0), 36 CPU cores, 92 GB RAM, CentOS 7.3.
- vLLM cannot run on Pascal/CentOS 7, so **llama.cpp** (`llama-server`) was compiled for sm_60 (gcc 9.1, CUDA 12.2) and
  serves an OpenAI-compatible endpoint; all layers on the GPU (`-ngl 999`), 8 parallel slots × 3,072 context tokens for
  NCO (6 × 4,096 for the longer O*NET prompts), continuous batching.
- Jobs ran in `screen` sessions (the PBS queue accepts but does not dispatch jobs on this machine).

### 4.3 Prompt and output

- **System message:** role, the six rules, the scale, the five dimensions with anchors, Q1–Q12, output format.
- **Few-shot example:** one worked occupation (illustrative Accounts Clerk text) with its full JSON answer.
- **User message:** occupation title + description only.
- **Structured output:** JSON schema enforced by the server (pydantic model `Coding`): for each dimension
  `rationale`, `evidence`, `score` (0–4), `confidence` (1–3); plus q1, q9–q12. A call that fails or returns output that does not fit the schema is retried up to 3 times (none failed in the end).
- Settings: temperature **0.7** (so repeated runs can disagree and stability is a real test), max 1,500 output tokens,
  5 runs per occupation with seeds 0–4.
- **Evidence check:** every quoted evidence string is matched against the description: `exact`, `close` (content words in
  order within a 3-token window, stopwords ignored), `partial`, `not_found`, `empty`. A non-zero score whose evidence is
  `not_found`, `partial` or `empty` counts as **ungrounded**.
- Full example prompt (system + few-shot + one real occupation) and the model's answer: `example_prompt.txt`,
  `example_output.json` in this folder.

### 4.4 What was run (all completed, 0 failed calls)

| Job | Model | Rubric | Units × runs | Calls | Started (IST) | Ended (IST) | Wall time | Tokens in / out |
|---|---|---|---|---|---|---|---|---|
| Smoke test | Qwen | described-task | 3 calls | 3 | 20 Oct 01:57 | 20 Oct 01:59 | 2 min | — |
| Pilot | Qwen | described-task | 50 × 5 | 250 | 20 Oct 02:07 | 20 Oct 02:30 | 23 min | |
| Pilot | Qwen | strict | 50 × 5 | 250 | 20 Oct 02:32 | 20 Oct 02:54 | 22 min | |
| Pilot | Llama | described-task | 50 × 5 | 250 | 20 Oct 02:55 | 20 Oct 03:04 | 9 min | |
| Pilot | Llama | strict | 50 × 5 | 250 | 20 Oct 03:04 | 20 Oct 03:13 | 9 min | |
| **Full NCO** | **Qwen** | strict | 3,450 × 5 | 17,250 | 20 Oct 03:15 | 21 Oct 05:50 | **26.5 h** | 30.4 M / 4.4 M |
| **Full NCO** | **Llama** | strict | 3,450 × 5 | 17,250 | 21 Oct 05:50 | 21 Oct 15:41 | **9.8 h** | 30.5 M / 3.8 M |
| **O*NET (RQ2)** | **Qwen** | strict | 923 × 5 | 4,615 | 21 Oct 15:44 | 22 Oct 01:02 | **9.3 h** | 9.1 M / 1.5 M |

The full NCO runs reuse the 250 strict-pilot calls (same prompt hash, same seeds). The GPU ran continuously for
about 46 hours (20 Oct 03:15 → 22 Oct 01:02). Throughput: Qwen ≈ 640 calls/h, Llama ≈ 1,740 calls/h, Qwen on
O*NET text ≈ 500 calls/h. Figures 1–4 show the timeline, progress, throughput and tokens; `run_log.csv` has one row per
call (39,615 rows).

CPU analysis jobs on the same server: wage analysis with the Qwen DTI 21 Oct 06:43–08:34; Llama robustness and
cross-model agreement 15:46–15:54; DoubleML learner comparison 18:19–19:43; RQ2 aggregation and gap 22 Oct 01:02–01:04.

## 5. Reliability and validation (RQ1)

| Check | Statistic | Implementation |
|---|---|---|
| Intra-model stability | ICC(2,1) and ICC(2,k) (two-way random, absolute agreement, Shrout–Fleiss); Krippendorff's ordinal α; share of occupations with 5 identical runs; mean run SD | `dti reliability` → `stability_runs.csv` |
| Cross-model agreement | Exact and within-1 agreement, quadratic-weighted Cohen's κ, Spearman ρ, ordinal α per dimension; DTI correlation at occupation, family and group level | `cross_model.csv`, RESULTS.md 3.4 |
| Grounding | Share of non-zero scores whose evidence quote is found in the description | evidence check, Section 4.3 |
| Internal consistency | Spearman between the equal-weight dimension mean and the model's own holistic Q9 | `q9_vs_equal_weight.csv` |
| Keyword benchmark | Share of description sentences with a digital keyword (Stöllinger & Guarascio style), correlated with the LLM score | `dti baseline` |
| External benchmark | O*NET measures and the same-instrument O*NET score (RQ2) | `dti gap` |
| Human validation | Human–human vs human–LLM κ and α; LLM added as an extra rater in a multi-rater α | `dti reliability` with forms in `data/human/` — **no valid forms yet** |

**Human validation design.** 200 occupations, stratified by division × whether the description names a digital term
(70 keyword occupations oversampled, 130 others; at least 2 per division stratum), pilot occupations excluded, seed 1;
inclusion probabilities and weights saved. Three coders, blind to the LLM and to each other, using the same rubric and
form (Excel with drop-downs, a status column and a rule that evidence cannot be a number). Three rounds of returned
forms failed the quality checks (copied between coders, patterned scores, no zeros, evidence not from the text) and are
not used; details in RESULTS.md 3.5.

## 6. Pilot (prompt and model choice)

50 occupations, stratified by division (`data/interim/pilot_50_seed0.csv`), 5 runs, two models × two rubric readings.
Strict vs described-task: all-zero share 50% vs 48% (Qwen), cross-model weighted κ 0.83 vs 0.69, Spearman with O*NET 0.59
vs 0.46 → **strict** chosen. Qwen vs Llama: ICC 0.81 vs 0.68, grounded 89% vs 73% → **Qwen** main. The prompt was then
frozen (hash 46a323537a) and the pilot occupations excluded from human validation.

## 7. O*NET benchmark (RQ2)

- **Same-instrument measure:** the identical prompt and model score each O*NET occupation from its O*NET description
  plus core task statements (`data/interim/onet_corpus.csv`), 5 runs, median → `dti_mean_score_onet`.
- **Conventional measures:** Muro et al. (2017) computer score (importance × level of Working with Computers and
  Computers & Electronics knowledge, 0–100), Working with Computers importance, Computers & Electronics knowledge, e-mail
  frequency (Work Context), share of core tasks with digital keywords.
- **Mapping:** O*NET-SOC 2019 → SOC 2010 → ISCO-08 (BLS crosswalk); many-to-many links split equally; aggregated to ISCO-08
  4-digit with **US OEWS employment weights**; ISCO-08 4-digit = NCO-2015 family. 361 families matched; 13 NCO families
  have no ISCO counterpart.
- **DigitalGap_j = DTI_j(O*NET) − DTI_j(NCO-LLM)** on the common 0–4 scale (same instrument) and as percentile-rank
  difference (all measures), summarised by division and skill level.

## 8. PLFS harmonisation

- Files: first-visit person + household files per round (`configs/plfs.yaml` maps each round's raw column names to
  standard names; household variables merged on the household key).
- **Weights:** annual rule `(MULT/100 if NSS == NSC else MULT/200) / No_Qtr` (PLFS documentation).
- **Sample:** usual residents (temporary visitors, serial ≥ 81, dropped); employed in the current weekly status (CWS);
  wage earners = regular salaried and casual labourers; age 15–64; self-employed analysed separately.
- **Wages:** CWS earnings. Regular: monthly earnings / (weekly hours × 4.33). Casual: weekly earnings (sum of both
  activities and all days) / weekly hours. Hourly wage trimmed at the 0.5th and 99.5th percentile within each round.
  Outcome `ln_real_hourly_wage`.
- ⚠ **Price deflation:** no state × sector CPI file was supplied, so wages are **nominal** (deflator = 1; the variable
  name keeps "real" from the design). Common inflation is absorbed by **year-quarter fixed effects** in every model
  from M1 onwards, and state fixed effects absorb permanent state price differences; state-specific inflation is not
  removed. Adding `data/raw/cpi.csv` (state, sector, year, CPI) and re-running `dti plfs-build` + `dti analysis` would
  produce deflated wages; the paper should either do this or state the year-quarter FE approach.
- **Occupation link:** 3-digit occupation code → DTI of the matching NCO-2004 (2017-21) or NCO-2015 (2021-24) group;
  `occ_cluster` = system × group (233 clusters in the main sample). 98.7–99.8% of employed workers matched per round
  (unmatched: armed forces and a few groups without Vol II descriptions).
- **Covariates:** age, age², female, married, rural, education category, social group, religion, state, NIC two-digit
  industry, year-quarter; formality for regular workers = social-security coverage; household size, children under 6
  and household head for the selection equation.
- Analysis sample: 466,095 regular and casual wage earners (≈ 160–196 million weighted per round).

## 9. Econometrics (RQ3–RQ4)

Main equation (abstract):  ln Wageᵢ = α + β·DTI_j(i) + γXᵢ + δ_industry + λ_state + τ_year-quarter + εᵢ

| Step | Specification | Implementation |
|---|---|---|
| FE ladder | M1 year-quarter FE only; M2 + controls, education, social group, religion; M3 + state and NIC2 industry FE; **M4 + occupational division FE (preferred)**; M5 five dimensions instead of the index | `pyfixest` `feols`, PLFS weights, SEs clustered by occupation (`occ_cluster`) |
| Inference check | Wild cluster bootstrap (999 reps, unweighted) | `wildboottest` |
| Coefficient stability | Oster (2019) δ for β = 0 and β at δ = 1, R_max = 1.3 × R² of M4 | `econ.oster_table` |
| Robustness | Unweighted; monthly earnings; regular only; casual only; NCO-2015 rounds; NCO-2004 rounds; NCO-2004 groups with ≥ 75% direct links; DTI quintiles; self-employed (earnings incl. capital returns); second-LLM DTI | `robustness.csv` |
| Selection | Heckman two-step into wage employment, exclusions: children < 6, household size, household head; all, men, women | `heckman.csv` (2nd-step SEs not corrected for the generated regressor) |
| Distribution | Unconditional quantile (RIF) regressions at 10/25/50/75/90; conditional quantile regression on a 100,000 subsample | `rif.csv`, `cqr.csv` |
| Heterogeneity | DTI × female, rural, education band, age band, employment type; formality among regular workers; with M4 FE and with full 3-digit occupation FE (within-occupation identification); M4 by subgroup | `interactions.csv`, `subgroups.csv` |
| Gender gap | Pooled Oaxaca–Blinder (male − female), explained part split by covariate block | `oaxaca.csv` |
| Machine learning | DoubleML partially linear model, 200,000-worker subsample, 5-fold cross-fitting: average partial effect; best linear projection on pre-specified covariates; group average effects (gradient boosting) | `dml_ate.csv`, `dml_blp.csv`, `dml_gate.csv` |
| ML learner comparison | Same estimator with linear regression, cross-validated Lasso, random forest (200 trees, min leaf 20) and gradient boosting (HistGradientBoosting, 200 iterations); **cluster-based cross-fitting and SEs clustered by occupation**; out-of-sample R² of each nuisance model | `dml_learners.csv` |
| Causal forest | `grf` input exported; R not available on the server, not run | `scripts/grf_causal_forest.R` |

## 10. Software

Python 3.10 (server) / 3.12 (laptop): pandas, numpy, scipy, statsmodels, pyfixest, wildboottest, doubleml 0.11.4,
scikit-learn 1.7.2, krippendorff, pydantic, openai (client for the local endpoint), openpyxl, pyarrow; llama.cpp (built
from source, CUDA 12.2); matplotlib for figures; Node `docx` for the Word draft.

## 11. Reproducing

```bash
pip install -e .                                   # inside the repository
dti corpus                                         # NCO-2015 corpus + NCO-2004 link from the coder form
bash scripts/shavak_score.sh qwen14b --rubric configs/rubric_strict.yaml           # GPU, ~26 h
bash scripts/shavak_score.sh llama8b_gguf --rubric configs/rubric_strict.yaml      # ~10 h
bash scripts/shavak_score.sh qwen14b --corpus onet --rubric configs/rubric_strict.yaml   # ~9 h
bash scripts/post_run.sh                           # aggregate, reliability, gap, PLFS merge, wage models, tables
python paper/make_figures.py && python paper/results_doc.py   # figures and RESULTS.md
```

PLFS microdata must be downloaded separately from microdata.gov.in (`docs/PLFS_DATA_NOTES.md`).

## 12. Open items and limitations of the implementation

1. **Human validation** — no valid coder forms yet.
2. **Wages are nominal** (no CPI file); see Section 8.
3. **Causal forest** not run (needs R `grf`).
4. Wage-model choices marked OPEN in `configs/analysis.yaml` await the professors' confirmation (they are the defaults used).
5. Occupation is observed at 3 digits in PLFS, so within-group variation in DTI is not used; groups weight their
   8-digit occupations equally.
