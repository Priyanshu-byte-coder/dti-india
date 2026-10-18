# Decision log

Decisions that shape the measure or the estimates, with who decided and when. Open
items are listed at the end; the full question list is in
[DTI_Implementation_Plan_and_Questions.md](DTI_Implementation_Plan_and_Questions.md).

## Decided

| Date | Decision | Source | Effect in code |
|---|---|---|---|
| 2026-10-18 | The LLM scores **only the NCO text**; no external sources (no web, O\*NET or QP text added to the prompt). | Professors (answer to Q1 of the meeting list) | `configs/rubric.yaml` rule 1; prompt contains title + NCO description only |
| 2026-10-18 | Use **older PLFS rounds as well** (before July 2021, coded in NCO-2004), with a code conversion. | Professors (answer to Q5) | `src/dti/crosswalk.py`; `dti aggregate` writes `dti_group3_nco2004.csv` next to the NCO-2015 group file |
| 2026-10-18 | Score at the **8-digit NCO-2015 occupation** level (3,450 occupations, the same rows the human coders get), then aggregate up. | Implementation default | `dti corpus` builds the corpus from the coder form |
| 2026-10-18 | Occupations within a family/group are **weighted equally** when aggregating (no employment counts exist below 3-digit). Mean by default, median as robustness. | Implementation default | `dti aggregate --how mean|median` |
| 2026-10-18 | DTI = equal-weight sum of the five z-scored dimensions, re-standardised (abstract eq. 1). | Abstract | `configs/rubric.yaml` → `aggregation.weights` |

| 2026-10-18 | O\*NET benchmark uses O\*NET 31.0. The main O\*NET measure is the **same LLM prompt** run on O\*NET text (description + core tasks), so the gap reflects the texts, not the method. Conventional measures (keyword share of core tasks, Working with Computers, Computers and Electronics, e-mail, Muro-style score) are reported alongside. | Implementation default | `src/dti/onet.py`, `src/dti/gap.py` |
| 2026-10-18 | O\*NET → NCO path: O\*NET-SOC 2019 → 2010 (O\*NET crosswalk) → SOC 2010 → ISCO-08 (BLS) = NCO-2015 family; US employment weights (OEWS), split equally across many-to-many links. | Implementation default | `onet_isco_links` |
| 2026-10-18 | Wage-model defaults follow the plan's proposals (hourly wage, regular + casual, 15–64, division FE preferred, occupation-clustered SEs, PLFS weights). Each is marked OPEN in `configs/analysis.yaml` until confirmed. | Plan proposals | `configs/analysis.yaml` |

## NCO-2015 → NCO-2004 link (for pre-July-2021 PLFS)

The coder form carries an NCO-2004 concordance code (NCO-2015 Vol I) for 2,657 of 3,450
occupations. The other 793 are occupations new in 2015. They are linked to the most
common NCO-2004 code among their siblings:

| Link type | Occupations | Rule |
|---|---|---|
| direct | 2,657 | NCO-2004 code given in NCO-2015 Vol I |
| family_mode | 759 | most common NCO-2004 code in the same NCO-2015 family (4-digit) |
| group_mode | 32 | most common NCO-2004 code in the same NCO-2015 group (3-digit) |
| none | 2 | no linked sibling; dropped from the NCO-2004 file |

Result: 112 NCO-2004 3-digit groups. `share_direct_link` in the output shows how much of
each group rests on direct links; a robustness check can keep direct links only.

To verify on the PLFS side once data is in: every NCO-2004 3-digit code observed in
PLFS 2017-18 to 2020-21 should appear in `dti_group3_nco2004.csv`.

## Open — needs professors' input

1. **Digital vocabulary in NCO text is sparse.** Only 5.7% of the 3,450 descriptions use
   any core digital term (computer, software, internet, online, e-mail, programming,
   database, spreadsheet, CNC, CAD). By division: Professionals 16.5%, Clerks 7.6%,
   Managers 7.8%, Craft 2.4%, Machine operators 0.6%, Agriculture 0%. With "text only,
   silent → 0", most occupations will score 0 and the DTI will have little variation
   for the wage regressions. Question: does "text only" mean
   (a) score only digital work the text **names**, or
   (b) score tasks the text **describes** that are normally done digitally (e.g.
   "maintains accounts and prepares statements"), still with no outside sources?
   Option (b) needs a rubric change; the pilot can run both and compare.
2. **Q11 (own knowledge of India today)** — keep for coders and LLM? It does not feed
   the DTI; it measures how dated the text is.
3. **Models** — depends on the Nirma GPU spec (memory per GPU, number of GPUs).
4. **Temperature for repeated runs** — currently 0.7 so runs can differ and stability is
   a real test. Temperature 0 would make runs near-identical (stability trivially high).
5. **NCO-2004 link for new occupations** — accept the sibling-mode rule above, or use an
   official NCO-2004/2015 concordance table if the professors have one.
6. **Wage-model choices** marked OPEN in `configs/analysis.yaml` (A1–A13 of the meeting list):
   outcome, sample, age band, occupation controls, clustering, weights, Heckman exclusion
   restrictions, heterogeneity list.
7. **Pooling NCO-2004 and NCO-2015 rounds**: the DTI is matched within each system, then
   standardised across all workers in the pooled sample. Robustness reruns each system
   separately (`robustness.csv`).
