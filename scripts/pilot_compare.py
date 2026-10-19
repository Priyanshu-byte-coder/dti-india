"""Compare the pilot runs across rubric versions and models (decision aid for item 1 of
docs/decisions.md). Run from the repo root after the pilot:  python scripts/pilot_compare.py

Writes reports/pilot_comparison.csv and prints a summary.
"""
import glob
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.stats import spearmanr

from dti.aggregate import consensus, load_runs
from dti.config import DIMENSIONS
from dti.prompt import prompt_version
from dti.reliability import alpha_ordinal, icc2, pairwise

corpus = pd.read_csv("data/interim/nco2015_corpus.csv", dtype=str)
desc = dict(zip(corpus["nco2015"], corpus["description"]))
names = {}
for path in ["configs/rubric.yaml", "configs/rubric_strict.yaml"]:
    rub = yaml.safe_load(open(path, encoding="utf-8"))
    names[prompt_version(rub)] = "described-task (v1.1)" if "strict" not in path else "strict (v1.0)"

runs = load_runs(sorted(Path(p) for p in glob.glob("data/llm/*/*/nco.jsonl")), descriptions=desc)
cons = consensus(runs)
cons["dti_mean"] = cons[list(DIMENSIONS)].mean(axis=1)

onet = None
p = Path("data/processed/onet_measures_isco4.csv")
if p.exists():
    onet = pd.read_csv(p, dtype={"isco08": str}).set_index("isco08")["muro_0_100"]
fam = corpus.set_index("nco2015")["family4"]

rows = []
for (model, ver), g in runs.groupby(["model_name", "prompt_version"]):
    c = cons[(cons.model_name == model) & (cons.prompt_version == ver)].set_index("nco2015")
    stab = [icc2(g.pivot(index="nco2015", columns="run", values=d).to_numpy())[0] for d in DIMENSIONS]
    alph = [alpha_ordinal(g.pivot(index="nco2015", columns="run", values=d).to_numpy().T) for d in DIMENSIONS]
    pos = g[list(DIMENSIONS)].gt(0)
    ev = pd.concat([g[f"{d}_evidence"][pos[d]] for d in DIMENSIONS])
    row = {
        "model": model, "rubric": names.get(ver, ver), "occupations": len(c),
        "share_all_zero": round(float((c[list(DIMENSIONS)].sum(axis=1) == 0).mean()), 3),
        "mean_score_0_4": round(float(c["dti_mean"].mean()), 3),
        "icc_runs_median": round(float(np.nanmedian(stab)), 3),
        "alpha_runs_median": round(float(np.nanmedian(alph)), 3),
        "scores_gt0": int(len(ev)),
        "grounded_share": round(float(ev.isin(["exact", "close"]).mean()), 3) if len(ev) else np.nan,
        "ungrounded_empty": int((ev == "empty").sum()), "ungrounded_not_found": int(ev.isin(["not_found", "partial"]).sum()),
        "spearman_q9_vs_mean": round(float(spearmanr(c["dti_mean"], c["q9_overall"]).statistic), 3),
    }
    if onet is not None:
        o = c.index.map(fam).map(onet)
        ok = ~pd.isna(o)
        row["spearman_vs_onet_muro"] = round(float(spearmanr(c["dti_mean"][ok], o[ok]).statistic), 3)
    rows.append(row)
summary = pd.DataFrame(rows)

agree = []
for ver, gv in cons.groupby("prompt_version"):
    models = sorted(gv.model_name.unique())
    for m1, m2 in combinations(models, 2):
        a, b = gv[gv.model_name == m1].set_index("nco2015"), gv[gv.model_name == m2].set_index("nco2015")
        st = pairwise(a["dti_mean"].round(0), b["dti_mean"].round(0))
        r = spearmanr(a["dti_mean"], b["dti_mean"].reindex(a.index)).statistic
        agree.append({"rubric": names.get(ver, ver), "models": f"{m1} vs {m2}", "spearman_dti": round(float(r), 3),
                      "kappa_quadratic_rounded": round(st["kappa_quadratic"], 3)})
for model, gm in cons.groupby("model_name"):
    vs = sorted(gm.prompt_version.unique())
    if len(vs) == 2:
        a, b = gm[gm.prompt_version == vs[0]].set_index("nco2015"), gm[gm.prompt_version == vs[1]].set_index("nco2015")
        agree.append({"rubric": "strict vs described", "models": model,
                      "spearman_dti": round(float(spearmanr(a["dti_mean"], b["dti_mean"].reindex(a.index)).statistic), 3)})

Path("reports").mkdir(exist_ok=True)
summary.to_csv("reports/pilot_comparison.csv", index=False)
pd.DataFrame(agree).to_csv("reports/pilot_agreement.csv", index=False)
pd.set_option("display.width", 250)
print(summary.to_string(index=False))
print()
print(pd.DataFrame(agree).to_string(index=False))

# examples: same occupations under both rubrics (primary model)
prim = cons[cons.model_name == "qwen14b"]
if prim.prompt_version.nunique() == 2:
    w = prim.pivot(index="nco2015", columns="prompt_version", values="dti_mean").rename(columns=names)
    w["title"] = w.index.map(corpus.set_index("nco2015")["title"])
    print("\nqwen14b, mean score 0-4 by rubric (largest differences):")
    w["diff"] = w.iloc[:, 0] - w.iloc[:, 1]
    print(w.reindex(w["diff"].abs().sort_values(ascending=False).index).head(10).round(2).to_string())
