"""Build the NCO-2015 occupation corpus from the coder form workbook.

The coder form's "Coding" sheet already holds every NCO-2015 8-digit occupation
with its Vol II description and hierarchy, so the LLM scores exactly the text the
human coders see.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

COLUMN_MAP = {
    "NCO-2015 code": "nco2015",
    "Occupation title": "title",
    "Occupation description (NCO-2015 Vol II)": "description",
    "Family code (4-digit)": "family4",
    "Family title": "family_title",
    "Group code (3-digit, PLFS level)": "group3",
    "Group title": "group_title",
    "Division": "division",
    "Division title": "division_title",
    "NCO skill level": "skill_level",
    "NCO-2004 code": "nco2004",
    "QP/NOS reference": "qp_ref",
    "NSQF level": "nsqf_level",
}


def _clean(text: object) -> str:
    if pd.isna(text):
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def build_corpus(xlsx_path: Path) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, sheet_name="Coding", header=1, dtype=str)
    missing = set(COLUMN_MAP) - set(df.columns)
    if missing:
        raise ValueError(f"coder form is missing columns: {sorted(missing)}")

    out = df[list(COLUMN_MAP)].rename(columns=COLUMN_MAP)
    out = out[out["nco2015"].notna()].copy()
    for col in out.columns:
        out[col] = out[col].map(_clean)

    if out["nco2015"].duplicated().any():
        dups = out.loc[out["nco2015"].duplicated(), "nco2015"].tolist()
        raise ValueError(f"duplicate NCO-2015 codes: {dups[:10]}")
    if (out["description"] == "").any():
        raise ValueError("some occupations have an empty description")

    out["n_words"] = out["description"].str.split().str.len()
    return out.reset_index(drop=True)


def load_corpus(csv_path: Path) -> pd.DataFrame:
    return pd.read_csv(csv_path, dtype=str, keep_default_na=False).assign(
        n_words=lambda d: d["n_words"].astype(int)
    )


def pilot_sample(corpus: pd.DataFrame, n: int, seed: int = 0) -> pd.DataFrame:
    """Prompt-development set stratified by division, proportional with at least one per division."""
    shares = corpus["division"].value_counts(normalize=True)
    quota = (shares * n).round().clip(lower=1).astype(int)
    parts = [
        g.sample(n=min(quota[div], len(g)), random_state=seed)
        for div, g in corpus.groupby("division")
    ]
    return pd.concat(parts).sort_values("nco2015").reset_index(drop=True)
