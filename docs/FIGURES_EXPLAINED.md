# Figures — what each one shows and what it means

19 figures in `paper/figures/` (PNG 300 dpi for Word/slides, PDF vector for LaTeX). Regenerate with
`python paper/make_figures.py`; every figure is drawn from the result files named under it.
Colours are the same in every figure: **blue = India-specific DTI from Qwen2.5-14B (main)**,
**aqua/green = second LLM (Llama-3.1-8B)**, **orange = O\*NET-transferred measure**. Coefficients are in
**log points per one standard deviation of DTI** (≈ % difference in hourly wages); whiskers are 95% confidence intervals.

Suggested use: **Paper** = figure for the main text; **Appendix** = supplementary; **Slides** = presentation only.

---

## A. How the AI scoring was run (Figures 1–4)

### Figure 1 — `fig01_run_timeline`: timeline of every scoring job
- **Shows:** each LLM job on PARAM Shavak as a bar from its first to its last completed call, 20–22 Oct 2026 (IST).
  Lighter bars are the four pilot jobs (50 occupations × 5 runs each); the three solid bars are the full runs.
- **Read:** Qwen scored all NCO occupations in 26.5 h, then Llama in 9.8 h, then Qwen scored the O\*NET occupations in 9.3 h,
  back to back. "+250 from pilot" means the 250 strict-rubric pilot calls were reused in the full run (same prompt, same seeds).
- **Takeaway:** about 46 hours of continuous GPU scoring, 39,615 LLM calls in total, none failed.
- **Use:** Appendix (computational details) / Slides.

### Figure 2 — `fig02_run_progress`: cumulative progress of the full runs
- **Shows:** completed calls against hours since each job started.
- **Read:** straight lines = constant speed; steeper = faster. Llama (8B) is about 2.7× faster than Qwen (14B); Qwen on O\*NET
  text is slower than on NCO text because O\*NET prompts are longer (description + core tasks).
- **Takeaway:** the runs were stable from start to finish (no stalls, no restarts).
- **Use:** Appendix / Slides.

### Figure 3 — `fig03_run_throughput`: calls per hour over time
- **Shows:** completed calls per hour in 30-minute bins; medians in the legend (Qwen 644/h, Llama 1,742/h, Qwen on O\*NET 495/h).
- **Takeaway:** a 16 GB, 2016-era GPU is enough to score the entire Indian occupational classification five times
  in about a day with an open model — the method is cheap and reproducible without commercial APIs.
- **Use:** Appendix; useful for a "feasibility / cost" sentence in the paper.

### Figure 4 — `fig04_run_tokens`: tokens processed
- **Shows:** input (prompt) and output (generated) tokens per full run: Qwen NCO 30.4 M in / 4.4 M out; Llama NCO 30.5 M / 3.8 M;
  Qwen O\*NET 9.1 M / 1.5 M (about 80 M tokens in total).
- **Takeaway:** input dominates because every call carries the full rubric and a worked example (≈ 1,800 tokens) for a short
  occupation description; the output is a compact JSON (≈ 220–320 tokens).
- **Use:** Appendix.

## B. RQ1 — is the LLM a reliable instrument? (Figures 5–9)

### Figure 5 — `fig05_pilot`: pilot comparison
- **Shows:** for 50 occupations, two models × two readings of "text only" (solid = strict, hatched = described-task):
  share of occupations scored 0 on every dimension, median run-to-run ICC, share of non-zero scores grounded in a quote.
- **Read:** the broader described-task reading barely reduces the all-zero share (Qwen 50% → 48%) and lowers stability;
  Qwen beats Llama on stability (0.81 vs 0.68) and grounding (89% vs 73%).
- **Takeaway:** why the paper uses the **strict rubric** and **Qwen as the main model**.
- **Use:** Appendix (design choice) or one sentence in Methods.

### Figure 6 — `fig06_stability`: run-to-run stability by dimension
- **Shows:** ICC(2,1) across the five repeated runs for all 3,450 occupations, per dimension, for both models. Dashed line 0.75 = "good".
- **Read:** Qwen 0.70–0.84 (good for information processing, specialised tools, problem solving; moderate for basic operation
  and communication); Llama lower everywhere (0.57–0.75).
