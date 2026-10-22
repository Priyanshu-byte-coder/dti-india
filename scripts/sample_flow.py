"""Sample construction (observations kept after each filter) and descriptive statistics of the
analytical sample. Needs the PLFS microdata, so it runs where the data is (PARAM Shavak).

    python scripts/sample_flow.py [harmonised.parquet] [out_dir]
    default: data/processed/plfs_qwen14b.parquet  reports/sample

Writes (estimates and counts only, no microdata):
  sample_flow.csv               rows kept after each filter, by round and in total
  descriptives_pooled.csv       weighted mean / SD (and unweighted N) of every variable, analysis sample
  descriptives_by_round.csv     key variables by PLFS round
  descriptives_by_group.csv     key variables by employment type and by sex
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dti.econ import analysis_sample  # noqa: E402

PQ = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/processed/plfs_qwen14b.parquet"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "reports/sample"
OUT.mkdir(parents=True, exist_ok=True)
pcfg = yaml.safe_load(open(ROOT / "configs/plfs.yaml"))
acfg = yaml.safe_load(open(ROOT / "configs/analysis.yaml"))
s = acfg["sample"]
df = pd.read_parquet(PQ)
rounds = sorted(df["round"].unique())

# stage 0: raw person records in the first-visit person file
raw = {}
for r, rc in pcfg["rounds"].items():
    n = 0
    for f in rc["files"]:
        with open(ROOT / f, "rb") as fh:
            n += sum(1 for _ in fh) - 1  # minus header
    raw[r] = n

y = s["outcome"]
stages = [
    ("1. Person records, PLFS first-visit file", None),
    ("2. Usual household members (temporary visitors dropped)", lambda d: pd.Series(True, index=d.index)),
    (f"3. Aged {s['age_min']}-{s['age_max']}", lambda d: d["age"].between(s["age_min"], s["age_max"])),
    ("4. Employed in the current weekly status (CWS)", lambda d: d["emp_type"].isin(["self_employed", "regular", "casual"])),
    ("5. Wage employees: regular salaried or casual labour", lambda d: d["emp_type"].isin(s["emp_types"])),
    ("6. Positive earnings and hours reported (hourly wage computable)", lambda d: d["hourly_wage"].notna()),
    ("7. Hourly wage within the 0.5th-99.5th percentile of the round", lambda d: d[y].notna()),
    ("8. Occupation code matched to a DTI score", lambda d: d["dti_matched"] == 1),
    ("9. Positive survey weight", lambda d: d["weight"] > 0),
]
rows = []
keep = pd.Series(True, index=df.index)
for label, f in stages:
    if f is None:
        counts = {r: raw.get(r, np.nan) for r in rounds}
    else:
        keep &= f(df)
        counts = df[keep].groupby("round").size().reindex(rounds).to_dict()
    rows.append({"stage": label, **counts})

# stage 10: complete covariates used in the preferred model (what pyfixest keeps for M4)
samp = analysis_sample(df, acfg)
fe = acfg["fe_sets"]["preferred"]
need = [y, "dti_std", *acfg["controls"], *fe, "occ_cluster"]
complete = samp[need].notna().all(axis=1)
for c in fe:
    complete &= samp[c].astype(str).ne("nan") & samp[c].astype(str).ne("<NA>") & samp[c].astype(str).ne("NA")
rows.append({"stage": "10. Complete covariates for the preferred model (M4)",
             **samp[complete].groupby("round").size().reindex(rounds).to_dict()})
flow = pd.DataFrame(rows)
flow["Total"] = flow[rounds].sum(axis=1)
flow["dropped_at_stage"] = flow["Total"].shift(1) - flow["Total"]
flow["share_of_previous"] = flow["Total"] / flow["Total"].shift(1)
flow.to_csv(OUT / "sample_flow.csv", index=False)
print(flow.to_string(index=False))

# ---------------------------------------------------------------- descriptives (analysis sample, M4-complete)
a = samp[complete].copy()
w = a["weight"]
a["hourly_wage_nominal"] = a["hourly_wage"]
a["monthly_earnings_nominal"] = a["monthly_earnings"]
a["regular"] = (a["emp_type"] == "regular").astype(int)
for b in ["up_to_primary", "middle_secondary", "tertiary"]:
    a[f"edu_{b}"] = (a["edu_band"] == b).astype(int)
for g in sorted(a["social_group"].dropna().unique()):
    a[f"social_group_{g}"] = (a["social_group"] == g).astype(int)
a["dti_mean_score_0_4"] = a[["D1", "D2", "D3", "D4", "D5"]].mean(axis=1)
a["nco2015_round"] = (a["occ_system"] == "nco2015").astype(int)

VARS = [("ln_real_hourly_wage", "Log hourly wage (outcome; nominal Rs.)"), ("hourly_wage_nominal", "Hourly wage, Rs. (nominal)"),
        ("monthly_earnings_nominal", "Monthly earnings, Rs. (nominal)"), ("hours_week", "Hours worked per week"),
        ("dti_z", "DTI (z-score across occupations)"), ("dti_std", "DTI standardised across workers (regressor)"),
        ("dti_mean_score_0_4", "DTI mean dimension score (0-4)"),
        ("D1", "D1 basic digital operation (0-4)"), ("D2", "D2 information processing (0-4)"), ("D3", "D3 communication (0-4)"),
        ("D4", "D4 specialised tools (0-4)"), ("D5", "D5 problem solving / content (0-4)"),
        ("age", "Age (years)"), ("female", "Female"), ("married", "Currently married"), ("rural", "Rural"),
        ("edu_up_to_primary", "Education: up to primary"), ("edu_middle_secondary", "Education: middle / secondary"),
        ("edu_tertiary", "Education: tertiary (graduate+)"), ("regular", "Regular salaried"), ("casual", "Casual labour"),
        ("formal_ss", "Social-security coverage (regular workers only)"), ("hh_size", "Household size"),
        ("nco2015_round", "Observed in an NCO-2015 round (2021-24)")]
VARS += [(c, f"Social group code {c.split('_')[-1]}") for c in a.columns if c.startswith("social_group_")]


def wstats(d, var):
    x = pd.to_numeric(d[var], errors="coerce")
    m = x.notna()
    if m.sum() == 0:
        return np.nan, np.nan, 0
    ww = d.loc[m, "weight"]
    mu = np.average(x[m], weights=ww)
    sd = np.sqrt(np.average((x[m] - mu) ** 2, weights=ww))
    return mu, sd, int(m.sum())


pooled = []
for v, lab in VARS:
    mu, sd, n = wstats(a, v)
    q = pd.to_numeric(a[v], errors="coerce").dropna()
    pooled.append({"variable": v, "label": lab, "mean_weighted": mu, "sd_weighted": sd, "n": n,
                   "min": q.min() if len(q) else np.nan, "median": q.median() if len(q) else np.nan,
                   "max": q.max() if len(q) else np.nan})
pd.DataFrame(pooled).to_csv(OUT / "descriptives_pooled.csv", index=False)

KEY = ["ln_real_hourly_wage", "hourly_wage_nominal", "hours_week", "dti_mean_score_0_4", "dti_z", "age", "female", "rural",
       "edu_up_to_primary", "edu_tertiary", "casual", "formal_ss"]
out = []
for r, d in a.groupby("round"):
    row = {"round": r, "occ_system": d["occ_system"].iloc[0], "n": len(d), "weighted_millions": d["weight"].sum() / 1e6,
           "occ_groups": d["occ_cluster"].nunique()}
    row.update({v: wstats(d, v)[0] for v in KEY})
    out.append(row)
pd.DataFrame(out).to_csv(OUT / "descriptives_by_round.csv", index=False)

grp = []
for name, col in [("employment type", "emp_type"), ("sex", "female"), ("sector", "rural"), ("education", "edu_band")]:
    for lev, d in a.groupby(col):
        row = {"by": name, "group": lev, "n": len(d), "weighted_share": d["weight"].sum() / w.sum()}
        row.update({v: wstats(d, v)[0] for v in KEY})
        grp.append(row)
pd.DataFrame(grp).to_csv(OUT / "descriptives_by_group.csv", index=False)
print(f"analysis sample (M4-complete): {len(a):,} workers, {a['occ_cluster'].nunique()} occupation groups -> {OUT}")
