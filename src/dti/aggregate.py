"""From raw LLM runs to the DTI at every level PLFS needs.

Steps:
1. runs -> one long table (model x occupation x run)
2. consensus per model x occupation: median score per dimension across runs, plus spread
3. DTI_j = sum_k w_k z(D_jk), re-standardised (abstract eq. 1; Vashisht & Dubey style)
4. aggregate occupation DTI to NCO-2015 family (4-digit), group (3-digit, PLFS from
   July 2021) and NCO-2004 3-digit (PLFS before July 2021)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DIMENSIONS

CATEGORICAL = ("q1_detail", "q10_core", "q11_india_today")


def load_runs(
    paths: list[Path],
    key: str = "nco2015",
    prompt_version: str | None = None,
    descriptions: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Successful runs from JSONL files; the record's `code` is returned as column `key`.
    With `descriptions` (code -> text) the evidence check is recomputed with the current
    checker instead of using the status stored at scoring time."""
    from .evidence import check_evidence

    rows = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if not rec.get("ok"):
                    continue
                if prompt_version and rec["prompt_version"] != prompt_version:
                    continue
                c = rec["coding"]
                row = {
                    "model_name": rec["model_name"],
                    "prompt_version": rec["prompt_version"],
                    key: rec["code"],
                    "run": rec["run"],
                    "q1_detail": c["q1_detail"],
                    "q9_overall": c["q9_overall"],
                    "q10_core": c["q10_core"],
                    "q11_india_today": c["q11_india_today"],
                }
                for d in DIMENSIONS:
                    row[d] = c["dimensions"][d]["score"]
                    row[f"{d}_conf"] = c["dimensions"][d]["confidence"]
                    if descriptions is not None and rec["code"] in descriptions:
                        row[f"{d}_evidence"] = check_evidence(c["dimensions"][d]["evidence"], descriptions[rec["code"]])
                    else:
                        row[f"{d}_evidence"] = rec.get("evidence_check", {}).get(d)
                rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("no successful LLM records found")
    # a resumed job can leave a duplicate (occupation, run); keep the last
    return df.drop_duplicates(["model_name", "prompt_version", key, "run"], keep="last")


def consensus(runs: pd.DataFrame, key: str = "nco2015") -> pd.DataFrame:
    keys = ["model_name", "prompt_version", key]
    g = runs.groupby(keys)
    out = g.size().rename("n_runs").to_frame()
    for d in DIMENSIONS:
        out[d] = g[d].median()
        out[f"{d}_sd"] = g[d].std(ddof=0)
        out[f"{d}_conf"] = g[f"{d}_conf"].mean()
        # share of runs with a score > 0 whose evidence is missing or not found in the text
        bad = runs[d].gt(0) & runs[f"{d}_evidence"].isin(["not_found", "partial", "empty"])
        out[f"{d}_ungrounded"] = bad.groupby([runs[k] for k in keys]).mean()
    out["q9_overall"] = g["q9_overall"].median()
    for col in CATEGORICAL:
        out[col] = g[col].agg(lambda s: s.mode().sort_values().iloc[0])
    out["max_sd"] = out[[f"{d}_sd" for d in DIMENSIONS]].max(axis=1)
    return out.reset_index()


def weighted_z(x: pd.Series, w: pd.Series | None = None) -> pd.Series:
    w = pd.Series(1.0, index=x.index) if w is None else w.reindex(x.index).fillna(0.0)
    mu = np.average(x, weights=w)
    sd = np.sqrt(np.average((x - mu) ** 2, weights=w))
    return (x - mu) / sd if sd > 0 else x * 0.0


def build_dti(
    cons: pd.DataFrame,
    weights: dict[str, float],
    std_weights: pd.Series | None = None,
) -> pd.DataFrame:
    """Add z-scored dimensions and the DTI to a consensus table (one model at a time).

    std_weights: optional employment weights indexed like `cons` (e.g. PLFS employment
    mapped to occupations). Unweighted across occupations when None.
    """
    if abs(sum(weights.values()) - 1) > 1e-9:
        raise ValueError("dimension weights must sum to 1")
    out = cons.copy()
    for d in DIMENSIONS:
        out[f"{d}_z"] = weighted_z(out[d].astype(float), std_weights)
    raw = sum(weights[d] * out[f"{d}_z"] for d in DIMENSIONS)
    out["dti_z"] = weighted_z(raw, std_weights)
    lo, hi = raw.min(), raw.max()
    out["dti_0_100"] = 100 * (raw - lo) / (hi - lo) if hi > lo else 0.0
    out["dti_mean_score"] = out[list(DIMENSIONS)].mean(axis=1)  # 0-4, easy to read
    return out


def aggregate_level(
    occ: pd.DataFrame,
    level_map: pd.DataFrame,
    level: str,
    how: str = "mean",
    key: str = "nco2015",
) -> pd.DataFrame:
    """Aggregate occupation-level scores to `level`. NCO has no employment counts below
    3-digit, so occupations within a group are weighted equally (`how` = mean | median)."""
    value_cols = [*DIMENSIONS, "dti_z", "dti_0_100", "dti_mean_score", "q9_overall"]
    overlap = [c for c in level_map.columns if c != key and c in occ.columns]
    df = occ.drop(columns=overlap).merge(level_map, on=key, how="left", validate="many_to_one")
    df = df[df[level].fillna("") != ""]
    keys = ["model_name", "prompt_version", level]
    out = df.groupby(keys)[value_cols].agg(how)
    out["n_occupations"] = df.groupby(keys).size()
    out["dti_sd_within"] = df.groupby(keys)["dti_z"].std(ddof=0)
    if "link" in df:
        out["share_direct_link"] = df.assign(direct=df["link"].eq("direct")).groupby(keys)["direct"].mean()
    return out.reset_index()
