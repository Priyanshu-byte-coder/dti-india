"""Sample construction and descriptive statistics as a paper-ready section (Markdown), from
reports/sample/ (written by scripts/sample_flow.py).

    python paper/sample_doc.py  ->  paper/sample_section.md   (Word: node paper/build_docx.js paper/sample_section.md "" out.docx)
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "reports" / "sample"
flow = pd.read_csv(S / "sample_flow.csv")
pooled = pd.read_csv(S / "descriptives_pooled.csv")
byr = pd.read_csv(S / "descriptives_by_round.csv")
byg = pd.read_csv(S / "descriptives_by_group.csv")
rounds = [c for c in flow.columns if c[:2] == "20"]


def n(x):
    return "—" if pd.isna(x) else f"{int(x):,}"


def md(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
                     + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


final = flow.iloc[-1]
first = flow.iloc[0]
P = []
A = P.append
A("# Descriptive Statistics and Sample Construction")
A("")
A("*Generated from the PLFS microdata by `scripts/sample_flow.py` and `paper/sample_doc.py`; all counts are unweighted person "
  "records, all means are weighted with the PLFS annual weights.*")
A("")
A("## Sample construction")
A("")
A(f"The analysis uses the first-visit person files of the seven annual PLFS rounds from July 2017–June 2018 to July 2023–June 2024 "
  f"({n(first['Total'])} person records), merged with the first-visit household files. Table S1 reports the number of observations "
  "retained after each filtering step. Temporary visitors (person serial number 81 or higher, recorded from 2020-21) are dropped. "
  "Restricting to the working-age population aged 15–64 keeps 70% of records; of these, 49% are employed in the current weekly status (CWS). "
  "The wage analysis is limited to wage employees — regular salaried workers and casual labourers — because the self-employed report "
  "earnings that include returns to capital; they are analysed separately as a robustness check. Wage employees with zero or missing "
  "earnings or hours are dropped, and hourly wages are trimmed at the 0.5th and 99.5th percentiles within each round. Workers whose "
  "three-digit occupation code cannot be matched to a DTI score (mainly the armed forces and a few occupation groups without NCO "
  "descriptions) are excluded, as are 32 observations with missing covariates in the preferred specification. "
  f"The final analytical sample comprises **{n(final['Total'])} wage employees** in 233 occupation groups (111 NCO-2004 groups in "
  "2017-18 to 2020-21 and 122 NCO-2015 groups in 2021-22 to 2023-24), representing 160–196 million workers per year.")
A("")
A("## Table S1. Sample construction: observations retained after each filter")
A("")
SHORT = ["1. All person records", "2. Usual members only", "3. Aged 15–64", "4. Employed (CWS)", "5. Regular or casual wage employee",
         "6. Valid earnings and hours", "7. Wage outliers trimmed", "8. Occupation matched to DTI", "9. Positive weight",
         "10. Complete covariates (M4)"]
flow["stage"] = SHORT[:len(flow)]
rows = [[r.stage, n(r.Total), "—" if pd.isna(r.dropped_at_stage) else n(r.dropped_at_stage),
         "—" if pd.isna(r.share_of_previous) else f"{100 * r.share_of_previous:.1f}%",
         f"{100 * r.Total / flow.iloc[0].Total:.1f}%"] for _, r in flow.iterrows()]
A("Panel A. All rounds pooled")
A("")
A(md(["Filter", "Observations kept", "Dropped at this step", "Kept (% of previous step)", "Kept (% of all records)"], rows))
A("")
A("Panel B. Observations kept, by PLFS round")
A("")
rows = [[r.stage.split(". ", 1)[0]] + [n(r[c]) for c in rounds] for _, r in flow.iterrows()]
A(md(["Step"] + rounds, rows))
A("")
A("Notes: unweighted person records. Step 1: all records in the first-visit person files. Step 5: regular salaried or casual labour in the CWS. Step 6: positive earnings and hours, so an hourly wage can be computed. Step 9: positive survey weight. Step 2 removes temporary visitors (serial number ≥ 81), recorded from the 2020-21 round. Step 4 "
  "uses the current weekly status (principal activity in the reference week). Step 7: the trimming percentiles are computed within each round. "
  "Step 8: rounds up to 2020-21 code occupation in NCO-2004 and are linked to the NCO-2015-based DTI through the NCO-2015 → NCO-2004 "
  "concordance; unmatched codes are mainly armed forces (NCO-2004 010/099) and a few groups without Vol II descriptions. "
  "Step 10 equals the number of observations in the preferred regression (M4).")
A("")
A("## Table S2. Descriptive statistics of the analytical sample (pooled 2017-18 to 2023-24)")
A("")
LABEL_OVERRIDE = {"social_group_1": "Social group: Scheduled Tribe", "social_group_2": "Social group: Scheduled Caste",
                  "social_group_3": "Social group: Other Backward Class", "social_group_9": "Social group: Others"}
order = ["ln_real_hourly_wage", "hourly_wage_nominal", "monthly_earnings_nominal", "hours_week", "dti_mean_score_0_4", "dti_z",
         "D1", "D2", "D3", "D4", "D5", "age", "female", "married", "rural", "edu_up_to_primary", "edu_middle_secondary",
         "edu_tertiary", "social_group_1", "social_group_2", "social_group_3", "social_group_9", "regular", "casual", "formal_ss",
         "hh_size", "nco2015_round"]
pi = pooled.set_index("variable")
binary = {"female", "married", "rural", "edu_up_to_primary", "edu_middle_secondary", "edu_tertiary", "regular", "casual",
          "formal_ss", "nco2015_round", "social_group_1", "social_group_2", "social_group_3", "social_group_9"}
rows = []
for v in order:
    if v not in pi.index:
        continue
    r = pi.loc[v]
    lab = LABEL_OVERRIDE.get(v, r["label"])
    if v in binary:
        rows.append([lab, f"{100 * r.mean_weighted:.1f}%", "", "", "", n(r.n)])
    else:
        dec = 0 if "earnings" in v else 2
        rows.append([lab, f"{r.mean_weighted:,.{dec}f}", f"{r.sd_weighted:,.{dec}f}", f"{r['median']:,.{dec}f}",
                     f"{r['min']:,.{dec}f} – {r['max']:,.{dec}f}", n(r.n)])
A(md(["Variable", "Mean / share", "SD", "Median", "Min – max", "N"], rows))
A("")
A("Notes: means, shares and SDs weighted with PLFS annual weights; median and range unweighted. Wages and earnings are nominal rupees "
  "(no CPI deflator applied; year-quarter fixed effects absorb common inflation in the regressions). Hourly wage = monthly earnings / "
  "(weekly hours × 4.33) for regular workers and weekly earnings / weekly hours for casual workers. DTI = Digital Task Intensity of the "
  "worker's 3-digit occupation from the LLM coding of NCO-2015 texts (Qwen2.5-14B, strict rubric); dimensions on a 0–4 scale; "
  "the regressor is DTI standardised across workers (mean 0, SD 1). Social-security coverage is defined for regular salaried workers only.")
A("")
A("## Table S3. Key characteristics by PLFS round")
A("")
rows = [[r["round"], r.occ_system.upper().replace("NCO", "NCO-"), n(r.n), f"{r.weighted_millions:.1f}", int(r.occ_groups),
         f"{r.hourly_wage_nominal:.1f}", f"{r.ln_real_hourly_wage:.2f}", f"{r.hours_week:.1f}", f"{r.dti_mean_score_0_4:.2f}",
         f"{100 * r.female:.1f}%", f"{100 * r.rural:.1f}%", f"{100 * r.edu_tertiary:.1f}%", f"{100 * r.casual:.1f}%",
         f"{100 * r.formal_ss:.1f}%"] for _, r in byr.iterrows()]
A(md(["Round", "Occupation code", "N", "Weighted (million)", "Occ. groups", "Hourly wage (Rs.)", "Log wage", "Hours/week",
      "DTI (0–4)", "Female", "Rural", "Tertiary", "Casual", "Soc. security (regular)"], rows))
A("")
A("## Table S4. Key characteristics by group")
A("")
names = {"casual": "Casual labour", "regular": "Regular salaried", 0: "Men", 1: "Women", "0": "Men", "1": "Women",
         "middle_secondary": "Middle / secondary", "tertiary": "Tertiary", "up_to_primary": "Up to primary"}
rows = []
for _, r in byg.iterrows():
    g = r["group"]
    if r["by"] == "sex":
        lab = "Men" if str(g) in ("0", "0.0") else "Women"
    elif r["by"] == "sector":
        lab = "Urban" if str(g) in ("0", "0.0") else "Rural"
    else:
        lab = names.get(g, g)
    rows.append([r["by"].capitalize(), lab, n(r.n), f"{100 * r.weighted_share:.1f}%", f"{r.hourly_wage_nominal:.1f}",
                 f"{r.dti_mean_score_0_4:.2f}", f"{100 * r.female:.1f}%",
                 f"{100 * r.rural:.1f}%", f"{100 * r.edu_tertiary:.1f}%", "—" if pd.isna(r.formal_ss) else f"{100 * r.formal_ss:.1f}%"])
A(md(["By", "Group", "N", "Weighted share", "Hourly wage (Rs.)", "DTI (0–4)", "Female", "Rural", "Tertiary",
      "Soc. security (regular)"], rows))
A("")
A("## What the tables show")
A("")
pr = pi.loc
A(f"- **Who is in the sample.** Wage employees are about half regular salaried ({100 * pr['regular'].mean_weighted:.0f}%) and half casual "
  f"labourers; {100 * pr['female'].mean_weighted:.0f}% are women, {100 * pr['rural'].mean_weighted:.0f}% live in rural areas, "
  f"{100 * pr['edu_up_to_primary'].mean_weighted:.0f}% have at most primary education and {100 * pr['edu_tertiary'].mean_weighted:.0f}% are graduates. "
  f"Average age is {pr['age'].mean_weighted:.0f} years and the average work week is {pr['hours_week'].mean_weighted:.0f} hours.")
A(f"- **Wages.** The mean hourly wage is Rs. {pr['hourly_wage_nominal'].mean_weighted:.0f} (median Rs. {pr['hourly_wage_nominal']['median']:.0f}); "
  f"it rises from Rs. {byr.iloc[0].hourly_wage_nominal:.0f} in 2017-18 to Rs. {byr.iloc[-1].hourly_wage_nominal:.0f} in 2023-24 in nominal terms. "
  "Regular salaried workers earn about twice as much per hour as casual labourers, graduates about three times as much as workers with "
  "at most primary education, and men about 27% more than women.")
A(f"- **Digital task intensity.** The average worker's occupation scores {pr['dti_mean_score_0_4'].mean_weighted:.2f} on the 0–4 scale "
  "(median 0.07): most Indian wage employees work in occupations whose official descriptions mention little digital work. DTI is far "
  "higher for regular than casual workers (0.39 vs 0.03), for urban than rural workers (0.37 vs 0.12) and for graduates (0.63) than for "
  "workers with at most primary education (0.05). It is stable across rounds (0.21–0.22), because it is a property of occupations: "
  "changes over time come only from shifts in the occupational composition of employment.")
A("- **Comparability across rounds.** Sample sizes (61–71 thousand per round) and composition are similar in the NCO-2004 rounds "
  "(2017-18 to 2020-21) and the NCO-2015 rounds (2021-22 to 2023-24), which supports pooling them with round-specific (year-quarter) fixed effects.")
(ROOT / "paper" / "sample_section.md").write_text("\n".join(P) + "\n", encoding="utf-8")
print("wrote paper/sample_section.md")
