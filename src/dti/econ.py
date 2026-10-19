"""Wage models for RQ3 (conditional digital occupational premium) and RQ4 (heterogeneity).

ln w_i = a + b DTI_j(i) + g X_i + FE + e_i, clustered by occupation (DTI varies only
across ~110-120 occupation groups per NCO system). b is a conditional association,
not a causal return; Oster bounds quantify how much selection on unobservables would
be needed to explain it away.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd
import pyfixest as pf
import statsmodels.api as sm
from scipy.stats import gaussian_kde, norm

DIMS_STD = ["D1_std", "D2_std", "D3_std", "D4_std", "D5_std"]


# --- sample ------------------------------------------------------------------------

def weighted_std(x: pd.Series, w: pd.Series) -> pd.Series:
    mu = np.average(x, weights=w)
    sd = np.sqrt(np.average((x - mu) ** 2, weights=w))
    return (x - mu) / sd


def analysis_sample(df: pd.DataFrame, cfg: dict[str, Any], outcome: str | None = None,
                    emp_types: list[str] | None = None) -> pd.DataFrame:
    s = cfg["sample"]
    y = outcome or s["outcome"]
    keep = (
        df["age"].between(s["age_min"], s["age_max"])
        & df["emp_type"].isin(emp_types or s["emp_types"])
        & (df["dti_matched"] == 1)
        & df[y].notna()
        & (df["weight"] > 0)
    )
    if s.get("rounds"):
        keep &= df["round"].isin(s["rounds"])
    out = df[keep].copy()
    out["occ_cluster_id"] = pd.factorize(out["occ_cluster"])[0]  # integer ids for the wild bootstrap
    # standardise across workers in the analysis sample, so b = premium per worker-SD of DTI
    out["dti_std"] = weighted_std(out["dti_z"], out["weight"])
    for d in ["D1", "D2", "D3", "D4", "D5"]:
        out[f"{d}_std"] = weighted_std(out[d], out["weight"]) if out[d].nunique() > 1 else 0.0
    out["dti_quintile"] = pd.qcut(out["dti_std"].rank(method="first"), 5, labels=False) + 1
    for q in range(2, 6):
        out[f"dti_q{q}"] = (out["dti_quintile"] == q).astype(int)
    for band, label in [("middle_secondary", "edu_middle_secondary"), ("tertiary", "edu_tertiary")]:
        out[label] = (out["edu_band"] == band).astype(int)
    out["casual"] = (out["emp_type"] == "casual").astype(int)
    out["age_15_24"] = (out["age"] < 25).astype(int)
    out["age_45_64"] = (out["age"] >= 45).astype(int)
    return out


# --- OLS with fixed effects ---------------------------------------------------------------

def formula(y: str, terms: list[str], controls: list[str], fe: list[str]) -> str:
    rhs = " + ".join(dict.fromkeys([*terms, *controls]))
    return f"{y} ~ {rhs}" + (f" | {' + '.join(fe)}" if fe else "")


def fit(df: pd.DataFrame, fml: str, cluster: str, weights: str | None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = pf.feols(fml, data=df, vcov={"CRV1": cluster}, weights=weights)
    model.n_clusters = df[cluster].nunique()
    return model


def tidy(model, label: str, terms: list[str], **extra) -> pd.DataFrame:
    t = model.tidy()
    t = t[t.index.isin(terms)].reset_index().rename(columns={
        "Coefficient": "term", "Estimate": "coef", "Std. Error": "se", "Pr(>|t|)": "p", "2.5%": "ci_low", "97.5%": "ci_high",
    })
    t.insert(0, "model", label)
    t["n"] = model._N
    t["r2"] = getattr(model, "_r2", np.nan)
    t["r2_within"] = getattr(model, "_r2_within", np.nan)
    t["n_clusters"] = getattr(model, "n_clusters", np.nan)
    for k, v in extra.items():
        t[k] = v
    return t[["model", "term", "coef", "se", "p", "ci_low", "ci_high", "n", "n_clusters", "r2", "r2_within", *extra]]


def run_spec(df: pd.DataFrame, cfg: dict[str, Any], name: str, y: str | None = None,
             weights: str | None | bool = True, label: str | None = None, extra_terms: list[str] | None = None):
    spec = cfg["specs"][name]
    y = y or cfg["sample"]["outcome"]
    terms = [*spec["terms"], *(extra_terms or [])]
    controls = cfg["controls"] if spec["controls"] else []
    w = cfg["weights"] if weights is True else (weights or None)
    model = fit(df, formula(y, terms, controls, cfg["fe_sets"][spec["fe"]]), cfg["cluster"], w)
    return model, tidy(model, label or name, terms, outcome=y, weighted=bool(w))


def baseline(df: pd.DataFrame, cfg: dict[str, Any]) -> tuple[pd.DataFrame, dict]:
    rows, models = [], {}
    for name, spec in cfg["specs"].items():
        if all(df[t].nunique() <= 1 for t in spec["terms"]):
            continue  # e.g. the per-dimension model when the DTI has no dimensions (O*NET benchmark)
        models[name], t = run_spec(df, cfg, name)
        rows.append(t)
    return pd.concat(rows, ignore_index=True), models


# --- robustness -----------------------------------------------------------------------------

def robustness(df_all: pd.DataFrame, df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    p = cfg["preferred"]
    rows = []
    rows.append(run_spec(df, cfg, p, weights=False, label=f"{p} unweighted")[1])

    m, t = run_spec(df, {**cfg, "cluster": "occ_cluster_id"}, p, weights=False, label=f"{p} unweighted, wild cluster bootstrap")
    try:
        wb = m.wildboottest(param="dti_std", reps=cfg["wild_bootstrap_reps"], seed=1)
        t["p"] = float(wb["Pr(>|t|)"])
        t["note"] = "p from wild cluster bootstrap (WCR11)"
    except Exception as e:  # wildboottest not installed or unsupported
        t["note"] = f"wild bootstrap failed: {e}"
    rows.append(t)

    alt_y = "ln_real_monthly_earnings"
    s2 = analysis_sample(df_all, cfg, outcome=alt_y)
    rows.append(run_spec(s2, cfg, p, y=alt_y, label=f"{p} monthly earnings")[1])

    for label, mask in [
        ("regular wage workers only", df["emp_type"] == "regular"),
        ("casual workers only", df["emp_type"] == "casual"),
        ("NCO-2015 rounds (Jul 2021+)", df["occ_system"] == "nco2015"),
        ("NCO-2004 rounds (pre Jul 2021)", df["occ_system"] == "nco2004"),
    ]:
        sub = df[mask]
        if sub["occ_cluster"].nunique() > 10:
            rows.append(run_spec(sub, cfg, p, label=f"{p} {label}")[1])

    if "share_direct_link" in df:
        sub = df[(df["occ_system"] == "nco2015") | (df["share_direct_link"] >= 0.75)]
        rows.append(run_spec(sub, cfg, p, label=f"{p} NCO-2004 groups with >=75% direct links")[1])

    spec = cfg["specs"][p]
    q_terms = ["dti_q2", "dti_q3", "dti_q4", "dti_q5"]
    m = fit(df, formula(cfg["sample"]["outcome"], q_terms, cfg["controls"], cfg["fe_sets"][spec["fe"]]), cfg["cluster"], cfg["weights"])
    rows.append(tidy(m, f"{p} DTI quintiles (base Q1)", q_terms))

    se_sub = analysis_sample(df_all, cfg, emp_types=["self_employed"])
    if len(se_sub) > 100 and se_sub["occ_cluster"].nunique() > 10:
        rows.append(run_spec(se_sub, cfg, p, label=f"{p} self-employed (earnings incl. capital returns)")[1])
    return pd.concat(rows, ignore_index=True)


# --- selection (Heckman two-step) --------------------------------------------------------------

def heckman(df_all: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """Selection into wage employment with a valid wage, among working-age persons.
    Second-step SEs are clustered but not corrected for the generated regressor."""
    s = cfg["sample"]
    excl = [c for c in cfg["selection"]["exclusions"] if c in df_all]
    pop = df_all[df_all["age"].between(s["age_min"], s["age_max"])].copy()
    pop["selected"] = (
        pop["emp_type"].isin(s["emp_types"]) & pop[s["outcome"]].notna() & (pop["dti_matched"] == 1)
    ).astype(int)
    rows = []
    for label, sub in [("all", pop), ("men", pop[pop["female"] == 0]), ("women", pop[pop["female"] == 1])]:
        X = pd.concat([
            sub[[c for c in cfg["controls"] if sub[c].nunique() > 1] + excl].astype(float),
            pd.get_dummies(sub[["edu_cat", "yq"]].astype(str), drop_first=True, dtype=float),
        ], axis=1)
        X = sm.add_constant(X)
        ok = X.notna().all(axis=1)
        probit = sm.Probit(sub.loc[ok, "selected"], X[ok]).fit(disp=False)
        xb = X[ok] @ probit.params
        sub = sub.loc[ok].assign(imr=norm.pdf(xb) / norm.cdf(xb))
        wage = analysis_sample(sub, cfg)
        _, t = run_spec(wage, cfg, cfg["preferred"], label=f"Heckman {label}", extra_terms=["imr"])
        t["exclusion_restrictions"] = ", ".join(excl)
        t["probit_exclusion_p"] = ", ".join(f"{c}={probit.pvalues[c]:.3g}" for c in excl)
        rows.append(t)
    return pd.concat(rows, ignore_index=True)


# --- distribution ------------------------------------------------------------------------------

def weighted_quantile(x: np.ndarray, w: np.ndarray, q: float) -> float:
    order = np.argsort(x)
    cw = np.cumsum(w[order])
    return float(x[order][np.searchsorted(cw, q * cw[-1])])


def rif_regressions(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """Unconditional quantile (RIF) regressions, Firpo, Fortin & Lemieux (2009)."""
    y_col = cfg["sample"]["outcome"]
    y, w = df[y_col].to_numpy(), df[cfg["weights"]].to_numpy()
    sample = np.random.default_rng(0).choice(len(y), size=min(len(y), 50_000), replace=False)
    kde = gaussian_kde(y[sample], weights=w[sample])
    rows = []
    for tau in cfg["quantiles"]:
        q = weighted_quantile(y, w, tau)
        f = float(kde(q)[0])
        d = df.assign(rif=q + (tau - (y <= q)) / f)
        _, t = run_spec(d, cfg, cfg["preferred"], y="rif", label=f"RIF q{int(tau * 100)}")
        t["quantile"] = tau
        rows.append(t)
    return pd.concat(rows, ignore_index=True)


def conditional_quantiles(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """Conditional quantile regression on a random subsample (statsmodels QuantReg is slow).
    Controls + education, year-quarter and division dummies; state/industry FE omitted."""
    d = df.sample(n=min(len(df), cfg["cqr_max_obs"]), random_state=0)
    X = pd.concat([
        d[["dti_std", *[c for c in cfg["controls"] if d[c].nunique() > 1]]].astype(float),
        pd.get_dummies(d[["edu_cat", "yq", "division"]].astype(str), drop_first=True, dtype=float),
    ], axis=1)
    X = sm.add_constant(X)
    rows = []
    for tau in cfg["quantiles"]:
        r = sm.QuantReg(d[cfg["sample"]["outcome"]], X).fit(q=tau, max_iter=5000)
        ci = r.conf_int().loc["dti_std"]
        rows.append({"model": f"CQR q{int(tau * 100)}", "term": "dti_std", "coef": r.params["dti_std"],
                     "se": r.bse["dti_std"], "p": r.pvalues["dti_std"], "ci_low": ci[0], "ci_high": ci[1],
                     "n": len(d), "quantile": tau})
    return pd.DataFrame(rows)


# --- Oaxaca-Blinder ---------------------------------------------------------------------------

OAXACA_GROUPS = {
    "dti": ["dti_std"],
    "age": ["age", "age2"],
    "demographics": ["married", "rural"],
    "education": ["edu_cat"],
    "social group / religion": ["social_group", "religion"],
    "state": ["state"],
    "industry": ["nic2"],
    "time": ["yq"],
    "occupation division": ["division"],
}
OAXACA_CATEGORICAL = {"edu_cat", "social_group", "religion", "state", "nic2", "yq", "division"}


def _wls(X: np.ndarray, y: np.ndarray, w: np.ndarray) -> np.ndarray:
    sw = np.sqrt(w)
    return np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]


def oaxaca(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """Twofold decomposition of the gap between group 0 and group 1 (e.g. men - women),
    pooled reference coefficients with a group indicator (Neumark 1988 / Jann 2008)."""
    g = cfg["oaxaca"]["group"]
    y_col, w_col = cfg["sample"]["outcome"], cfg["weights"]
    all_cols = [c for cols in OAXACA_GROUPS.values() for c in cols]
    cat = [c for c in all_cols if c in OAXACA_CATEGORICAL]
    num = [c for c in all_cols if c not in OAXACA_CATEGORICAL]
    X = pd.concat([df[num].astype(float), pd.get_dummies(df[cat].astype(str), drop_first=True, dtype=float)], axis=1)
    X.insert(0, "const", 1.0)
    X = X.loc[:, X.std() > 0].assign(const=1.0)
    y, w, grp = df[y_col].to_numpy(), df[w_col].to_numpy(), df[g].to_numpy()

    b_pool = _wls(np.column_stack([X.to_numpy(), grp]), y, w)[:-1]
    a, b = grp == 0, grp == 1
    b_a, b_b = _wls(X.to_numpy()[a], y[a], w[a]), _wls(X.to_numpy()[b], y[b], w[b])
    xa = np.average(X.to_numpy()[a], axis=0, weights=w[a])
    xb = np.average(X.to_numpy()[b], axis=0, weights=w[b])

    rows = [
        {"component": "total gap", "value": float(np.average(y[a], weights=w[a]) - np.average(y[b], weights=w[b]))},
        {"component": "explained", "value": float((xa - xb) @ b_pool)},
        {"component": "unexplained", "value": float(xa @ (b_a - b_pool) + xb @ (b_pool - b_b))},
    ]
    for group, cols in OAXACA_GROUPS.items():
        idx = [i for i, c in enumerate(X.columns) if any(c == col or c.startswith(f"{col}_") for col in cols)]
        rows.append({"component": f"explained: {group}", "value": float((xa[idx] - xb[idx]) @ b_pool[idx])})
    out = pd.DataFrame(rows)
    out["group_0"] = f"{g}=0"
    out["group_1"] = f"{g}=1"
    return out


# --- Oster (2019) ------------------------------------------------------------------------------

def oster(beta_short: float, r_short: float, beta_long: float, r_long: float, rmax: float) -> dict[str, float]:
    """Approximate Oster (2019) bounds: delta that would drive beta to 0, and beta at delta = 1."""
    move_b, move_r = beta_short - beta_long, r_long - r_short
    delta = beta_long * move_r / (move_b * (rmax - r_long)) if move_b and rmax > r_long else np.nan
    beta_star = beta_long - move_b * (rmax - r_long) / move_r if move_r else np.nan
    return {"beta_uncontrolled": beta_short, "r2_uncontrolled": r_short, "beta_controlled": beta_long,
            "r2_controlled": r_long, "rmax": rmax, "delta_for_beta_0": delta, "beta_at_delta_1": beta_star}


def oster_table(models: dict, cfg: dict[str, Any]) -> pd.DataFrame:
    short, long = models["M1"], models[cfg["preferred"]]
    r_long = long._r2
    rmax = min(1.0, cfg["oster"]["rmax_multiplier"] * r_long)
    res = oster(short.coef()["dti_std"], short._r2, long.coef()["dti_std"], r_long, rmax)
    res["note"] = "approximate formula; R2 includes fixed effects in both models"
    return pd.DataFrame([res])


# --- heterogeneity -------------------------------------------------------------------------------

def _het_terms(df: pd.DataFrame, cfg: dict[str, Any]) -> tuple[pd.DataFrame, list[str], list[str]]:
    h = cfg["heterogeneity"]
    d = df.copy()
    inter, mains = [], []
    for v in h["binary"]:
        d[f"dti_x_{v}"] = d["dti_std"] * d[v]
        inter.append(f"dti_x_{v}")
    for v, base in h["categorical"].items():
        for level in sorted(d[v].dropna().unique()):
            if level == base:
                continue
            col = f"{v}_{level}".replace("-", "_").replace("+", "plus")
            d[col] = (d[v] == level).astype(int)
            d[f"dti_x_{col}"] = d["dti_std"] * d[col]
            mains.append(col)
            inter.append(f"dti_x_{col}")
    return d, inter, mains


def interactions(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """DTI x group interactions, with the preferred FE and with full occupation FE.
    With occupation FE the DTI main effect is absorbed but the interactions are still
    identified from within-occupation differences between groups."""
    d, inter, mains = _het_terms(df, cfg)
    y, spec = cfg["sample"]["outcome"], cfg["specs"][cfg["preferred"]]
    rows = []
    for label, fe, terms in [
        (f"{cfg['preferred']} + interactions", cfg["fe_sets"][spec["fe"]], ["dti_std", *inter]),
        ("occupation FE + interactions", cfg["fe_sets"]["occupation"], inter),
    ]:
        m = fit(d, formula(y, terms, [*cfg["controls"], *mains], fe), cfg["cluster"], cfg["weights"])
        rows.append(tidy(m, label, terms))

    f = cfg["heterogeneity"].get("formality")
    if f and f in d:
        reg = d[(d["emp_type"] == "regular") & d[f].notna()].assign(**{f"dti_x_{f}": lambda x: x["dti_std"] * x[f]})
        if reg["occ_cluster"].nunique() > 10:
            for label, fe, terms in [
                (f"{cfg['preferred']} + formality interaction (regular)", cfg["fe_sets"][spec["fe"]], ["dti_std", f"dti_x_{f}"]),
                ("occupation FE + formality interaction (regular)", cfg["fe_sets"]["occupation"], [f"dti_x_{f}"]),
            ]:
                m = fit(reg, formula(y, terms, [*cfg["controls"], f], fe), cfg["cluster"], cfg["weights"])
                rows.append(tidy(m, label, terms))
    return pd.concat(rows, ignore_index=True)


def subgroups(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    h, p = cfg["heterogeneity"], cfg["preferred"]
    rows = []
    groups = [(v, d) for v in [*h["binary"], *h["categorical"]] for _, d in df.groupby(v)]
    if h.get("formality") in df:
        groups += [(h["formality"], d) for _, d in df[df["emp_type"] == "regular"].groupby(h["formality"])]
    for var, sub in groups:
        if len(sub) < 200 or sub["occ_cluster"].nunique() < 10:
            continue
        level = sub[var].iloc[0]
        _, t = run_spec(sub, cfg, p, label=f"{p} | {var}={level}")
        t["group_var"], t["group_level"] = var, level
        rows.append(t)
    return pd.concat(rows, ignore_index=True)


def double_ml(df: pd.DataFrame, cfg: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Partially linear DML: average partial effect of DTI with flexible controls, then the
    best linear projection (BLP) of effect heterogeneity on pre-specified covariates and
    group average effects (GATE). Unweighted; nuisance learners are gradient boosting."""
    import doubleml as dml
    from sklearn.ensemble import HistGradientBoostingRegressor

    c = cfg["dml"]
    d = df.sample(n=min(len(df), c["max_obs"]), random_state=0).reset_index(drop=True)
    X = pd.concat([
        d[[x for x in cfg["controls"] if d[x].nunique() > 1]].astype(float),
        pd.get_dummies(d[["edu_cat", "social_group", "religion", "state", "nic2", "yq", "division"]].astype(str), drop_first=True, dtype=float),
    ], axis=1)
    X.columns = [f"x{i}" for i in range(X.shape[1])]
    data = pd.concat([d[[cfg["sample"]["outcome"], "dti_std"]].reset_index(drop=True), X], axis=1)
    obj = dml.DoubleMLData(data, y_col=cfg["sample"]["outcome"], d_cols="dti_std", x_cols=list(X.columns))
    learner = HistGradientBoostingRegressor(max_iter=c["max_iter"], random_state=0)
    plr = dml.DoubleMLPLR(obj, ml_l=learner, ml_m=learner, n_folds=c["n_folds"])
    plr.fit()

    ate = plr.summary.reset_index().rename(columns={"index": "term"})
    basis = pd.concat([pd.Series(1.0, index=d.index, name="const"), d[c["blp_basis"]].astype(float)], axis=1)
    blp = plr.cate(basis=basis)
    blp_tab = blp.summary.reset_index().rename(columns={"index": "term"})

    # GATEs need mutually exclusive groups, so one dimension at a time
    gates = []
    for v in ["female", "rural", "edu_band", "emp_type"]:
        levels = sorted(d[v].dropna().unique())
        groups = pd.DataFrame({f"{v}={lv}": d[v] == lv for lv in levels})
        g = plr.gate(groups=groups).confint().reset_index().rename(columns={"index": "group"})
        g.insert(0, "dimension", v)
        g["n_group"] = groups.sum().to_numpy()
        gates.append(g)
    gate = pd.concat(gates, ignore_index=True)
    return {"dml_ate": ate.assign(n=len(d)), "dml_blp": blp_tab.assign(n=len(d)), "dml_gate": gate}


