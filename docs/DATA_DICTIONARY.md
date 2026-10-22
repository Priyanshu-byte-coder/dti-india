# Data dictionary — every shared data file and its columns

Paths are as in the repository; in the shared package the same files sit under `04_Data/` (folder names in brackets).
No file contains PLFS microdata (MoSPI terms do not allow redistribution); PLFS-based files hold estimates only.

## Common column meanings

| Column | Meaning |
|---|---|
| `nco2015` | 8-digit NCO-2015 occupation code (e.g. `2512.0100`) |
| `family4`, `group3`, `division` | 4-digit family, 3-digit group, 1-digit division of NCO-2015 (= ISCO-08 structure) |
| `nco2004_g3` | 3-digit NCO-2004 group (used in PLFS 2017-18 to 2020-21) |
| `model_name` | `qwen14b` = Qwen2.5-14B-Instruct (main); `llama8b_gguf` = Llama-3.1-8B-Instruct (second model) |
| `prompt_version` | hash of rubric + prompt: `46a323537a` = strict rubric (main); `8153504f69` = described-task (pilot only) |
| `D1`…`D5` | dimension scores 0–4: basic operation, information processing, communication, specialised tools, problem solving/content (median of 5 runs at occupation level; mean of occupations at family/group level) |
| `D*_sd` | standard deviation of the score across the 5 runs |
| `D*_conf` | mean self-reported confidence 1–3 |
| `D*_ungrounded` | share of runs with a score > 0 whose evidence quote is missing or not found in the description |
| `D*_z` | z-score of the dimension across occupations |
| `dti_z` | **the DTI**: equal-weight sum of the five z-scores, re-standardised (mean 0, SD 1 across occupations) |
| `dti_0_100` | DTI rescaled to 0–100 (min–max) |
| `dti_mean_score` | plain mean of D1–D5 on the 0–4 scale (easiest to read) |
| `q9_overall` | holistic digital intensity 0–10 (median of runs) |
| `q1_detail`, `q10_core`, `q11_india_today` | detail enough (Yes/Partly/No); digital work Core/Supporting/Not relevant; India today More/Same/Less digital than the text (mode of runs) |
| `max_sd` | largest run-to-run SD over the five dimensions (> 0.5 = flagged unstable) |
| `coef`, `se`, `p`, `ci_low`, `ci_high` | regression coefficient on standardised DTI (×100 = log points per SD), clustered SE, p-value, 95% CI |
| `n`, `n_clusters`, `r2`, `r2_within` | observations, occupation clusters, R², within-R² |

## Occupation-level scores (`occupation_scores/`)

| File | Rows | What it is |
|---|---|---|
| `data/interim/nco2015_corpus.csv` | 3,450 | The NCO-2015 occupations as scored: code, title, **full description**, hierarchy, skill level, NCO-2004 concordance, word count |
| `data/interim/nco2015_to_nco2004.csv` | 3,450 | Link to NCO-2004: `link` = direct (Vol I concordance), family_mode, group_mode, none |
| `data/processed/dti_occupation_nco2015.csv` | 6,900 | **Main index**: one row per occupation × model (Qwen and Llama), all columns above plus title and hierarchy |
| `data/processed/dti_family4_nco2015.csv` | 746 | DTI per 4-digit family × model; `n_occupations`, `dti_sd_within` (spread inside the family) |
| `data/processed/dti_group3_nco2015.csv` | 244 | DTI per 3-digit NCO-2015 group × model (**merged onto PLFS 2021-22 to 2023-24**) |
| `data/processed/dti_group3_nco2004.csv` | 222 | DTI per 3-digit NCO-2004 group × model (**merged onto PLFS 2017-18 to 2020-21**); `share_direct_link` |
| `data/processed/keyword_baseline_nco2015.csv` | 3,450 | Keyword benchmark: `kw_share` share of description sentences with a digital keyword, `kw_any`, keyword hits per dimension |
| `data/processed/llm_runs_long.csv` | 34,500 | Every individual run (occupation × run × model), scores, confidence and evidence status (`exact/close/partial/not_found/empty`) |

## Raw LLM outputs (`llm_raw_outputs/`)

`data/llm/<model>/<prompt_version>/<corpus>.jsonl` — one JSON line per call, exactly as returned: `code`, `run`, `seed`,
`temperature`, `timestamp` (UTC), `ok`, `coding` (q1, dimensions with rationale, evidence, score, confidence, q9–q12), `raw`
(model text), `usage` (prompt/completion tokens), `errors`. Files: Qwen NCO (17,250), Llama NCO (17,250), Qwen O\*NET (4,615),
and the two described-task pilots (250 each).

## O\*NET side (`onet/`)