- **Takeaway:** asked five times at temperature 0.7, the main model gives largely the same scores → the measure is not noise.
- **Use:** **Paper**, Section 6.1.

### Figure 7 — `fig07_dti_by_division`: digital intensity by NCO division
- **Shows:** left, mean dimension score (0–4) by division (number of occupations in brackets); right, share of occupations scoring
  0 on every dimension.
- **Read:** professionals 1.05, technicians 0.65, clerks 0.59 … craft 0.20, elementary 0.06, agriculture 0.05; 88–89% of
  elementary and agricultural occupations are all-zero, 31% of professionals.
- **Takeaway:** the ordering is what labour economists would expect (face validity), and it shows how rarely the NCO-2015 texts
  mention digital work outside white-collar jobs.
- **Use:** **Paper**, Section 6.1 (descriptive result of the index).

### Figure 8 — `fig08_cross_model`: two LLMs, same occupation groups
- **Shows:** DTI (z-score) of each of the 122 NCO-2015 3-digit groups from Qwen (x) and Llama (y); dashed = equality.
- **Read:** points hug the diagonal; Spearman ρ = **0.91**.
- **Takeaway:** at the level used in the PLFS wage models, an independently trained model from another developer ranks
  occupation groups almost identically — the wage results do not depend on the choice of LLM.
- **Use:** **Paper**, Section 6.1 (strongest RQ1 evidence in the absence of human validation).

### Figure 9 — `fig09_cross_model_dims`: agreement per dimension
- **Shows:** quadratic-weighted κ between Qwen and Llama for each dimension and the holistic score, with exact agreement.
- **Read:** κ 0.77–0.78 for information processing and problem solving/content; 0.62 specialised tools; 0.47–0.51 basic
  operation and communication. Communication has 95% exact agreement but low κ because almost everything is 0 (κ penalises that).
- **Takeaway:** occupation-level agreement is moderate-to-good; aggregation to groups (Figure 8) removes most disagreement.
- **Use:** Appendix.

## C. RQ2 — India-specific vs O\*NET-transferred intensity (Figures 10–11)

### Figure 10 — `fig10_rq2_scatter`: same AI, Indian vs US descriptions
- **Shows:** each dot is an NCO-2015 family (361). x = mean score when the AI reads the Indian NCO description; y = mean score
  when the same AI, with the same rubric, reads the matching US O\*NET descriptions.
- **Read:** most dots lie above the dashed equality line; the ranking still lines up (Spearman ρ = **0.68**). Means: NCO 0.47 vs O\*NET 1.18.
- **Takeaway:** the two sources agree on *which* occupations are digital, but US descriptions of the same occupations read about
  **2.5 times as digital**. Many families that score 0 from the Indian text score 1–2.5 from the US text.
- **Use:** **Paper**, Section 6.2 (the central RQ2 figure).

### Figure 11 — `fig11_rq2_gap_division`: where the gap is largest
- **Shows:** mean DigitalGap (O\*NET score − NCO score, 0–4 scale) by NCO division.
- **Read:** managers +1.40, professionals +1.03, technicians, skilled agriculture and clerks ≈ +0.9; craft, operators, service ≈ +0.3;
  elementary +0.02.
- **Takeaway:** transferring O\*NET overstates digital intensity most for white-collar and managerial work in India.
  Caveat for the text: the gap may reflect real differences in Indian jobs *or* how the 2015 NCO texts were written — the
  comparison cannot separate the two.
- **Use:** **Paper**, Section 6.2.

## D. RQ3 — the wage premium (Figures 12–13, 19)

### Figure 12 — `fig12_premium_ladder`: the conditional digital occupational premium
- **Shows:** coefficient on standardised DTI in ln hourly wage as controls are added (M1 → M4), for the three measures.
- **Read:** no controls 27.5 (Qwen); adding individual characteristics → 8.5; state, industry and time FE → 6.3; comparing occupations
  within the same broad division (**M4, preferred**) → **4.1** (95% CI ≈ 1.5–6.7). Llama 2.2, O\*NET 5.7.
- **Takeaway:** most of the raw gap reflects who works in digital occupations; a modest premium (≈ 4%) remains within divisions.
  It is a conditional association, not a causal return (Oster δ = 0.34).
- **Use:** **Paper**, Section 6.3 (headline figure).

