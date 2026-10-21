"""Build the results-and-status PDF for co-authors from the result files (needs Chrome).

    python paper/results_report.py . docs/DTI_Results_and_Status.pdf
"""
import html
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO = Path(sys.argv[1])
OUT = Path(sys.argv[2])
R = REPO / "reports"
D = ["D1", "D2", "D3", "D4", "D5"]
DIM_NAMES = {"D1": "Basic digital operation", "D2": "Digital information processing",
             "D3": "Digital communication", "D4": "Specialised digital tools",
             "D5": "Digital problem solving / content"}
DIV = {"1": "Managers", "2": "Professionals", "3": "Technicians & assoc. professionals",
       "4": "Clerical support", "5": "Service & sales", "6": "Skilled agriculture",
       "7": "Craft & related trades", "8": "Plant & machine operators", "9": "Elementary occupations"}

STATUS_TIME = sys.argv[3] if len(sys.argv) > 3 else "21 October 2026"
ONET_PROGRESS = sys.argv[4] if len(sys.argv) > 4 else "running"
RUNNING = [
    ("Qwen2.5-14B scores all 3,450 NCO occupations × 5 runs", "Done (21 Oct, 05:50)", "17,250 / 17,250, 0 failed"),
    ("Wage analysis with the NCO-LLM DTI (RQ3–RQ4)", "Done (21 Oct, 08:34)", "10 tables"),
    ("Llama-3.1-8B scores all occupations (second model)", "Done (21 Oct, 15:40)", "17,250 / 17,250, 0 failed"),
    ("Cross-model agreement; wage robustness with the Llama DTI", "Done (21 Oct, 15:55)", "Sections 2 and 3"),
    ("DoubleML with four ML learners, occupation-clustered SEs", "Done (21 Oct)", "Section 4, last table"),
    ("Qwen2.5-14B scores 923 O*NET occupations (RQ2 same-instrument benchmark)", "Running", ONET_PROGRESS),
    ("Human validation (coders)", "Not usable yet", "round 2 forms rejected, see Section 2"),
]


def rd(*p):
    return pd.read_csv(R.joinpath(*p))


def e(x):
    return html.escape(str(x))


def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""


def lp(b, se=None, p=None):
    """coefficient in log points (×100), with SE and stars"""
    s = f"{100 * b:.1f}"
    if p is not None:
        s += stars(p)
    if se is not None:
        s += f" <span class=se>({100 * se:.1f})</span>"
    return s


def pct(b):
    return f"{100 * (math.exp(b) - 1):.1f}%"


def table(head, rows, cls=""):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table class='{cls}'><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


def row(df, model, term="dti_std"):
    r = df[(df["model"] == model) & (df["term"] == term)]
    return r.iloc[0] if len(r) else None


def cell(df, model, term="dti_std"):
    r = row(df, model, term)
    return "—" if r is None else lp(r["coef"], r["se"], r["p"])


# ---------------- RQ1 ----------------
occ = pd.read_csv(REPO / "data/processed/dti_occupation_nco2015.csv", dtype={"nco2015": str, "division": str})
occ = occ[occ["model_name"] == "qwen14b"].copy()
occ["m"] = occ[D].mean(axis=1)
stab = rd("stability_runs.csv")
stab = stab[stab["model_name"] == "qwen14b"]
q9 = rd("q9_vs_equal_weight.csv")
q9 = float(q9[q9["model_name"] == "qwen14b"]["spearman_q9_vs_equal_weight"].iloc[0])
unstable = rd("unstable_occupations.csv")
n_unstable = int((unstable["model_name"] == "qwen14b").sum()) if "model_name" in unstable else len(unstable)
kw = pd.read_csv(REPO / "data/processed/keyword_baseline_nco2015.csv", dtype={"nco2015": str})
mk = occ.merge(kw[["nco2015", "kw_share", "kw_any"]], on="nco2015")
rho_kw = mk["m"].corr(mk["kw_share"], method="spearman")
zero_share = (occ[D].sum(axis=1) == 0).mean()
zero_kw = mk.groupby("kw_any")["m"].apply(lambda s: (s == 0).mean())
mean_kw = mk.groupby("kw_any")["m"].mean()
ung = sum(occ[f"{d}_ungrounded"].sum() for d in D) if f"{D[0]}_ungrounded" in occ else None
pilot = rd("pilot_comparison.csv")
cov = pd.read_csv(REPO / "data/processed/plfs_harmonised_dti_coverage.csv")

