"""O*NET benchmark for RQ2: an India-independent digital intensity, mapped to NCO codes.

Two kinds of O*NET measure are built:
1. Same instrument: an O*NET corpus (description + core task statements) scored with
   the identical LLM prompt as the NCO corpus (`dti score --corpus onet`). The India-US
   gap then reflects the occupation texts, not a different method.
2. Conventional: keyword share of digital core tasks (Stöllinger & Guarascio 2025),
   "Working with Computers", "Computers and Electronics", e-mail frequency, and a
   Muro et al. (2017)-style 0-100 score.

Mapping: O*NET-SOC 2019 -> O*NET-SOC 2010 (O*NET taxonomy crosswalk) -> SOC 2010
6-digit -> ISCO-08 4-digit (BLS crosswalk) = NCO-2015 family. Each O*NET occupation's
weight is its US employment (OEWS, SOC 2018 = first 7 characters of O*NET-SOC 2019),
shared equally among O*NET occupations in the same SOC and among the ISCO codes it maps to.
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .baseline import _ANY as DIGITAL_KEYWORDS

CODE = "onetsoc"


# --- download -------------------------------------------------------------------

def download(cfg: dict[str, Any], root: Path) -> list[Path]:
    raw = root / cfg["raw_dir"]
    raw.mkdir(parents=True, exist_ok=True)
    v = cfg["version"].replace(".", "_")
    targets = [(cfg["base_url"].format(v=v, file=f), raw / f"{f}.csv") for f in cfg["files"]]
    targets.append((cfg["taxonomy_crosswalk_url"], raw / "2010_to_2019_Crosswalk.csv"))
    paths = []
    for url, path in targets:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(path, "wb") as f:
            f.write(resp.read())
        if path.stat().st_size < 5000 and b"Access Denied" in path.read_bytes():
            raise RuntimeError(f"download blocked: {url}")
        paths.append(path)
    return paths


def _read(raw: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(raw / f"{name}.csv", dtype=str)


# --- corpus for the LLM ---------------------------------------------------------------

def build_corpus(raw: Path) -> pd.DataFrame:
    """One row per O*NET occupation: description followed by its core task statements
    (all tasks when none are flagged core). Occupations without tasks are dropped."""
    occ = _read(raw, "occupation_data").rename(columns={"O*NET-SOC Code": CODE, "Title": "title", "Description": "summary"})
    tasks = _read(raw, "task_statements").rename(columns={"O*NET-SOC Code": CODE})
    core = tasks[tasks["Task Type"] == "Core"]
    use = pd.concat([core, tasks[~tasks[CODE].isin(core[CODE])]])
    joined = use.groupby(CODE)["Task"].agg(lambda s: " ".join(t.strip().rstrip(".") + "." for t in s))
    n_tasks = use.groupby(CODE).size()

    df = occ.merge(joined.rename("tasks"), on=CODE, how="inner")
    df["description"] = df["summary"].str.strip() + " " + df["tasks"]
    df["n_tasks"] = df[CODE].map(n_tasks)
    df["code"] = df[CODE]
    return df[["code", CODE, "title", "description", "n_tasks"]].reset_index(drop=True)


# --- conventional measures ----------------------------------------------------------------

def _item(raw: Path, item: dict[str, str], scale: str) -> pd.Series:
    df = _read(raw, item["file"])
    df = df[(df["Element ID"] == item["element"]) & (df["Scale ID"] == scale)]
    return pd.to_numeric(df.set_index("O*NET-SOC Code")["Data Value"], errors="coerce").groupby(level=0).mean()


def _scale_0_100(x: pd.Series) -> pd.Series:
    lo, hi = x.min(), x.max()
    return 100 * (x - lo) / (hi - lo) if hi > lo else x * 0.0


def measures(raw: Path, items: dict[str, dict[str, str]]) -> pd.DataFrame:
    tasks = _read(raw, "task_statements")
    core = tasks[tasks["Task Type"] == "Core"].copy()
    core["digital"] = core["Task"].fillna("").str.contains(DIGITAL_KEYWORDS)
    g = core.groupby("O*NET-SOC Code")["digital"]
    out = pd.DataFrame({"kw_share_core": g.mean(), "n_core_tasks": g.size(), "n_digital_tasks": g.sum()})

    for key in ("wa_computers", "kn_computers"):
        out[f"{key}_im"] = _item(raw, items[key], "IM")
        out[f"{key}_lv"] = _item(raw, items[key], "LV")
    out["cx_email"] = _item(raw, items["cx_email"], items["cx_email"].get("scale", "CX"))

    # Muro et al. (2017)-style: importance x level of the two computer items, each 0-100, averaged
    out["muro_0_100"] = (
        _scale_0_100(out["wa_computers_im"] * out["wa_computers_lv"])
        + _scale_0_100(out["kn_computers_im"] * out["kn_computers_lv"])
    ) / 2
    out.index.name = CODE
    return out.reset_index()


# --- crosswalk to ISCO-08 / NCO-2015 family ---------------------------------------------

def _find_header(raw: pd.DataFrame, patterns: list[str]) -> int:
    for i, row in raw.head(30).iterrows():
        cells = [str(c).lower() for c in row if pd.notna(c)]
        if all(any(re.search(p, c) for c in cells) for p in patterns):
            return i
    raise ValueError(f"no header row matching {patterns}")


def _check_not_html(path: Path) -> None:
    head = path.read_bytes()[:2000].lower()
    if head.lstrip().startswith(b"<!doctype") or b"access denied" in head:
        raise ValueError(f"{path} is a web page, not the BLS file (scripted download was blocked); download it in a browser")


def read_isco_soc(path: Path) -> pd.DataFrame:
    """BLS ISCO-08 <-> SOC 2010 crosswalk -> pairs (isco08, soc2010). Finds the header row itself."""
    _check_not_html(path)
    sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=str)
    for raw in sheets.values():
        try:
            h = _find_header(raw, [r"isco.*code", r"soc.*code"])
        except ValueError:
            continue
        df = raw.iloc[h + 1 :].copy()
        df.columns = [str(c).strip().lower() for c in raw.iloc[h]]
        isco_col = next(c for c in df.columns if "isco" in c and "code" in c)
        soc_col = next(c for c in df.columns if "soc" in c and "code" in c)
        pairs = pd.DataFrame({"isco08": df[isco_col], "soc2010": df[soc_col]}).dropna()
        pairs["isco08"] = pairs["isco08"].str.extract(r"(\d{4})")[0]
        pairs["soc2010"] = pairs["soc2010"].str.extract(r"(\d{2}-\d{4})")[0]
        return pairs.dropna().drop_duplicates().reset_index(drop=True)
    raise ValueError(f"{path}: no sheet with ISCO and SOC code columns")


def read_oews(path: Path) -> pd.Series:
    """OEWS national file -> employment by SOC 2018 detailed code."""
    _check_not_html(path)
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    if "o_group" in df:
        df = df[df["o_group"].str.lower() == "detailed"]
    emp = pd.to_numeric(df["tot_emp"].str.replace(",", ""), errors="coerce")
    return pd.Series(emp.values, index=df["occ_code"].str.strip(), name="emp").dropna().groupby(level=0).sum()


def onet_isco_links(raw: Path, isco_soc: pd.DataFrame, oews: pd.Series | None = None) -> pd.DataFrame:
    """Rows (onetsoc, isco08, weight). Weights sum, per O*NET occupation, to its US employment
    share (or to 1 each when OEWS is not available)."""
    walk = pd.read_csv(raw / "2010_to_2019_Crosswalk.csv", dtype=str)
    walk = walk.rename(columns={"O*NET-SOC 2019 Code": CODE, "O*NET-SOC 2010 Code": "onet2010"})
    walk["soc2010"] = walk["onet2010"].str[:7]
    links = walk[[CODE, "soc2010"]].merge(isco_soc, on="soc2010")[[CODE, "isco08"]].drop_duplicates()

    links["soc2018"] = links[CODE].str[:7]
    if oews is not None:
        n_same_soc = links.groupby("soc2018")[CODE].transform("nunique")
        base = links["soc2018"].map(oews) / n_same_soc
    else:
        base = pd.Series(1.0, index=links.index)
    links["weight"] = base / links.groupby(CODE)["isco08"].transform("nunique")
    return links[[CODE, "isco08", "weight"]]


def to_isco(values: pd.DataFrame, links: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Employment-weighted mean of O*NET-level columns at ISCO-08 4-digit."""
    df = links.merge(values, on=CODE)
    df = df[df["weight"].notna() & (df["weight"] > 0)]
    rows = {}
    for isco, g in df.groupby("isco08"):
        row = {"n_onet": g[CODE].nunique(), "us_emp_weight": g["weight"].sum()}
        for c in cols:
            ok = g[c].notna()
            row[c] = np.average(g.loc[ok, c], weights=g.loc[ok, "weight"]) if ok.any() else np.nan
        rows[isco] = row
    out = pd.DataFrame.from_dict(rows, orient="index")
    out.index.name = "isco08"
    return out.reset_index()