### Figure 13 — `fig13_robustness`: robustness of the premium
- **Shows:** preferred estimate and checks: unweighted, monthly earnings, regular only, casual only, NCO-2015 rounds, NCO-2004
  rounds, direct NCO-2004 links only, self-employed.
- **Read:** the Qwen estimate stays positive and similar except for casual workers (≈ 0) and the self-employed (≈ 0); weaker in
  the pre-2021 NCO-2004 rounds (3.1, 10% level). Llama estimates are smaller throughout.
- **Takeaway:** the premium is robust for wage employees with regular jobs; it does not exist for casual labour.
- **Use:** **Paper** or Appendix (with Table 4).

### Figure 19 — `fig19_plfs_sample`: PLFS analysis sample
- **Shows:** wage earners aged 15–64 per round (labels: sample size and weighted population in millions); light = NCO-2004 rounds
  linked through the concordance, dark = NCO-2015 rounds.
- **Takeaway:** 466,095 workers over seven rounds, 61–71 thousand per round, ≈ 160–196 million workers represented each year.
- **Use:** Appendix / Data section.

## E. RQ4 — who gains? (Figures 14–18)

### Figure 14 — `fig14_rif_quantiles`: premium across the wage distribution
- **Shows:** unconditional quantile (RIF) estimates at the 10th–90th wage percentiles with 95% bands.
- **Read:** around zero below the median (Qwen −1.7 at p10), 6.2 at p75, **21.3 at p90** (O\*NET similar: 19.8).
- **Takeaway:** occupational digital intensity pays mainly at the top of the wage distribution — it widens, not narrows, wage inequality.
- **Use:** **Paper**, Section 6.4.

### Figure 15 — `fig15_subgroups`: premium by group
- **Shows:** the preferred model estimated separately for each group, three measures.
- **Read:** education — none for up-to-primary, positive for secondary and tertiary; formality — none for regular workers
  without social security, positive with it; none for casual workers; women ≥ men; rural ≥ urban when estimated separately.
- **Takeaway:** the premium accrues to educated, formally employed workers — the abstract's **digital-returns gap**.
- **Use:** **Paper**, Section 6.4.

### Figure 16 — `fig16_interactions`: differences within the same occupation
- **Shows:** DTI × group interaction terms from models with full 3-digit occupation fixed effects (so comparisons are between workers
  in the same occupation).
- **Read:** tertiary vs up-to-primary +11.5 (O\*NET +18.0); middle/secondary +8.6; formal vs informal +4.0 (O\*NET +11.0); women +3.7;
  rural −3.0; casual −5.9.
- **Takeaway:** even inside the same occupation, educated and formal workers gain more from its digital intensity; rural workers
  gain less (opposite of Figure 15 — report rural–urban as inconclusive).
- **Use:** **Paper**, Section 6.4.

### Figure 17 — `fig17_oaxaca`: gender wage gap decomposition
- **Shows:** the 31.7-log-point male–female gap split into parts explained by DTI, education, industry, age, state, occupation
  division, and the unexplained part.
- **Read:** DTI explains 0.5 points (O\*NET −0.1); industry 5.9; most of the gap (28.0) is unexplained.
- **Takeaway:** women are not paid less because they work in less digital occupations; occupational DTI is not a channel of the
  gender gap, even though women's premium is larger.
- **Use:** **Paper**, Section 6.4 (gender paragraph).

### Figure 18 — `fig18_dml_learners`: machine-learning check with four learners
- **Shows:** left, the double/debiased ML average effect with linear regression, Lasso, random forest and gradient boosting
  (standard errors clustered by occupation); right, each learner's out-of-sample R² for predicting wages (higher = better adjustment).
- **Read:** India DTI 2.6–4.4 across learners; gradient boosting fits best (R² 0.594) and gives **3.3 (p = 0.02)**. O\*NET DTI 3.4–6.9,
  and its best learner (3.4) is not significant.
- **Takeaway:** the India-specific result does not hinge on the choice of ML model (the professors' question); the O\*NET premium
  shrinks once controls enter flexibly.
- **Use:** **Paper** (Section 6.4 or robustness) or Appendix with Table 11.

## F. Files alongside the figures

- `figures_index.md` — list with one-line captions and source files.
- `run_segments.csv` — start, end, duration, calls and tokens of every scoring job (the data behind Figure 1).