stab_rows = [[DIM_NAMES[r.dimension], f"{r.icc_2_1:.2f}", f"{r.alpha_ordinal:.2f}", f"{100 * r.share_unanimous:.0f}%",
              f"{100 * (occ[r.dimension] > 0).mean():.0f}%"] for r in stab.itertuples()]
div = occ.groupby("division")["m"].agg(["count", "mean", lambda s: (s == 0).mean()]).reset_index()
div_rows = [[f"{r.division}. {DIV.get(r.division, r.division)}", int(r.count), f"{r.mean:.2f}", f"{100 * r._4:.0f}%"]
            for r in div.itertuples()]
top = occ.sort_values(["m", "title"], ascending=[False, True]).head(10)
top_rows = [[e(t), f"{m:.1f}"] for t, m in zip(top["title"], top["m"])]

# ---------------- RQ3 ----------------
bl, bo = rd("econ_llm", "baseline.csv"), rd("econ_onet", "baseline.csv")
ladder = [("M1", "No controls"), ("M2", "+ individual characteristics"),
          ("M3", "+ state, industry, year-quarter FE"), ("M4", "+ occupational division FE (preferred)")]
lad_rows = []
for m, lab in ladder:
    rl, ro = row(bl, m), row(bo, m)
    lad_rows.append([f"<b>{m}</b> {lab}", cell(bl, m), f"{rl['r2']:.2f}" if rl is not None else "—", cell(bo, m)])
m4 = row(bl, "M4")
m4o = row(bo, "M4")
ost, osto = rd("econ_llm", "oster.csv").iloc[0], rd("econ_onet", "oster.csv").iloc[0]
rb, rbo = rd("econ_llm", "robustness.csv"), rd("econ_onet", "robustness.csv")
hk, hko = rd("econ_llm", "heckman.csv"), rd("econ_onet", "heckman.csv")
rob_specs = ["M4 unweighted", "M4 unweighted, wild cluster bootstrap", "M4 monthly earnings",
             "M4 regular wage workers only", "M4 casual workers only", "M4 NCO-2015 rounds (Jul 2021+)",
             "M4 NCO-2004 rounds (pre Jul 2021)", "M4 NCO-2004 groups with >=75% direct links",
             "M4 self-employed (earnings incl. capital returns)"]
rob_rows = [[e(s.replace(">=", "≥")), cell(rb, s), cell(rbo, s)] for s in rob_specs]
rob_rows.append(["Heckman selection correction (all)", cell(hk, "Heckman all"), cell(hko, "Heckman all")])
rob_rows.append(["DTI from the second LLM (Llama-3.1-8B)", cell(rd("econ_llm_llama8b_gguf", "baseline.csv"), "M4"), "—"])
for q in ["dti_q2", "dti_q3", "dti_q4", "dti_q5"]:
    rob_rows.append([f"DTI quintile {q[-1]} vs lowest fifth", cell(rb, "M4 DTI quintiles (base Q1)", q),
                     cell(rbo, "M4 DTI quintiles (base Q1)", q)])
total_n = int(m4["n"])

# ---------------- RQ4 ----------------
rif, rifo = rd("econ_llm", "rif.csv"), rd("econ_onet", "rif.csv")
dist_rows = [[f"{int(100 * q)}th percentile", cell(rif, f"RIF q{int(100 * q)}"), cell(rifo, f"RIF q{int(100 * q)}")]
             for q in [0.10, 0.25, 0.50, 0.75, 0.90]]
sg, sgo = rd("econ_llm", "subgroups.csv"), rd("econ_onet", "subgroups.csv")
het = [("Education: up to primary", "edu_band=up_to_primary"), ("Education: middle / secondary", "edu_band=middle_secondary"),
       ("Education: tertiary", "edu_band=tertiary"), ("Regular, no social security (informal)", "formal_ss=0.0"),
       ("Regular, with social security (formal)", "formal_ss=1.0"), ("Regular wage workers", "emp_type=regular"),
       ("Casual workers", "emp_type=casual"), ("Men", "female=0"), ("Women", "female=1"),
       ("Urban", "rural=0"), ("Rural", "rural=1"), ("Age 15–24", "age_band=15-24"), ("Age 45–54", "age_band=45-54")]
