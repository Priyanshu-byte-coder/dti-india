"""NCO-2015 -> NCO-2004 link, so the DTI can be merged onto pre-July-2021 PLFS rounds.

PLFS records 3-digit NCO-2004 up to June 2021 and 3-digit NCO-2015 from July 2021.
The coder form carries the NCO-2004 6-digit concordance code from NCO-2015 Vol I for
about 77% of 8-digit occupations; the rest are occupations new in 2015. For those we
borrow the most common NCO-2004 code of their siblings: first within the same NCO-2015
family (4-digit), then within the same group (3-digit). Every link is tagged so the
fallback links can be dropped in robustness checks.
"""

from __future__ import annotations

import pandas as pd

LINK_ORDER = ("direct", "family_mode", "group_mode", "none")


def _mode(s: pd.Series) -> str:
    s = s[s != ""]
    return s.mode().sort_values().iloc[0] if len(s) else ""


def nco2004_link(corpus: pd.DataFrame) -> pd.DataFrame:
    df = corpus[["nco2015", "family4", "group3", "nco2004"]].copy()
    df["nco2004"] = df["nco2004"].fillna("")
    df["link"] = (df["nco2004"] != "").map({True: "direct", False: "none"})

    fam = df.groupby("family4")["nco2004"].agg(_mode)
    grp = df.groupby("group3")["nco2004"].agg(_mode)

    need = df["link"] == "none"
    df.loc[need, "nco2004"] = df.loc[need, "family4"].map(fam)
    df.loc[need & (df["nco2004"] != ""), "link"] = "family_mode"

    need = df["link"] == "none"
    df.loc[need, "nco2004"] = df.loc[need, "group3"].map(grp)
    df.loc[need & (df["nco2004"] != ""), "link"] = "group_mode"

    df["nco2004_g3"] = df["nco2004"].str[:3]
    return df[["nco2015", "nco2004", "nco2004_g3", "link"]]
