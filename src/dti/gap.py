"""India (NCO-LLM) vs O*NET digital intensity: external validation and the gap (RQ2).

DigitalGap_j = DTI_j^{O*NET} - DTI_j^{NCO-LLM}  (abstract eq. 2)

Compared at the NCO-2015 family = ISCO-08 unit group level. Two gap versions:
- `gap_raw`: same-instrument LLM scores on the 0-4 rubric scale. Both sides were scored
  with the identical prompt, so raw units are directly comparable.
- `gap_pct`: percentile-rank difference, for any O*NET measure (scale-free).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


def correlations(df: pd.DataFrame, nco_col: str, onet_cols: list[str]) -> pd.DataFrame:
    rows = []
    for c in onet_cols:
        m = df[[nco_col, c]].dropna()
        ok = len(m) > 2 and m[nco_col].nunique() > 1 and m[c].nunique() > 1
        rows.append({
            "nco_measure": nco_col,
            "onet_measure": c,
            "n": len(m),
            "pearson": pearsonr(m[nco_col], m[c]).statistic if ok else np.nan,
            "spearman": spearmanr(m[nco_col], m[c]).statistic if ok else np.nan,
        })
    return pd.DataFrame(rows)


def gap_table(
    nco: pd.DataFrame,
    onet: pd.DataFrame,
    nco_col: str,
    onet_col: str,
    level: str = "family4",
    raw_comparable: bool = False,
) -> pd.DataFrame:
    """One row per matched occupation unit with percentile ranks and the gap.

    nco: NCO aggregates with column `level`; onet: O*NET aggregates with column `isco08`.
    """
    df = nco[[level, nco_col]].rename(columns={nco_col: "nco"}).merge(
        onet[["isco08", onet_col]].rename(columns={"isco08": level, onet_col: "onet"}), on=level, how="inner"
    ).dropna()
    df["pct_nco"] = df["nco"].rank(pct=True)
    df["pct_onet"] = df["onet"].rank(pct=True)
    df["gap_pct"] = df["pct_onet"] - df["pct_nco"]
    if raw_comparable:
        df["gap_raw"] = df["onet"] - df["nco"]
    df.insert(1, "nco_measure", nco_col)
    df.insert(2, "onet_measure", onet_col)
    return df.sort_values("gap_pct", ascending=False).reset_index(drop=True)


def gap_by(gaps: pd.DataFrame, meta: pd.DataFrame, by: str, level: str = "family4") -> pd.DataFrame:
    """Mean gap by a grouping (e.g. division, skill level): systematic over/under-statement."""
    df = gaps.merge(meta[[level, by]].drop_duplicates(level), on=level, how="left")
    cols = ["gap_pct"] + (["gap_raw"] if "gap_raw" in df else [])
    out = df.groupby(by)[cols].agg(["mean", "std", "count"])
    out.columns = ["_".join(c) for c in out.columns]
    return out.reset_index()


def unmatched(nco: pd.DataFrame, onet: pd.DataFrame, level: str = "family4") -> dict[str, list[str]]:
    a, b = set(nco[level]), set(onet["isco08"])
    return {"nco_only": sorted(a - b), "onet_only": sorted(b - a)}