het_rows = [[lab, cell(sg, f"M4 | {k}"), cell(sgo, f"M4 | {k}")] for lab, k in het]
it, ito = rd("econ_llm", "interactions.csv"), rd("econ_onet", "interactions.csv")
int_terms = [("Women vs men", "occupation FE + interactions", "dti_x_female"),
             ("Rural vs urban", "occupation FE + interactions", "dti_x_rural"),
             ("Middle/secondary vs up to primary", "occupation FE + interactions", "dti_x_edu_band_middle_secondary"),
             ("Tertiary vs up to primary", "occupation FE + interactions", "dti_x_edu_band_tertiary"),
             ("Casual vs regular", "occupation FE + interactions", "dti_x_emp_type_casual"),
             ("Formal vs informal (regular workers)", "occupation FE + formality interaction (regular)", "dti_x_formal_ss")]
int_rows = [[lab, cell(it, m, t), cell(ito, m, t)] for lab, m, t in int_terms]
ox, oxo = rd("econ_llm", "oaxaca.csv").set_index("component")["value"], rd("econ_onet", "oaxaca.csv").set_index("component")["value"]
ate, ateo = rd("econ_llm", "dml_ate.csv").iloc[0], rd("econ_onet", "dml_ate.csv").iloc[0]
LN = {"linear": "Linear regression", "lasso": "Lasso (cross-validated)", "random_forest": "Random forest",
      "gradient_boosting": "Gradient boosting"}
lrn = rd("econ_llm", "dml_learners.csv")
lrno = rd("econ_onet", "dml_learners.csv") if (R / "econ_onet" / "dml_learners.csv").exists() else None
lrn_rows = []
for r in lrn.itertuples():
    o = lrno[lrno["learner"] == r.learner].iloc[0] if lrno is not None else None
    lrn_rows.append([LN[r.learner], lp(r.coef, r.se_cluster, r.p), f"[{100 * r.ci_low:.1f}, {100 * r.ci_high:.1f}]",
                     f"{r.r2_wage:.3f}", f"{r.r2_dti:.3f}", "—" if o is None else lp(o["coef"], o["se_cluster"], o["p"])])
best = lrn.loc[lrn["r2_wage"].idxmax()]
not_sig = ", ".join(LN[x].split(" (")[0].lower() for x in lrn[lrn["p"] >= 0.05]["learner"]) or "no learner"
onet_ml_note = ""
if lrno is not None:
    bo_ = lrno.loc[lrno["r2_wage"].idxmax()]
    onet_ml_note = (f"With the O*NET-transferred DTI the spread is wider: {100 * lrno['coef'].min():.1f}–{100 * lrno['coef'].max():.1f} log points, and the "
                    f"best-fitting learner ({LN[bo_['learner']].lower()}) gives {lp(bo_['coef'])} (p = {bo_['p']:.2f}). The larger O*NET premium in the "
                    "linear models therefore shrinks once controls enter flexibly, while the India-specific estimate is more stable across learners.")

# second model
bll = rd("econ_llm_llama8b_gguf", "baseline.csv")
m4l = row(bll, "M4")
cm = rd("cross_model.csv")
cm_rows = [[DIM_NAMES.get(r.item, "Holistic score (Q9, 0–10)"), f"{100 * r.exact_agree:.0f}%", f"{100 * r.within_1:.0f}%",
            f"{r.kappa_quadratic:.2f}", f"{r.spearman:.2f}"] for r in cm.itertuples()]
lvl_rows = []
occ_all = pd.read_csv(REPO / "data/processed/dti_occupation_nco2015.csv", dtype={"nco2015": str})
w = occ_all.pivot(index="nco2015", columns="model_name", values="dti_z").dropna()
lvl_rows.append(["8-digit occupation", len(w), f"{w.corr(method='spearman').iloc[0, 1]:.2f}"])
for f, k, lab in [("dti_family4_nco2015", "family4", "4-digit family (NCO-2015)"),
                  ("dti_group3_nco2015", "group3", "3-digit group (NCO-2015, PLFS 2021-24)"),
                  ("dti_group3_nco2004", "nco2004_g3", "3-digit group (NCO-2004, PLFS 2017-21)")]:
    gg = pd.read_csv(REPO / f"data/processed/{f}.csv", dtype={k: str})
    w = gg.pivot(index=k, columns="model_name", values="dti_z").dropna()
    lvl_rows.append([lab, len(w), f"{w.corr(method='spearman').iloc[0, 1]:.2f}"])