def grf_export(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """Matrix for scripts/grf_causal_forest.R (R `grf`): outcome Y, treatment W = dti_std,
    occupation cluster ids, covariates X, and the BLP basis columns (prefixed `A_`)."""
    d = df.sample(n=min(len(df), cfg["dml"]["max_obs"]), random_state=0)
    X = pd.concat([
        d[[x for x in cfg["controls"] if d[x].nunique() > 1]].astype(float),
        pd.get_dummies(d[["edu_cat", "social_group", "religion", "yq", "division"]].astype(str), drop_first=True, dtype=float),
    ], axis=1).add_prefix("X_")
    A = d[cfg["dml"]["blp_basis"]].astype(float).add_prefix("A_")
    out = pd.concat([d[[cfg["sample"]["outcome"], "dti_std", "occ_cluster_id"]], X, A], axis=1)
    return out.rename(columns={cfg["sample"]["outcome"]: "Y", "dti_std": "W", "occ_cluster_id": "cluster"})


def sample_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["round", "occ_system"])
    return pd.DataFrame({
        "n": g.size(),
        "n_occ_groups": g["occ3"].nunique(),
        "weighted_n_millions": g["weight"].sum() / 1e6,
        "share_female": g.apply(lambda x: np.average(x["female"], weights=x["weight"])),
        "share_rural": g.apply(lambda x: np.average(x["rural"], weights=x["weight"])),
        "share_casual": g.apply(lambda x: np.average(x["emp_type"] == "casual", weights=x["weight"])),
        "mean_ln_wage": g.apply(lambda x: np.average(x["ln_real_hourly_wage"], weights=x["weight"])),
    }).reset_index()
