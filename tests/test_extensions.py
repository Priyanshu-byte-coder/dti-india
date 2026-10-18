import asyncio
import json
import warnings

import numpy as np
import pandas as pd
import pytest

from dti import econ as E
from dti import gap as G
from dti import onet as O
from dti import scoring
from dti.config import CONFIGS, load_rubric, load_yaml, model_settings
from dti.plfs import DTI_COLS, attach_dti, harmonise, read_round
from dti.synth import write_synthetic


# --- scoring: resumable, generic corpus -----------------------------------------------------

def test_score_corpus_resumes(tmp_path, monkeypatch):
    monkeypatch.setattr(scoring, "LLM_OUT", tmp_path)
    corpus = pd.DataFrame({
        "code": ["A", "B"],
        "title": ["Data Entry Operator", "Mason"],
        "description": ["Enters data into computer and maintains database.", "Lays bricks and stones."],
    })
    settings = model_settings("mock")
    rubric = load_rubric()
    path = asyncio.run(scoring.score_corpus(corpus, settings, rubric, corpus_name="test", runs=2))
    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 4 and all(r["ok"] and r["corpus"] == "test" for r in lines)
    asyncio.run(scoring.score_corpus(corpus, settings, rubric, corpus_name="test", runs=3))
    assert len(path.read_text(encoding="utf-8").splitlines()) == 6  # only run 2 added


# --- O*NET crosswalk -----------------------------------------------------------------------------

def _fake_raw(tmp_path):
    raw = tmp_path / "onet"
    raw.mkdir()
    pd.DataFrame({
        "O*NET-SOC 2010 Code": ["15-1132.00", "43-9021.00", "43-9021.00"],
        "O*NET-SOC 2010 Title": ["x", "y", "y"],
        "O*NET-SOC 2019 Code": ["15-1252.00", "43-9021.00", "43-9022.00"],
        "O*NET-SOC 2019 Title": ["x", "y", "z"],
    }).to_csv(raw / "2010_to_2019_Crosswalk.csv", index=False)
    return raw


def test_read_isco_soc_finds_header(tmp_path):
    path = tmp_path / "xwalk.xlsx"
    rows = [["Crosswalk ISCO-08 to 2010 SOC", None, None, None],
            ["notes", None, None, None],
            ["ISCO-08 Code", "ISCO-08 Title EN", "2010 SOC Code", "2010 SOC Title"],
            ["2512", "Software developers", "15-1132", "Software Developers, Applications"],
            ["4132", "Data entry clerks", "43-9021", "Data Entry Keyers"],
            ["4132", "Data entry clerks", "43-9022", "Word Processors"]]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)
    pairs = O.read_isco_soc(path)
    assert pairs.to_dict("records")[0] == {"isco08": "2512", "soc2010": "15-1132"}
    assert len(pairs) == 3


def test_read_isco_soc_rejects_blocked_page(tmp_path):
    path = tmp_path / "x.xls"
    path.write_text("<!DOCTYPE HTML><title>Access Denied</title>")
    with pytest.raises(ValueError, match="web page"):
        O.read_isco_soc(path)


def test_links_and_isco_aggregation(tmp_path):
    raw = _fake_raw(tmp_path)
    isco_soc = pd.DataFrame({"isco08": ["2512", "4132", "4132"], "soc2010": ["15-1132", "43-9021", "43-9022"]})
    oews = pd.Series({"15-1252": 1000.0, "43-9021": 300.0, "43-9022": 100.0})
    links = O.onet_isco_links(raw, isco_soc, oews)
    assert set(links["isco08"]) == {"2512", "4132"}
    values = pd.DataFrame({"onetsoc": ["15-1252.00", "43-9021.00", "43-9022.00"], "m": [10.0, 4.0, 0.0]})
    isco = O.to_isco(values, links, ["m"]).set_index("isco08")
    assert isco.loc["2512", "m"] == 10.0
    assert isco.loc["4132", "m"] == pytest.approx((4 * 300 + 0 * 100) / 400)  # employment-weighted


def test_onet_corpus_and_measures_on_real_files():
    raw = CONFIGS.parent / "data" / "raw" / "onet"
    if not (raw / "task_statements.csv").exists():
        pytest.skip("O*NET files not downloaded (run `dti onet-download`)")
    corpus = O.build_corpus(raw)
    assert corpus["onetsoc"].is_unique and (corpus["n_tasks"] > 0).all()
    m = O.measures(raw, load_yaml(CONFIGS / "onet.yaml")["items"]).set_index("onetsoc")
    assert m.loc["15-1252.00", "muro_0_100"] > m["muro_0_100"].median()  # software developers


