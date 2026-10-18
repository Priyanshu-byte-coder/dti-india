"""PLFS harmonisation across rounds and the DTI merge.

Rounds before July 2021 record 3-digit NCO-2004 and later rounds 3-digit NCO-2015, so
each worker gets the DTI from the file that matches the round's occupation system.
Raw column names differ between rounds; configs/plfs.yaml maps them to standard names.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED = ["state", "sector", "sex", "age", "cws_status", "occ3", "nic", "gen_edu", "mult"]
DTI_COLS = ["dti_z", "dti_0_100", "dti_mean_score", "D1", "D2", "D3", "D4", "D5"]


# --- reading ----------------------------------------------------------------------

def _read_file(path: Path, fmt: str, layout: Path | None) -> pd.DataFrame:
    if fmt == "csv":
        return pd.read_csv(path, dtype=str, low_memory=False)
    if fmt == "tsv":
        return pd.read_csv(path, sep="\t", dtype=str, low_memory=False)
    if fmt == "parquet":
        return pd.read_parquet(path).astype(str)
    if fmt == "dta":
        return pd.read_stata(path, convert_categoricals=False).astype(str)
    if fmt == "fwf":
        lay = pd.read_csv(layout)
        colspecs = [(int(s) - 1, int(s) - 1 + int(w)) for s, w in zip(lay["start"], lay["width"])]
        return pd.read_fwf(path, colspecs=colspecs, names=list(lay["name"]), dtype=str)
    raise ValueError(f"unknown format {fmt}")


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.strip().replace({"": None, "nan": None}), errors="coerce")


def read_round(name: str, rcfg: dict[str, Any], root: Path) -> pd.DataFrame:
    layout = root / rcfg["layout"] if rcfg.get("layout") else None
    raw = pd.concat([_read_file(root / f, rcfg["format"], layout) for f in rcfg["files"]], ignore_index=True)
    cols = rcfg["columns"]
    missing = [k for k in REQUIRED if k not in cols]
    if missing:
        raise ValueError(f"round {name}: configs/plfs.yaml has no column mapping for {missing}")

    out = pd.DataFrame(index=raw.index)
    for std, src in cols.items():
        if std == "hhid_parts":
            out["hhid"] = raw[src].astype(str).agg("-".join, axis=1)
        elif isinstance(src, list):  # sum of several raw columns (daily hours / earnings)
            out[std] = sum(_num(raw[c]).fillna(0) for c in src)
            out.loc[raw[src].isna().all(axis=1), std] = np.nan
        else:
            out[std] = raw[src]
    out["round"] = name
    out["year"] = rcfg["year"]
    out["occ_system"] = rcfg["occ_system"]
    return out


# --- harmonising ----------------------------------------------------------------------

def _in(s: pd.Series, codes: list[int]) -> pd.Series:
    return _num(s).isin(codes)


def _category(s: pd.Series, mapping: dict[str, list[int]]) -> pd.Series:
    x = _num(s)
    out = pd.Series(pd.NA, index=s.index, dtype="object")
    for label, codes in mapping.items():
        out[x.isin(codes)] = label
    return out


def harmonise(df: pd.DataFrame, cfg: dict[str, Any], cpi: pd.DataFrame | None = None) -> pd.DataFrame:
    codes, wcfg = cfg["codes"], cfg["wages"]
    h = pd.DataFrame(index=df.index)
    for c in ["round", "year", "occ_system", "state"]:
        h[c] = df[c]
    for c in ["district", "fsu", "stratum", "hhid"]:
        if c in df:
            h[c] = df[c]
    h["quarter"] = df["quarter"] if "quarter" in df else "1"
    h["yq"] = h["year"].astype(str) + "Q" + h["quarter"].astype(str).str.strip()

    h["age"] = _num(df["age"])
    h["age2"] = h["age"] ** 2 / 100
    h["female"] = _in(df["sex"], [codes["sex"]["female"]]).astype(int)
    h["rural"] = _in(df["sector"], [codes["sector"]["rural"]]).astype(int)
    h["sector"] = np.where(h["rural"] == 1, "rural", "urban")
    h["edu_cat"] = _category(df["gen_edu"], codes["gen_edu"])
    band = {cat: b for b, cats in codes["edu_band"].items() for cat in cats}
    h["edu_band"] = h["edu_cat"].map(band)
    h["married"] = _in(df["marital"], codes["marital"]["currently_married"]).astype(int) if "marital" in df else 0
    for c in ["social_group", "religion"]:
        h[c] = _num(df[c]).astype("Int64").astype(str) if c in df else "NA"
    h["age_band"] = pd.cut(h["age"], [14, 24, 34, 44, 54, 64, 200], labels=["15-24", "25-34", "35-44", "45-54", "55-64", "65+"]).astype(str)

    # employment type from CWS status
    status = _num(df["cws_status"])
    h["emp_type"] = "other"
    for label in ("self_employed", "regular", "casual", "unemployed"):
        h.loc[status.isin(codes["status"][label]), "emp_type"] = label
    h["wage_employed"] = h["emp_type"].isin(["regular", "casual"]).astype(int)

    # occupation and industry
    occ = df["occ3"].astype(str).str.extract(r"(\d+)")[0]
    h["occ3"] = occ.str.zfill(3).str[:3]
    h["division"] = h["occ3"].str[0]
    h["occ_cluster"] = h["occ_system"] + ":" + h["occ3"]
    h["nic2"] = df["nic"].astype(str).str.extract(r"(\d+)")[0].str.zfill(5).str[:2]

    # formality (regular wage workers only; NaN for others)
    reg = h["emp_type"] == "regular"
    if "social_security" in df:
        h["formal_ss"] = np.where(reg, _in(df["social_security"], codes["social_security_yes"]).astype(float), np.nan)
    if {"contract", "paid_leave", "social_security"} <= set(df.columns):
        strict = (
            _in(df["contract"], codes["contract_written"])
            & _in(df["paid_leave"], codes["paid_leave_yes"])
            & _in(df["social_security"], codes["social_security_yes"])
        )
        h["formal_strict"] = np.where(reg, strict.astype(float), np.nan)

    # household variables for selection models
    if "hhid" in h:
        key = h["round"] + "|" + h["hhid"]
        h["hh_size"] = key.map(key.value_counts())
        h["hh_children_u6"] = key.map((h["age"] < 6).groupby(key).sum())
    if "relation" in df:
        h["hh_head"] = _in(df["relation"], codes["relation"]["head"]).astype(int)

    # weights
    mult = _num(df["mult"])
    if cfg["weights"]["rule"] == "plfs_standard" and {"nss", "nsc"} <= set(df.columns):
        h["weight"] = np.where(_num(df["nss"]) == _num(df["nsc"]), mult / 100, mult / 200)
    else:
        h["weight"] = mult / 100

    # earnings and hours
    hours = _num(df["hours"]) if "hours" in df else pd.Series(np.nan, index=df.index)
    h["hours_week"] = hours.where(hours > 0)
    wpm = wcfg["weeks_per_month"]
    earn = pd.Series(np.nan, index=df.index)
    month = pd.Series(np.nan, index=df.index)
    if "earn_regular" in df:
        e = _num(df["earn_regular"])
        earn = earn.mask(reg, e / (h["hours_week"] * wpm))
        month = month.mask(reg, e)
    if "earn_casual" in df:
        cas = h["emp_type"] == "casual"
        e = _num(df["earn_casual"])
        earn = earn.mask(cas, e / h["hours_week"])
        month = month.mask(cas, e * wpm)
    if "earn_self" in df:
        se = h["emp_type"] == "self_employed"
        e = _num(df["earn_self"])
        weeks = wcfg["self_days"] / 7
        earn = earn.mask(se, e / (h["hours_week"] * weeks))
        month = month.mask(se, e * wpm / weeks)
    h["hourly_wage"] = earn.where(earn > 0)
    h["monthly_earnings"] = month.where(month > 0)

    # deflate to base-year prices
    h["deflator"] = 1.0
    if cpi is not None:
        c = cpi.copy()
        c["state"] = c["state"].astype(str)
        c["year"] = c["year"].astype(int)
        base = c[c["year"] == cfg["deflator"]["base_year"]].set_index(["state", "sector"])["cpi"]
        c["deflator"] = c.set_index(["state", "sector"]).index.map(base) / c["cpi"]
        m = h[["state", "sector", "year"]].astype({"state": str, "year": int}).merge(
            c[["state", "sector", "year", "deflator"]], on=["state", "sector", "year"], how="left"
        )
        h["deflator"] = m["deflator"].fillna(1.0).to_numpy()
    h["real_hourly_wage"] = h["hourly_wage"] * h["deflator"]
    h["real_monthly_earnings"] = h["monthly_earnings"] * h["deflator"]

    # trim hourly-wage outliers within each round
    lo, hi = wcfg["trim_pct"]
    q = h.groupby("round")["real_hourly_wage"].transform(lambda s: s.quantile(lo / 100))
    q2 = h.groupby("round")["real_hourly_wage"].transform(lambda s: s.quantile(hi / 100))
    h["wage_trimmed"] = ((h["real_hourly_wage"] < q) | (h["real_hourly_wage"] > q2)).astype(int)
    h["ln_real_hourly_wage"] = np.log(h["real_hourly_wage"].where(h["wage_trimmed"] == 0))
    h["ln_real_monthly_earnings"] = np.log(h["real_monthly_earnings"])
    return h


# --- DTI merge --------------------------------------------------------------------------

def attach_dti(h: pd.DataFrame, dti_2015: pd.DataFrame, dti_2004: pd.DataFrame) -> pd.DataFrame:
    """Give each worker the DTI of their 3-digit occupation in the round's NCO system."""
    a = dti_2015.rename(columns={"group3": "occ3"})[["occ3", *DTI_COLS]].assign(occ_system="nco2015")
    b = dti_2004.rename(columns={"nco2004_g3": "occ3"})[["occ3", *DTI_COLS]].assign(occ_system="nco2004")
    if "share_direct_link" in dti_2004:
        b["share_direct_link"] = dti_2004["share_direct_link"].to_numpy()
    lookup = pd.concat([a, b], ignore_index=True)
    lookup["occ3"] = lookup["occ3"].astype(str).str.zfill(3)
    out = h.merge(lookup, on=["occ_system", "occ3"], how="left", validate="many_to_one")
    out["dti_matched"] = out["dti_z"].notna().astype(int)
    return out


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    """Share of employed workers (by weight) whose occupation found a DTI, per round."""
    emp = df[df["emp_type"].isin(["regular", "casual", "self_employed"])]
    g = emp.groupby("round")
    return pd.DataFrame({
        "n_employed": g.size(),
        "share_matched_weighted": g.apply(lambda x: np.average(x["dti_matched"], weights=x["weight"])),
        "unmatched_codes": g.apply(lambda x: ",".join(sorted(x.loc[x["dti_matched"] == 0, "occ3"].dropna().unique())[:20])),
    }).reset_index()