| File | What it is |
|---|---|
| `data/interim/onet_corpus.csv` | 923 O\*NET occupations as scored: O\*NET-SOC code, title, description + core tasks, number of tasks |
| `data/interim/onet_to_isco08.csv` | O\*NET-SOC 2019 → ISCO-08 links with split weights (via SOC 2010, BLS crosswalk) |
| `data/processed/dti_llm_onet_onetsoc.csv` | LLM scores of each O\*NET occupation (same columns as the NCO index) |
| `data/processed/dti_llm_onet_isco4.csv` | Same, aggregated to ISCO-08 4-digit (= NCO family) with US employment weights (`us_emp_weight`) |
| `data/processed/onet_measures_isco4.csv` / `_onetsoc.csv` | Conventional O\*NET measures: `kw_share_core` (digital-keyword share of core tasks), `wa_computers_im/lv` (Working with Computers importance/level), `kn_computers_im/lv` (Computers & Electronics knowledge), `cx_email` (e-mail frequency), `muro_0_100` (Muro et al. score) |

## Reliability (`reliability/`)

| File | What it is |
|---|---|
| `reports/pilot_comparison.csv` | Pilot: per model × rubric — all-zero share, mean score, median ICC and α across runs, grounded share, Spearman with Q9 and with O\*NET |
| `reports/pilot_agreement.csv` | Pilot: cross-model and cross-rubric correlations |
| `reports/stability_runs.csv` | Full run: per model × dimension — ICC(2,1), ICC(2,k), ordinal α, share of occupations with 5 identical runs, mean run SD |
| `reports/cross_model.csv` | Qwen vs Llama per dimension and Q9: exact, within-1, weighted κ, Spearman, α, mean difference |
| `reports/q9_vs_equal_weight.csv` | Spearman between the equal-weight dimension mean and the holistic Q9 |
| `reports/unstable_occupations.csv` | Occupations with run SD > 0.5 on any dimension (for manual review) |
| `data/interim/validation_200_seed1.csv` | Human-validation sample: 200 occupations, stratum, inclusion probability, weight |

## RQ2 gap (`rq2_gap/`, `reports/gap/`)

| File | What it is |
|---|---|
| `correlations.csv` | Family-level Pearson and Spearman between the NCO-LLM DTI and each O\*NET measure |
| `gap_dti_mean_score_llm.csv` | Per family: NCO score (`nco`), O\*NET same-instrument score (`onet`), percentiles, `gap_raw` (O\*NET − NCO, 0–4), `gap_pct` (percentile difference), division, skill level, title |
| `gap_dti_mean_score_llm_by_division.csv`, `…_by_skill_level.csv` | Mean, SD and count of the gaps by division / skill level |
| `gap_muro_0_100*.csv`, `gap_wa_computers_im*.csv` | Same, against the conventional O\*NET measures (percentile gaps only) |
| `unmatched_codes.json` | NCO families with no ISCO match (`nco_only`) and ISCO groups with no NCO family (`onet_only`) |

## Wage results (`wage_results/`)

Three folders with identical file names: `reports/econ_llm/` (Qwen DTI, main), `reports/econ_llm_llama8b_gguf/` (Llama DTI,
robustness subset), `reports/econ_onet/` (O\*NET-transferred DTI).

| File | What it is |
|---|---|
| `sample_summary.csv` | Per PLFS round: occupation system, workers, occupation groups, weighted millions, shares female / rural / casual, mean ln wage |
| `baseline.csv` | Specification ladder M1–M5 (`model`), terms `dti_std` or `D*_std` |
| `oster.csv` | Oster (2019): β and R² without and with controls, R_max, δ for β = 0, β at δ = 1 |
| `robustness.csv` | Robustness specifications (`model` names them; `note` says e.g. "p from wild cluster boot"); quintile rows use terms `dti_q2…q5` |
| `heckman.csv` | Selection-corrected M4: all / men / women; `imr` = inverse Mills ratio; exclusion restrictions and their first-stage p |
| `rif.csv`, `cqr.csv` | Unconditional (RIF) and conditional quantile coefficients by `quantile` |
| `interactions.csv` | DTI × group terms (`dti_x_…`), with M4 FE and with full occupation FE; formality among regular workers |
| `subgroups.csv` | M4 estimated within each group (`group_var`, `group_level`) |
| `oaxaca.csv` | Gender-gap decomposition components (log points): total, explained, unexplained, explained by block |
| `dml_ate.csv`, `dml_blp.csv`, `dml_gate.csv` | DoubleML (gradient boosting): average effect; best linear projection on covariates; group average effects (SEs treat workers as independent — use `dml_learners.csv` for inference) |
| `dml_learners.csv` | DoubleML average effect for linear / lasso / random_forest / gradient_boosting: `coef`, `se_cluster`, CI, out-of-sample RMSE and R² for the wage (`_wage`) and DTI (`_dti`) predictions, `n`, `n_clusters` |

## Run logs (`run_logs/`)

| File | What it is |
|---|---|
| `reports/run_log.csv` | One row per LLM call (39,615): UTC timestamp, model, prompt version, corpus, code, run, ok, prompt and completion tokens |
| `paper/figures/run_segments.csv` | Each scoring job: model, rubric, corpus, start, end (IST), calls, tokens, phase (pilot / full run), hours |
| `docs/PLFS_DATA_NOTES.md` | PLFS round-by-round notes (variables, weights, quirks), not data |

## Not included, on purpose

- PLFS microdata and any worker-level file (MoSPI terms; e.g. `plfs_*.parquet`, `grf_input.csv`).
- Human coder forms received so far (personal data of the coders; all failed the quality checks).
- Server credentials of any kind.