# --- gap --------------------------------------------------------------------------------------------

def test_gap_table_and_correlations():
    nco = pd.DataFrame({"family4": ["1111", "2512", "4132", "9211"], "s": [0.2, 3.5, 2.0, 0.0]})
    onet = pd.DataFrame({"isco08": ["1111", "2512", "4132", "9211"], "s": [1.0, 3.8, 3.0, 0.2]})
    t = G.gap_table(nco, onet, "s", "s", raw_comparable=True).set_index("family4")
    assert t.loc["4132", "gap_raw"] == pytest.approx(1.0)
    assert t["gap_pct"].abs().max() == 0  # same ranking
    c = G.correlations(nco.merge(onet.rename(columns={"isco08": "family4", "s": "o"}), on="family4"), "s", ["o"])
    assert c.loc[0, "spearman"] == pytest.approx(1.0)


# --- PLFS + econometrics on synthetic data -------------------------------------------------------------

def _fake_dti(codes, key, seed):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({key: codes})
    for c in DTI_COLS:
        df[c] = rng.normal(size=len(codes))
    df["dti_z"] = (df["dti_z"] - df["dti_z"].mean()) / df["dti_z"].std(ddof=0)
    return df


@pytest.fixture(scope="module")
def synthetic_panel(tmp_path_factory):
    out = tmp_path_factory.mktemp("synth")
    codes = [f"{d}{i}{j}" for d in range(1, 10) for i in range(1, 4) for j in range(1, 3)]
    d15 = _fake_dti(codes, "group3", 1)
    d04 = _fake_dti(codes, "nco2004_g3", 2).assign(share_direct_link=1.0)
    cfg = load_yaml(CONFIGS / "plfs.yaml")
    cfg["rounds"] = write_synthetic(d15, d04, out, n_households=1500)
    frames = [harmonise(read_round(n, r, out), cfg, None) for n, r in cfg["rounds"].items()]
    return attach_dti(pd.concat(frames, ignore_index=True), d15, d04)


def test_harmonise_and_merge(synthetic_panel):
    h = synthetic_panel
    assert set(h["occ_system"]) == {"nco2004", "nco2015"}
    emp = h[h["emp_type"].isin(["regular", "casual"])]
    assert emp["dti_matched"].mean() == 1.0
    assert emp["ln_real_hourly_wage"].notna().mean() > 0.95
    assert h["weight"].gt(0).all()
    assert h.loc[h["emp_type"] != "regular", "formal_ss"].isna().all()
    assert {"hh_size", "hh_children_u6", "hh_head"} <= set(h.columns)


def test_econometrics_recover_synthetic_premium(synthetic_panel):
    cfg = load_yaml(CONFIGS / "analysis.yaml")
    sample = E.analysis_sample(synthetic_panel, cfg)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        base, models = E.baseline(sample, cfg)
        inter = E.interactions(sample, cfg)
    m4 = base[(base["model"] == "M4") & (base["term"] == "dti_std")].iloc[0]
    assert m4["coef"] > 0 and m4["p"] < 0.01
    fem = inter[(inter["model"] == "occupation FE + interactions") & (inter["term"] == "dti_x_female")].iloc[0]
    assert fem["coef"] < 0  # built-in smaller premium for women, identified within occupations
    assert not E.oster_table(models, cfg).empty


def test_oster_formula():
    r = E.oster(beta_short=0.2, r_short=0.1, beta_long=0.1, r_long=0.3, rmax=0.39)
    # beta* = 0.1 - 0.1 * (0.09 / 0.2) = 0.055 ; delta = 0.1 * 0.2 / (0.1 * 0.09)
    assert r["beta_at_delta_1"] == pytest.approx(0.055)
    assert r["delta_for_beta_0"] == pytest.approx(0.02 / 0.009)


def test_rif_and_oaxaca_run(synthetic_panel):
    cfg = load_yaml(CONFIGS / "analysis.yaml")
    cfg["quantiles"] = [0.25, 0.75]
    sample = E.analysis_sample(synthetic_panel, cfg)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rif = E.rif_regressions(sample, cfg)
        oax = E.oaxaca(sample, cfg).set_index("component")
    assert len(rif) == 2
    parts = oax.loc["explained", "value"] + oax.loc["unexplained", "value"]
    assert parts == pytest.approx(oax.loc["total gap", "value"], abs=1e-6)
