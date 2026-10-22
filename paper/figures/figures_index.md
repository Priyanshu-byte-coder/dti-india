# Figures

PNG (300 dpi) for Word/slides, PDF (vector) for LaTeX. Regenerate: `python paper/make_figures.py`.
Colours are fixed by measure: blue = NCO-LLM (Qwen, main), aqua = second LLM (Llama), orange = O*NET.

| File | What it shows | Data |
|---|---|---|
| `fig01_run_timeline` | Timeline of every LLM scoring job (pilot runs lighter). Each bar runs from the first to the last completed call; label = calls and wall-clock hours. | `reports/run_log.csv` |
| `fig02_run_progress` | Cumulative completed calls for the three full runs; 3,450 NCO occupations × 5 runs per model and 923 O*NET occupations × 5 runs. | `reports/run_log.csv` |
| `fig03_run_throughput` | Calls completed per hour. The 8B model is about 2.5× faster than the 14B model; O*NET prompts are longer (core tasks), so slower. | `reports/run_log.csv` |
| `fig04_run_tokens` | Input and output tokens per full run (llama.cpp usage counts). | `reports/run_log.csv` |
| `fig05_pilot` | Pilot comparison used to choose the strict rubric and Qwen as the main instrument. | `reports/pilot_comparison.csv` |
| `fig06_stability` | Intra-model stability: ICC(2,1) across the five runs at temperature 0.7, per dimension and model. | `reports/stability_runs.csv` |
| `fig07_dti_by_division` | Mean score and all-zero share by NCO division (number of 8-digit occupations in brackets). | `data/processed/dti_occupation_nco2015.csv` |
| `fig08_cross_model` | Cross-model agreement at the 3-digit group level used in the PLFS wage models; dashed = equality. | `data/processed/dti_group3_nco2015.csv` |
| `fig09_cross_model_dims` | Occupation-level agreement between the two LLMs per dimension. | `reports/cross_model.csv` |
| `fig10_rq2_scatter` | Each dot is an NCO-2015 family; points above the dashed line are read as more digital in O*NET than in NCO. | `reports/gap/gap_dti_mean_score_llm.csv` |
| `fig11_rq2_gap_division` | Mean family-level DigitalGap by NCO division (same LLM and rubric on both texts). | `reports/gap/gap_dti_mean_score_llm_by_division.csv` |
| `fig12_premium_ladder` | Coefficient on standardised DTI in ln real hourly wage, regular and casual workers 15–64, PLFS weights, SEs clustered by occupation. | `reports/econ_llm*/baseline.csv, reports/econ_onet/baseline.csv` |
| `fig13_robustness` | Preferred specification and robustness checks for the three DTI measures. | `reports/econ_*/robustness.csv` |
| `fig14_rif_quantiles` | RIF (unconditional quantile) regressions with 95% CI bands. | `reports/econ_llm/rif.csv, reports/econ_onet/rif.csv` |
| `fig15_subgroups` | Preferred specification estimated separately for each group. | `reports/econ_*/subgroups.csv` |
| `fig16_interactions` | Interaction terms from models with full 3-digit occupation fixed effects. | `reports/econ_llm/interactions.csv` |
| `fig17_oaxaca` | Pooled Oaxaca–Blinder decomposition of the gender gap in ln hourly wages (selected components). | `reports/econ_llm/oaxaca.csv` |
| `fig18_dml_learners` | DoubleML partially linear model, 200,000-worker subsample, cluster-based cross-fitting; higher R² = better learner. | `reports/econ_*/dml_learners.csv` |
| `fig19_plfs_sample` | Regular and casual wage earners aged 15–64 per PLFS round. | `reports/econ_llm/sample_summary.csv` |

`run_segments.csv`: start, end, duration, calls and tokens of every scoring job (from `reports/run_log.csv`).