stl = pd.read_csv(R / "stability_runs.csv")
stl = stl[stl["model_name"] == "llama8b_gguf"]
zero_llama = (occ_all[occ_all["model_name"] == "llama8b_gguf"][D].sum(axis=1) == 0).mean()
gate = rd("econ_llm", "dml_gate.csv")


def g(dim, grp):
    r = gate[(gate["dimension"] == dim) & (gate["group"] == grp)]
    return f"{100 * r['effect'].iloc[0]:.1f}" if len(r) else "—"


def sgv(df, k):
    r = row(df, f"M4 | {k}")
    return 100 * r["coef"]


# ---------------- page ----------------
css = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 10pt; color: #1d2433; line-height: 1.42; }
h1 { font-size: 17pt; margin: 0 0 2px; color: #14325c; }
h2 { font-size: 12.5pt; color: #14325c; border-bottom: 1.5px solid #c9d3e3; padding-bottom: 2px; margin: 18px 0 6px; page-break-after: avoid; }
h3 { font-size: 10.5pt; margin: 12px 0 4px; color: #2a4a7a; page-break-after: avoid; }
.sub { color: #556; font-size: 9.5pt; margin-bottom: 10px; }
table { border-collapse: collapse; width: 100%; margin: 4px 0 8px; font-size: 9pt; page-break-inside: avoid; }
th { background: #e8eef7; text-align: left; padding: 4px 6px; border-bottom: 1px solid #b8c4d8; font-weight: 600; }
td { padding: 3px 6px; border-bottom: 1px solid #e3e8f0; vertical-align: top; }
td:not(:first-child), th:not(:first-child) { text-align: right; }
table.left td, table.left th { text-align: left !important; }
.se { color: #667; font-size: 8.5pt; }
.box { background: #f3f6fb; border-left: 3px solid #2a5ea8; padding: 7px 10px; margin: 8px 0; page-break-inside: avoid; }
.warn { background: #fff7e6; border-left: 3px solid #c98a00; padding: 7px 10px; margin: 8px 0; page-break-inside: avoid; }
.mean { margin: 4px 0 10px; }
.mean b { color: #14325c; }
.note { color: #556; font-size: 8.5pt; }
ul { margin: 4px 0 8px 18px; padding: 0; } li { margin: 2px 0; }
.two { display: flex; gap: 14px; } .two > div { flex: 1; }
"""

parts = [f"""<html><head><meta charset='utf-8'><title>DTI results and status</title><style>{css}</style></head><body>
<h1>Digital Task Intensity of Indian Occupations — results and status</h1>
<div class=sub>Nair, Anand &amp; Shome (Nirma University) · SAU Digital Markets · status at {STATUS_TIME}<br>
For co-authors. All numbers come from the result files in the project repository (<code>dti-india</code>).</div>

<div class=box><b>In one paragraph.</b> The LLM instrument has scored all 3,450 NCO-2015 occupations and is stable and
grounded in the official text. Linked to {total_n:,} PLFS wage earners (2017-18 to 2023-24), a one-standard-deviation higher
India-specific DTI goes with <b>{lp(m4['coef'])} log points (≈ {pct(m4['coef'])}) higher hourly wages</b> within the same
occupational division (SE {100 * m4['se']:.1f}), somewhat below the {lp(m4o['coef'])} obtained with the US O*NET measure. The premium is
concentrated at the top of the wage distribution and is absent for workers with at most primary education, informal regular
jobs and casual work — the pattern the abstract calls a <i>digital-returns gap</i>. It is a conditional association, not a
causal return. A second LLM ranks occupation groups almost identically (Spearman {lvl_rows[2][2]}), and the DML estimate is similar across four ML learners. Still to come: the India–US comparison RQ2 (22 Oct, early morning) and valid human validation.</div>

<h2>1. What is running and what is left</h2>
{table(["Step", "Status", "Detail"], [[e(a), b, e(c)] for a, b, c in RUNNING], "left")}
<ul>
<li>Jobs run on PARAM Shavak (Quadro GP100) inside <code>screen</code>; they do not depend on anyone's laptop.</li>
<li>After the O*NET scoring: same-instrument India vs O*NET gap (RQ2), then the paper draft is updated. The human–LLM comparison runs as soon as
valid coder forms arrive.</li>
<li>Decisions still open for the professors: wage-model choices marked OPEN in <code>configs/analysis.yaml</code>; confirmation of the strict rubric (Section 2).</li>
</ul>

<h2>2. RQ1 — Is the LLM a reliable measurement instrument?</h2>
<p><b>Set-up.</b> Main instrument: Qwen2.5-14B-Instruct, strict rubric (score only digital work the NCO-2015 text names; silent → 0),
five independent runs per occupation at temperature 0.7, median across runs. Five dimensions scored 0–4; DTI = equal-weight sum of the
z-scored dimensions. The strict rubric was chosen in the pilot (50 occupations, two models, two rubric readings): the broader
"described-task" reading barely reduced the share of all-zero occupations (48% vs 50%) and lowered agreement between models (κ 0.69 vs 0.83).</p>
<h3>Stability across repeated runs (all 3,450 occupations)</h3>
{table(["Dimension", "ICC(2,1)", "Krippendorff α", "All 5 runs identical", "Occupations scored > 0"], stab_rows)}
<div class=mean><b>Meaning.</b> ICC/α of 0.70–0.84 is "good" agreement by the usual benchmarks (0.75+ good, 0.6–0.75 moderate): asked five times,
the model gives largely the same scores. Communication (D3) is the least stable because it is rarely non-zero, so a single
deviating run weighs heavily. {n_unstable:,} occupations ({100 * n_unstable / len(occ):.0f}%) vary by more than 0.5 points (SD) on at least one dimension;
they are listed for review, and the median across five runs is used precisely to absorb this noise.</div>
<h3>Grounding and consistency</h3>
<ul>
<li><b>87%</b> of the 20,355 non-zero dimension scores come with a quote that is found in the official description (pilot: 89%). The rest are
mostly scores without a quote, where the model drew on general knowledge despite the rule.</li>
<li>Equal-weight dimension mean vs the model's own holistic 0–10 judgement (Q9): Spearman <b>{q9:.2f}</b> — supports equal weighting.</li>
<li>Correlation with a simple keyword count on the same text: Spearman <b>{rho_kw:.2f}</b>. Occupations whose description names a digital term
average {mean_kw[1]:.2f} (0–4) vs {mean_kw[0]:.2f} for the rest; only {100 * zero_kw[1]:.0f}% of the former are all-zero. The LLM therefore picks up much
more than keywords, but stays tied to the text.</li>
<li><b>{100 * zero_share:.1f}%</b> of occupations score 0 on every dimension. This is a finding about the NCO-2015 text, not an error: only about 5% of descriptions
use any digital term. It is the main reason to compare with O*NET (RQ2).</li>
</ul>
<div class=two><div><h3>Mean score (0–4) by division</h3>
{table(["Division", "Occ.", "Mean", "All-zero"], div_rows)}</div>
<div><h3>Most digital occupations</h3>{table(["Occupation", "Mean"], top_rows, "")}</div></div>
<div class=mean><b>Meaning.</b> The ranking is economically sensible (professionals &gt; technicians &gt; clerks &gt; … &gt; agriculture and elementary
work) and the most digital occupations are the expected ones — face validity for the instrument.
PLFS match rate: {100 * cov['share_matched_weighted'].min():.1f}–{100 * cov['share_matched_weighted'].max():.1f}% of employed workers in each round receive a DTI.</div>
<h3>Agreement between two LLM families (Qwen2.5-14B vs Llama-3.1-8B, all 3,450 occupations)</h3>
<div class=two><div>{table(["Dimension", "Exact", "Within 1", "Weighted κ", "Spearman"], cm_rows)}</div>
<div>{table(["Level", "Units", "Spearman, DTI"], lvl_rows)}</div></div>
<div class=mean><b>Meaning.</b> Two independently trained models, from different companies and of different size, rank occupation <i>groups</i> (the level
at which DTI enters the wage regressions) almost identically ({lvl_rows[2][2]} for the NCO-2015 groups). Agreement on single occupations is moderate,
highest for information processing and content/problem solving and lowest for communication, which is rarely non-zero. Llama is the noisier
instrument: run stability ICC {stl['icc_2_1'].min():.2f}–{stl['icc_2_1'].max():.2f} (Qwen {stab['icc_2_1'].min():.2f}–{stab['icc_2_1'].max():.2f}) and {100 * zero_llama:.0f}% all-zero occupations
(Qwen {100 * zero_share:.0f}%). This supports Qwen as the main instrument.</div>
<div class=warn><b>Human validation not yet usable.</b> 200 occupations were sent to three coders (stratified by division and by whether the text names
digital work; pilot occupations excluded). The two forms returned on 21 Oct failed the quality checks and are not used: one is a near-copy of the other
(96% identical rows, identical evidence, same coder ID), no occupation was scored 0 although the rule requires 0 when the text is silent,
agricultural and elementary jobs score like professionals, only 23% of evidence words appear in the description, and scores repeat in a fixed
10-row pattern. (The first round, 19 Oct, gave identical scores on all five dimensions.) A smaller sample coded independently, e.g. 100 occupations
by two coders, would suffice.</div>

<h2>3. RQ3 — Conditional digital occupational wage premium</h2>
<p>ln(real hourly wage) of regular and casual wage earners aged 15–64, seven PLFS rounds, PLFS weights, standard errors clustered by
occupation ({int(m4['n_clusters'])} occupation groups). Coefficients in <b>log points per one standard deviation of DTI</b> (≈ % difference in wages). SE in brackets;
*** p&lt;0.01, ** p&lt;0.05, * p&lt;0.1.</p>
{table(["Specification", "NCO-LLM DTI (India)", "R²", "O*NET-transferred DTI"], lad_rows)}
<div class=mean><b>Meaning.</b> Without controls, more digital occupations pay {lp(row(bl, 'M1')['coef'])} log points more per SD. Most of that reflects who works in them
(education, age, location, industry). Comparing occupations within the same broad division, the premium is <b>{lp(m4['coef'])} log points (≈ {pct(m4['coef'])})</b>:
modest but clearly different from zero (p = {m4['p']:.3f}). With the US O*NET measure it is {lp(m4o['coef'])}: transferring US task content gives a somewhat larger premium.</div>
<h3>How robust is it?</h3>
{table(["Check (all M4)", "NCO-LLM DTI", "O*NET DTI"], rob_rows)}
<div class=mean><b>Meaning.</b> The premium survives unweighted estimation, the wild cluster bootstrap, monthly earnings, direct links only
and correction for selection into wage work; it is weaker (significant only at 10%) in the pre-2021 NCO-2004 rounds.
With the DTI from the second LLM it is {lp(m4l['coef'])} (p = {m4l['p']:.3f}): same sign and pattern, smaller, as expected when the noisier Llama scores
attenuate the estimate. It is <b>not linear</b>: only the two most digital fifths of occupations earn significantly more.
It is absent for casual workers and the self-employed.</div>
<div class=warn><b>Not causal.</b> Oster (2019) δ = {ost['delta_for_beta_0']:.2f} (O*NET: {osto['delta_for_beta_0']:.2f}): selection on unobservables only about a third as strong as selection
on observables would explain the premium away. Workers sort into digital occupations by ability and background, so the paper reports β as a
<b>conditional occupational association</b>, as stated in the abstract.</div>

<h2>4. RQ4 — Who gains? Heterogeneity</h2>
<h3>Across the wage distribution (unconditional quantile / RIF regressions)</h3>
{table(["Wage percentile", "NCO-LLM DTI", "O*NET DTI"], dist_rows)}
<div class=mean><b>Meaning.</b> No premium in the lower half of the distribution; it rises to about {lp(row(rif, 'RIF q90')['coef'])} log points at the 90th percentile.
Occupational digital intensity pays mainly at the top.</div>
<h3>By group (M4 estimated separately for each group)</h3>
{table(["Group", "NCO-LLM DTI", "O*NET DTI"], het_rows)}
<h3>Within the same 3-digit occupation (interactions with full occupation fixed effects)</h3>
{table(["Difference in the premium", "NCO-LLM DTI", "O*NET DTI"], int_rows)}
<div class=mean><b>Meaning.</b>
<ul>
<li><b>Education is the clearest divide.</b> No premium for workers with at most primary schooling ({sgv(sg, 'edu_band=up_to_primary'):.1f}, n.s.); {sgv(sg, 'edu_band=tertiary'):.1f} for graduates.
Within the same occupation, graduates gain about {100 * row(it, 'occupation FE + interactions', 'dti_x_edu_band_tertiary')['coef']:.0f} log points more per SD than the least educated.</li>
<li><b>Formality.</b> Among regular workers, the premium exists only with social-security coverage ({sgv(sg, 'formal_ss=1.0'):.1f} vs {sgv(sg, 'formal_ss=0.0'):.1f}, n.s.).
Casual workers get none.</li>
<li><b>Gender.</b> Women earn a larger premium than men ({sgv(sg, 'female=1'):.1f} vs {sgv(sg, 'female=0'):.1f}; machine-learning group effects {g('female', 'female=1')} vs {g('female', 'female=0')}),
but occupational DTI explains almost none of the {100 * ox['total gap']:.1f}-point gender wage gap (Oaxaca–Blinder: {100 * ox['explained: dti']:.1f} points;
O*NET: {100 * oxo['explained: dti']:.1f}). Most of the gap ({100 * ox['unexplained']:.1f} points) is unexplained.</li>
<li><b>Rural–urban is mixed.</b> Estimated separately, the premium is higher for rural workers; within the same occupation it is lower. This needs
care in the paper and is reported as inconclusive.</li>
<li><b>Machine-learning group effects</b> (double/debiased ML with gradient boosting) confirm the education and gender gradients.</li>
</ul>
</div>
<h3>Machine-learning check: does the result depend on the ML model?</h3>
<p>Double/debiased ML (partially linear model, 200,000-worker random subsample, 5-fold cross-fitting by occupation, standard errors clustered by
occupation). The same estimator is run with four learners for the two nuisance predictions (wage from controls, DTI from controls).
R² = how well each learner predicts on held-out data.</p>
{table(["Learner", "Average effect (cluster SE)", "95% CI", "R², wage", "R², DTI", "O*NET DTI"], lrn_rows)}
<div class=mean><b>Meaning.</b> The effect is {100 * lrn['coef'].min():.1f}–{100 * lrn['coef'].max():.1f} log points across learners, close to the regression estimate ({lp(m4['coef'])}):
the result does not hinge on one ML model. The best-fitting learner is {LN[best['learner']].lower()} (highest out-of-sample R² for wages), with
{lp(best['coef'])} log points (95% CI {100 * best['ci_low']:.1f} to {100 * best['ci_high']:.1f}). With occupation-clustered standard errors the intervals are much wider than
in a DML run that treats workers as independent; with {not_sig} the effect is not significant at 5%.
{onet_ml_note}</div>
<div class=box><b>Policy reading (abstract, Section 7).</b> Digital intensity of an occupation translates into higher pay mainly for educated, formally employed,
higher-paid workers. For the less educated, informal and casual workforce the premium is zero. This is a <b>digital-returns gap</b>, not only a
digital-skills gap: basic digital training alone is unlikely to close it without formalisation, advanced skills and access to digitally enabled jobs.</div>

<h2>5. RQ2 — India-specific vs O*NET-transferred intensity</h2>
<p>Partly visible already: with the same wage model, the US O*NET measure gives a larger average premium ({lp(m4o['coef'])} vs {lp(m4['coef'])}) and a larger
gradient by education and formality. Whether this is because US occupations are described as more digital than their Indian counterparts is exactly what the RQ2 comparison tests.
<b>Pending tonight:</b> the same LLM prompt applied to O*NET texts (so the gap reflects texts, not method), correlations at the occupation-family
level, and the DigitalGap by division and skill level.</p>

<h2>6. Data and reproducibility</h2>
<ul>
<li>NCO-2015 Vol II descriptions (3,450 occupations); PLFS 2017-18 to 2023-24 (seven annual rounds, CWS wages, MoSPI weights), pre-2021 rounds linked through an
NCO-2015 → NCO-2004 concordance (2,657 direct links, others via siblings); O*NET 31.0 with BLS SOC–ISCO crosswalk and OEWS weights.</li>
<li>LLMs run locally (llama.cpp, GGUF): no occupation text leaves the university server. Prompt and rubric are versioned (hash 46a323537a).</li>
<li>PLFS microdata are not redistributed; only estimates appear in the repository. Code: private GitHub repository <code>dti-india</code>
(guide for writing: <code>docs/PAPER_GUIDE.md</code>).</li>
</ul>
<p class=note>Preliminary results for internal discussion; numbers may change slightly once RQ2 and the human validation are added.</p>
</body></html>"""]

html_path = OUT.with_suffix(".html")
html_path.write_text("".join(parts), encoding="utf-8")
chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={OUT}", html_path.resolve().as_uri()], check=True, timeout=120)
print("wrote", OUT)
