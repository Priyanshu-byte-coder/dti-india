"""Reliability statistics for RQ1: run stability, cross-model and human-LLM agreement."""

from __future__ import annotations

from itertools import combinations

import krippendorff
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score

from .config import DIMENSIONS


def icc2(matrix: np.ndarray) -> tuple[float, float]:
    """ICC(2,1) and ICC(2,k): two-way random effects, absolute agreement (Shrout & Fleiss).
    matrix: units x raters, complete rows only."""
    x = np.asarray(matrix, dtype=float)
    x = x[~np.isnan(x).any(axis=1)]
    n, k = x.shape
    if n < 2 or k < 2:
        return np.nan, np.nan
    grand = x.mean()
    ss_rows = k * ((x.mean(axis=1) - grand) ** 2).sum()
    ss_cols = n * ((x.mean(axis=0) - grand) ** 2).sum()
    ss_err = ((x - grand) ** 2).sum() - ss_rows - ss_cols
    msr, msc = ss_rows / (n - 1), ss_cols / (k - 1)
    mse = ss_err / ((n - 1) * (k - 1))
    if msr == 0 and mse == 0:
        return 1.0, 1.0  # every unit identical across raters and units
    icc_1 = (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)
    icc_k = (msr - mse) / (msr + (msc - mse) / n)
    return float(icc_1), float(icc_k)


def alpha_ordinal(matrix: np.ndarray) -> float:
    """Krippendorff's alpha, ordinal. matrix: raters x units, NaN = missing."""
    x = np.asarray(matrix, dtype=float)
    if np.nanmax(x) == np.nanmin(x):
        return np.nan  # no variation: alpha undefined
    return float(krippendorff.alpha(reliability_data=x, level_of_measurement="ordinal"))


def pairwise(a: pd.Series, b: pd.Series) -> dict[str, float]:
    m = pd.concat([a, b], axis=1).dropna()
    x, y = m.iloc[:, 0].round().astype(int), m.iloc[:, 1].round().astype(int)
    return {
        "n": len(m),
        "exact_agree": float((x == y).mean()),
        "within_1": float(((x - y).abs() <= 1).mean()),
        "kappa_quadratic": float(cohen_kappa_score(x, y, weights="quadratic")) if len(set(x) | set(y)) > 1 else np.nan,
        "spearman": float(spearmanr(x, y).statistic) if x.nunique() > 1 and y.nunique() > 1 else np.nan,
        "alpha_ordinal": alpha_ordinal(np.vstack([x, y])),
        "mean_diff": float((y - x).mean()),
    }


def run_stability(runs: pd.DataFrame, key: str = "nco2015") -> pd.DataFrame:
    """Intra-model stability across repeated runs, per model and dimension."""
    rows = []
    for (model, version), g in runs.groupby(["model_name", "prompt_version"]):
        for d in DIMENSIONS:
            wide = g.pivot(index=key, columns="run", values=d)
            icc_1, icc_k = icc2(wide.to_numpy())
            rows.append({
                "model_name": model,
                "prompt_version": version,
                "dimension": d,
                "n_occupations": len(wide),
                "n_runs": wide.shape[1],
                "icc_2_1": icc_1,
                "icc_2_k": icc_k,
                "alpha_ordinal": alpha_ordinal(wide.to_numpy().T),
                "share_unanimous": float((wide.nunique(axis=1) == 1).mean()),
                "mean_sd": float(wide.std(axis=1, ddof=0).mean()),
            })
    return pd.DataFrame(rows)


def unstable_occupations(cons: pd.DataFrame, sd_threshold: float = 0.5) -> pd.DataFrame:
    """Occupations whose run-to-run SD exceeds the threshold on any dimension: manual review list."""
    return cons[cons["max_sd"] > sd_threshold].sort_values("max_sd", ascending=False)


def cross_model(cons: pd.DataFrame, key: str = "nco2015") -> pd.DataFrame:
    """Agreement between models, separately for each prompt (rubric) version."""
    rows = []
    for version, gv in cons.groupby("prompt_version"):
        models = sorted(gv["model_name"].unique())
        for m1, m2 in combinations(models, 2):
            a = gv[gv["model_name"] == m1].set_index(key)
            b = gv[gv["model_name"] == m2].set_index(key)
            for col in [*DIMENSIONS, "q9_overall"]:
                rows.append({"prompt_version": version, "model_a": m1, "model_b": m2, "item": col,
                             **pairwise(a[col], b[col].reindex(a.index))})
    return pd.DataFrame(rows)


def human_vs_llm(human: pd.DataFrame, cons: pd.DataFrame) -> pd.DataFrame:
    """Agreement of every coder with every model, next to the human-human benchmark.

    The headline comparison: is human-LLM agreement as high as human-human agreement?
    """
    rows = []
    coders = sorted(human["coder_id"].unique())
    h = {c: human[human["coder_id"] == c].set_index("nco2015") for c in coders}
    for c1, c2 in combinations(coders, 2):
        for col in [*DIMENSIONS, "q9_overall"]:
            rows.append({"pair": "human-human", "a": c1, "b": c2, "item": col, **pairwise(h[c1][col], h[c2][col])})
    for model, g in cons.groupby("model_name"):
        m = g.set_index("nco2015")
        for c in coders:
            for col in [*DIMENSIONS, "q9_overall"]:
                rows.append({"pair": "human-llm", "a": c, "b": model, "item": col, **pairwise(h[c][col], m[col])})
    return pd.DataFrame(rows)


def multi_rater_alpha(human: pd.DataFrame, cons: pd.DataFrame | None = None) -> pd.DataFrame:
    """Krippendorff's alpha over all human coders, with and without each model added as a rater."""
    rows = []
    for col in [*DIMENSIONS, "q9_overall"]:
        hw = human.pivot(index="coder_id", columns="nco2015", values=col)
        rows.append({"item": col, "raters": "humans", "alpha_ordinal": alpha_ordinal(hw.to_numpy())})
        if cons is not None:
            for model, g in cons.groupby("model_name"):
                mw = g.set_index("nco2015")[col].rename(model).to_frame().T
                both = pd.concat([hw, mw]).reindex(columns=hw.columns)
                rows.append({"item": col, "raters": f"humans+{model}", "alpha_ordinal": alpha_ordinal(both.to_numpy())})
    return pd.DataFrame(rows)


def summary_q9_vs_dimensions(cons: pd.DataFrame) -> pd.DataFrame:
    """Does the equal-weight index track the holistic Q9 judgement? Supports the weighting choice."""
    rows = []
    for model, g in cons.groupby("model_name"):
        eq = g[list(DIMENSIONS)].mean(axis=1)
        rho = spearmanr(eq, g["q9_overall"]).statistic if eq.nunique() > 1 and g["q9_overall"].nunique() > 1 else np.nan
        rows.append({"model_name": model, "n": len(g), "spearman_q9_vs_equal_weight": float(rho)})
    return pd.DataFrame(rows)
