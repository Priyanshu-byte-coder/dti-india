"""Synthetic PLFS-like rounds for testing the PLFS and econometrics code without microdata.

The data are fake: a known DTI wage premium (0.10 log points per SD, smaller for women
and rural workers) is built in so the estimators can be checked. Never report results
from these files.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

TRUE_PREMIUM = 0.10
FEMALE_SHIFT = -0.04
RURAL_SHIFT = -0.03

IDENTITY_COLUMNS = {
    "state": "state", "district": "district", "sector": "sector", "sex": "sex", "age": "age",
    "cws_status": "cws_status", "occ3": "occ3", "nic": "nic", "gen_edu": "gen_edu", "mult": "mult",
    "nss": "nss", "nsc": "nsc", "quarter": "quarter", "fsu": "fsu", "marital": "marital",
    "social_group": "social_group", "religion": "religion", "relation": "relation",
    "hhid_parts": ["fsu", "hh_no"], "earn_regular": "earn_regular", "earn_casual": "earn_casual",
    "earn_self": "earn_self", "hours": "hours", "contract": "contract", "paid_leave": "paid_leave",
    "social_security": "social_security",
}


def synth_round(occ_dti: pd.Series, year: int, n_households: int, seed: int) -> pd.DataFrame:
    """occ_dti: DTI z-score indexed by 3-digit occupation code."""
    rng = np.random.default_rng(seed)
    rows = []
    codes = occ_dti.index.to_numpy()
    for hh in range(n_households):
        fsu = hh // 8
        state = rng.integers(1, 37)
        sector = rng.choice([1, 2], p=[0.65, 0.35])
        size = rng.integers(2, 7)
        for p in range(size):
            age = int(rng.integers(0, 75)) if p else int(rng.integers(25, 70))
            rows.append({"fsu": fsu, "hh_no": hh, "state": state, "district": f"{state}{rng.integers(1, 20):02d}",
                         "sector": sector, "relation": 1 if p == 0 else rng.choice([2, 3, 4]),
                         "sex": rng.choice([1, 2]), "age": age})
    df = pd.DataFrame(rows)
    n = len(df)
    df["quarter"] = rng.integers(1, 5, n)
    df["mult"] = rng.uniform(5_000, 50_000, n).round()
    df["nss"] = rng.choice([1, 2], n, p=[0.3, 0.7])
    df["nsc"] = 2
    df["marital"] = np.where(df["age"] > 22, rng.choice([1, 2], n, p=[0.2, 0.8]), 1)
    df["social_group"] = rng.choice([1, 2, 3, 9], n)
    df["religion"] = rng.choice([1, 2, 3, 9], n, p=[0.8, 0.14, 0.03, 0.03])
    edu = rng.choice([1, 5, 6, 7, 8, 10, 11, 12, 13], n, p=[0.2, 0.1, 0.1, 0.12, 0.13, 0.13, 0.04, 0.13, 0.05])
    df["gen_edu"] = edu
    years_edu = pd.Series(edu).map({1: 0, 5: 3, 6: 5, 7: 8, 8: 10, 10: 12, 11: 13, 12: 15, 13: 17}).to_numpy()

    female = (df["sex"] == 2).to_numpy()
    working_age = (df["age"] >= 15) & (df["age"] <= 64)
    hh_kids = df.groupby("hh_no")["age"].transform(lambda a: (a < 6).sum()).to_numpy()
    p_work = 1 / (1 + np.exp(-(1.2 - 1.8 * female + 0.08 * years_edu - 0.35 * female * hh_kids)))
    works = working_age.to_numpy() & (rng.uniform(size=n) < p_work)
    status = np.where(works, rng.choice([11, 21, 31, 51], n, p=[0.3, 0.1, 0.3, 0.3]), 92)
    df["cws_status"] = status

    # occupation: more educated workers sort into higher-DTI occupations
    ranks = np.argsort(np.argsort(occ_dti.to_numpy()))
    pick = []
    for y in years_edu:
        w = np.exp(0.25 * y * ranks / len(ranks))
        pick.append(rng.choice(codes, p=w / w.sum()))
    df["occ3"] = np.where(works, pick, "")
    df["nic"] = np.where(works, rng.integers(1, 99, n).astype(str).astype(object), "")
    df["nic"] = [f"{int(x):02d}{rng.integers(0, 999):03d}" if x else "" for x in df["nic"]]

    dti = pd.Series(df["occ3"]).map(occ_dti).fillna(0).to_numpy()
    rural = (df["sector"] == 1).to_numpy()
    beta = TRUE_PREMIUM + FEMALE_SHIFT * female + RURAL_SHIFT * rural
    ln_w = (3.0 + 0.06 * years_edu + 0.03 * (df["age"] - 15) - 0.0004 * (df["age"] - 15) ** 2
            - 0.2 * female - 0.15 * rural + beta * dti + 0.03 * (year - 2017) + rng.normal(0, 0.45, n))
    hours = rng.integers(20, 60, n).astype(float)
    wage = np.exp(ln_w)
    df["hours"] = np.where(works, hours, np.nan)
    df["earn_regular"] = np.where(status == 31, (wage * hours * 4.33).round(), np.nan)
    df["earn_casual"] = np.where(status == 51, (wage * hours).round(), np.nan)
    df["earn_self"] = np.where(np.isin(status, [11]), (wage * hours * 30 / 7).round(), np.nan)
    df["contract"] = np.where(status == 31, rng.choice([1, 2, 4], n), np.nan)
    df["paid_leave"] = np.where(status == 31, rng.choice([1, 2], n), np.nan)
    df["social_security"] = np.where(status == 31, rng.choice([1, 8], n), np.nan)
    return df


def write_synthetic(dti_2015: pd.DataFrame, dti_2004: pd.DataFrame, out_dir: Path, n_households: int = 3000) -> dict:
    """Write two fake rounds (one per NCO system) and return a matching plfs config."""
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = [("2019-20", 2019, "nco2004", dti_2004.set_index("nco2004_g3")["dti_z"]),
            ("2022-23", 2022, "nco2015", dti_2015.set_index("group3")["dti_z"])]
    rounds = {}
    for i, (name, year, system, occ_dti) in enumerate(plan):
        path = out_dir / f"synthetic_{name}.csv"
        synth_round(occ_dti, year, n_households, seed=100 + i).to_csv(path, index=False)
        rounds[name] = {"year": year, "occ_system": system, "format": "csv", "files": [str(path)], "columns": IDENTITY_COLUMNS}
    return rounds
