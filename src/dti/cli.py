"""Command line entry point: `dti <command>`. Run `dti -h` for the list."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import pandas as pd

from . import config as C

CORPORA = {
    "nco": {"path": C.CORPUS_CSV, "key": "nco2015"},
    "onet": {"path": C.INTERIM / "onet_corpus.csv", "key": "onetsoc"},
}


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def _load_numeric(path: Path, text_cols: set[str]) -> pd.DataFrame:
    df = _read_csv(path)
    for c in df.columns:
        if c in text_cols:
            continue
        conv = pd.to_numeric(df[c], errors="coerce")
        if conv.notna().sum() == df[c].notna().sum():
            df[c] = conv
    return df


def _pick_model(df: pd.DataFrame, model: str | None, version: str | None) -> pd.DataFrame:
    if model:
        df = df[df["model_name"] == model]
    if version:
        df = df[df["prompt_version"] == version]
    elif df["prompt_version"].nunique() > 1:
        raise SystemExit(f"several prompt versions {sorted(df['prompt_version'].unique())}: pass one explicitly")
    if df.empty:
        raise SystemExit(f"no DTI rows for model={model} version={version}")
    return df


# --- NCO corpus ---------------------------------------------------------------------------

def cmd_corpus(args) -> None:
    from .corpus import build_corpus
    from .crosswalk import nco2004_link

    corpus = build_corpus(Path(args.xlsx))
    C.INTERIM.mkdir(parents=True, exist_ok=True)
    corpus.to_csv(C.CORPUS_CSV, index=False)
    link = nco2004_link(corpus)
    link.to_csv(C.INTERIM / "nco2015_to_nco2004.csv", index=False)
    print(f"{len(corpus)} occupations -> {C.CORPUS_CSV}")
    print(f"  {corpus['family4'].nunique()} families, {corpus['group3'].nunique()} NCO-2015 groups (PLFS from Jul 2021)")
    print(f"  NCO-2004 link: {link['link'].value_counts().to_dict()}, {link['nco2004_g3'].nunique()} NCO-2004 groups")


def _corpus(args) -> pd.DataFrame:
    from .corpus import pilot_sample

    spec = CORPORA[args.corpus]
    corpus = _read_csv(spec["path"]).fillna("")
    corpus["code"] = corpus[spec["key"]]
    if getattr(args, "sample", None):
        corpus = _read_csv(Path(args.sample))[[spec["key"]]].merge(corpus, on=spec["key"])
    if getattr(args, "codes", None):
        corpus = corpus[corpus["code"].isin(args.codes)]
    if getattr(args, "pilot", None):
        if args.corpus != "nco":
            raise SystemExit("--pilot is for the NCO corpus")
        corpus = pilot_sample(corpus, args.pilot, seed=args.seed)
    if getattr(args, "limit", None):
        corpus = corpus.head(args.limit)
    return corpus


def cmd_pilot(args) -> None:
    from .corpus import pilot_sample

    sample = pilot_sample(_read_csv(C.CORPUS_CSV), args.n, seed=args.seed)
    out = C.INTERIM / f"pilot_{args.n}_seed{args.seed}.csv"
    sample.to_csv(out, index=False)
    print(f"{len(sample)} occupations -> {out}")


def cmd_prompt(args) -> None:
    from .prompt import build_messages, prompt_version

    rubric = C.load_rubric()
    row = _corpus(args).iloc[0]
    print(f"# prompt version {prompt_version(rubric)}\n")
    for m in build_messages(rubric, row["title"], row["description"]):
        print(f"--- {m['role']} ---\n{m['content']}\n")


def cmd_score(args) -> None:
    from .scoring import score_corpus

    settings = C.model_settings(args.model)
    for key in ("runs", "temperature", "concurrency", "base_url"):
        if getattr(args, key, None) is not None:
            settings[key] = getattr(args, key)
    asyncio.run(score_corpus(_corpus(args), settings, C.load_rubric(), corpus_name=args.corpus, runs=settings["runs"]))


# --- aggregation ------------------------------------------------------------------------------

def _runs_paths(corpus: str, models: list[str] | None) -> list[Path]:
    paths = sorted(C.LLM_OUT.glob(f"*/*/{corpus}.jsonl"))
    if models:
        paths = [p for p in paths if p.parts[-3] in models]
    if not paths:
        raise SystemExit(f"no LLM output for corpus '{corpus}' under {C.LLM_OUT}")
    return paths


def cmd_aggregate(args) -> None:
    from .aggregate import aggregate_level, build_dti, consensus, load_runs

    rubric = C.load_rubric()
    key = CORPORA[args.corpus]["key"]
    runs = load_runs(_runs_paths(args.corpus, args.models), key=key, prompt_version=args.prompt_version)
    cons = consensus(runs, key=key)
    occ = pd.concat(
        [build_dti(g, rubric["aggregation"]["weights"]) for _, g in cons.groupby(["model_name", "prompt_version"])],
        ignore_index=True,
    )
    C.PROCESSED.mkdir(parents=True, exist_ok=True)

    if args.corpus == "nco":
        from .crosswalk import nco2004_link

        corpus = _read_csv(C.CORPUS_CSV)
        meta = corpus[["nco2015", "title", "family4", "group3", "division", "skill_level"]]
        occ = occ.merge(meta, on="nco2015", how="left")
        runs.to_csv(C.PROCESSED / "llm_runs_long.csv", index=False)
        occ.to_csv(C.PROCESSED / "dti_occupation_nco2015.csv", index=False)
        levels = corpus[["nco2015", "family4", "group3"]].merge(nco2004_link(corpus), on="nco2015")
        for level, name in [("family4", "dti_family4_nco2015"), ("group3", "dti_group3_nco2015"), ("nco2004_g3", "dti_group3_nco2004")]:
            agg = aggregate_level(occ, levels[["nco2015", level, "link"]], level, how=args.how)
            agg.to_csv(C.PROCESSED / f"{name}.csv", index=False)
        print(f"{runs['model_name'].nunique()} model(s), {occ['nco2015'].nunique()} occupations -> {C.PROCESSED}")
        return

    runs.to_csv(C.PROCESSED / "llm_runs_long_onet.csv", index=False)
    occ.to_csv(C.PROCESSED / "dti_llm_onet_onetsoc.csv", index=False)
    links = _onet_links()
    if links is None:
        print("O*NET-level LLM DTI written; ISCO aggregation skipped (BLS crosswalk missing, see `dti onet-build`)")
        return
    from .onet import to_isco

    cols = ["D1", "D2", "D3", "D4", "D5", "dti_mean_score", "q9_overall"]
    out = []
    for (model, version), g in occ.groupby(["model_name", "prompt_version"]):
        agg = to_isco(g, links, cols)
        out.append(agg.assign(model_name=model, prompt_version=version))
    pd.concat(out).to_csv(C.PROCESSED / "dti_llm_onet_isco4.csv", index=False)
    print(f"O*NET LLM DTI: {occ['onetsoc'].nunique()} O*NET occupations -> ISCO-08 4-digit")


def cmd_baseline(args) -> None:
    from .baseline import keyword_baseline

    out = keyword_baseline(_read_csv(C.CORPUS_CSV))
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    out.to_csv(C.PROCESSED / "keyword_baseline_nco2015.csv", index=False)
    print(f"keyword baseline: {out['kw_any'].mean():.1%} of occupations mention a digital keyword")


def cmd_reliability(args) -> None:
    from . import reliability as R

    C.REPORTS.mkdir(parents=True, exist_ok=True)
    runs = _load_numeric(C.PROCESSED / "llm_runs_long.csv", {"nco2015", "model_name", "prompt_version"})
    cons = _load_numeric(C.PROCESSED / "dti_occupation_nco2015.csv", {"nco2015", "model_name", "prompt_version", "family4", "group3", "division"})

    R.run_stability(runs).to_csv(C.REPORTS / "stability_runs.csv", index=False)
    R.unstable_occupations(cons, args.sd_threshold).to_csv(C.REPORTS / "unstable_occupations.csv", index=False)
    R.summary_q9_vs_dimensions(cons).to_csv(C.REPORTS / "q9_vs_equal_weight.csv", index=False)
    if cons["model_name"].nunique() > 1:
        R.cross_model(cons).to_csv(C.REPORTS / "cross_model.csv", index=False)

    if list(C.HUMAN.glob("*.xlsx")):
        from .human import read_all

        human = read_all(C.HUMAN)
        human.to_csv(C.PROCESSED / "human_codings_long.csv", index=False)
        R.human_vs_llm(human, cons).to_csv(C.REPORTS / "human_vs_llm.csv", index=False)
        R.multi_rater_alpha(human, cons).to_csv(C.REPORTS / "alpha_multi_rater.csv", index=False)
        print(f"human forms: {human['coder_id'].nunique()} coder(s), {len(human)} codings")
    print(f"reports -> {C.REPORTS}")


# --- O*NET ------------------------------------------------------------------------------------

def _onet_cfg() -> dict:
    return C.load_yaml(C.CONFIGS / "onet.yaml")


def _onet_links():
    from .onet import onet_isco_links, read_isco_soc, read_oews

    cfg = _onet_cfg()
    xw = C.ROOT / cfg["bls"]["isco_soc_crosswalk"]["path"]
    if not xw.exists():
        return None
    oews_path = C.ROOT / cfg["bls"]["oews_national"]["path"]
    oews = read_oews(oews_path) if oews_path.exists() else None
    return onet_isco_links(C.ROOT / cfg["raw_dir"], read_isco_soc(xw), oews)


def cmd_onet_download(args) -> None:
    from .onet import download

    cfg = _onet_cfg()
    for p in download(cfg, C.ROOT):
        print(f"  {p}")
    print("\nManual step (bls.gov blocks scripts) — download in a browser and save as:")
    for item in cfg["bls"].values():
        print(f"  {item['path']}  <-  {item['url']}")


def cmd_onet_build(args) -> None:
    from .onet import build_corpus, measures, to_isco

    cfg = _onet_cfg()
    raw = C.ROOT / cfg["raw_dir"]
    corpus = build_corpus(raw)
    corpus.to_csv(C.INTERIM / "onet_corpus.csv", index=False)
    m = measures(raw, cfg["items"])
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    m.to_csv(C.PROCESSED / "onet_measures_onetsoc.csv", index=False)
    print(f"O*NET corpus: {len(corpus)} occupations -> {C.INTERIM / 'onet_corpus.csv'}")
    print(f"O*NET measures: {len(m)} occupations")

    links = _onet_links()
    if links is None:
        print(f"BLS ISCO-SOC crosswalk not found at {cfg['bls']['isco_soc_crosswalk']['path']}: ISCO aggregation skipped")
        return
    links.to_csv(C.INTERIM / "onet_to_isco08.csv", index=False)
    cols = [c for c in m.columns if c != "onetsoc"]
    isco = to_isco(m, links, cols)
    isco.to_csv(C.PROCESSED / "onet_measures_isco4.csv", index=False)
    oews_found = (C.ROOT / cfg["bls"]["oews_national"]["path"]).exists()
    weighted = "US employment (OEWS)" if oews_found else "equal weights (OEWS file missing)"
    print(f"  -> {len(isco)} ISCO-08 unit groups, weights: {weighted}")


def cmd_gap(args) -> None:
    from . import gap as G

    out_dir = C.REPORTS / "gap"
    out_dir.mkdir(parents=True, exist_ok=True)
    text = {"family4", "model_name", "prompt_version", "isco08", "group3"}
    nco = _pick_model(_load_numeric(C.PROCESSED / "dti_family4_nco2015.csv", text), args.model, args.prompt_version)
    corpus = _read_csv(C.CORPUS_CSV)
    meta = corpus.groupby("family4")[["division", "skill_level", "family_title"]].first().reset_index()

    tables, corrs = [], []
    conv_path = C.PROCESSED / "onet_measures_isco4.csv"
    if conv_path.exists():
        conv = _load_numeric(conv_path, text)
        cols = ["kw_share_core", "wa_computers_im", "kn_computers_im", "cx_email", "muro_0_100"]
        corrs.append(G.correlations(nco.merge(conv.rename(columns={"isco08": "family4"}), on="family4"), "dti_z", cols))
        tables.append(G.gap_table(nco, conv, "dti_z", "muro_0_100"))
        tables.append(G.gap_table(nco, conv, "dti_z", "wa_computers_im"))
        json.dump(G.unmatched(nco, conv), open(out_dir / "unmatched_codes.json", "w"), indent=1)

    llm_path = C.PROCESSED / "dti_llm_onet_isco4.csv"
    if llm_path.exists():
        llm = _pick_model(_load_numeric(llm_path, text), args.model, args.prompt_version)
        both = nco.merge(llm.rename(columns={"isco08": "family4"}), on="family4", suffixes=("", "_onet"))
        corrs.append(G.correlations(both, "dti_mean_score", ["dti_mean_score_onet", *[f"D{i}_onet" for i in range(1, 6)]]))
        tables.append(G.gap_table(nco, llm, "dti_mean_score", "dti_mean_score", raw_comparable=True))

    if not tables:
        raise SystemExit("no O*NET aggregates found: run `dti onet-build` (and `dti aggregate --corpus onet`) first")
    pd.concat(corrs).to_csv(out_dir / "correlations.csv", index=False)
    for t in tables:
        name = f"gap_{t['onet_measure'].iloc[0]}" + ("_llm" if "gap_raw" in t else "")
        t.merge(meta, on="family4", how="left").to_csv(out_dir / f"{name}.csv", index=False)
        for by in ["division", "skill_level"]:
            G.gap_by(t, meta, by).to_csv(out_dir / f"{name}_by_{by}.csv", index=False)
    print(f"gap reports -> {out_dir}")


# --- PLFS and analysis --------------------------------------------------------------------------

def _dti_tables(model: str | None, version: str | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    text = {"group3", "nco2004_g3", "model_name", "prompt_version"}
    a = _pick_model(_load_numeric(C.PROCESSED / "dti_group3_nco2015.csv", text), model, version)
    b = _pick_model(_load_numeric(C.PROCESSED / "dti_group3_nco2004.csv", text), model, version)
    return a, b


def cmd_plfs_build(args) -> None:
    from .plfs import attach_dti, coverage, harmonise, read_round

    cfg = C.load_yaml(Path(args.config))
    acfg = C.load_yaml(C.CONFIGS / "analysis.yaml")["dti"]
    cpi_path = C.ROOT / cfg["deflator"]["path"]
    cpi = pd.read_csv(cpi_path) if cpi_path.exists() else None
    if cpi is None:
        print(f"no CPI file at {cpi_path}: wages stay nominal (year-quarter FE absorb the national price level)")

    rounds = args.rounds or list(cfg["rounds"])
    frames = []
    for name in rounds:
        raw = read_round(name, cfg["rounds"][name], C.ROOT)
        frames.append(harmonise(raw, cfg, cpi))
        print(f"  {name}: {len(raw):,} persons")
    h = pd.concat(frames, ignore_index=True)
    d15, d04 = _dti_tables(args.model or acfg["model_name"], args.prompt_version or acfg["prompt_version"])
    h = attach_dti(h, d15, d04)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    h.to_parquet(out, index=False)
    cov = coverage(h)
    cov.to_csv(out.with_name(out.stem + "_dti_coverage.csv"), index=False)
    print(f"{len(h):,} persons -> {out}\n{cov.to_string(index=False)}")


def cmd_synth_plfs(args) -> None:
    import yaml

    from .synth import write_synthetic

    acfg = C.load_yaml(C.CONFIGS / "analysis.yaml")["dti"]
    d15, d04 = _dti_tables(args.model or acfg["model_name"], args.prompt_version)
    out_dir = C.DATA / "synthetic"
    rounds = write_synthetic(d15, d04, out_dir, n_households=args.households)
    cfg = C.load_yaml(C.CONFIGS / "plfs.yaml")
    cfg["rounds"] = rounds
    cfg["deflator"]["path"] = "data/synthetic/no_cpi.csv"
    path = out_dir / "plfs_synthetic.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    print(f"SYNTHETIC rounds {list(rounds)} -> {out_dir}\nconfig -> {path}")


def cmd_analysis(args) -> None:
    from . import econ as E

    cfg = C.load_yaml(Path(args.config))
    df = pd.read_parquet(args.input)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    skip = set(args.skip or [])

    sample = E.analysis_sample(df, cfg)
    print(f"analysis sample: {len(sample):,} workers, {sample['occ_cluster'].nunique()} occupation clusters")
    E.sample_summary(sample).to_csv(out / "sample_summary.csv", index=False)

    steps = {
        "baseline": lambda: E.baseline(sample, cfg),
        "robustness": lambda: E.robustness(df, sample, cfg),
        "heckman": lambda: E.heckman(df, cfg),
        "rif": lambda: E.rif_regressions(sample, cfg),
        "cqr": lambda: E.conditional_quantiles(sample, cfg),
        "oaxaca": lambda: E.oaxaca(sample, cfg),
        "interactions": lambda: E.interactions(sample, cfg),
        "subgroups": lambda: E.subgroups(sample, cfg),
        "dml": lambda: E.double_ml(sample, cfg),
        "grf_input": lambda: E.grf_export(sample, cfg),
    }
    models = {}
    for name, step in steps.items():
        if name in skip:
            continue
        print(f"  {name} ...", flush=True)
        res = step()
        if name == "baseline":
            res, models = res
            E.oster_table(models, cfg).to_csv(out / "oster.csv", index=False)
        if isinstance(res, dict):
            for k, v in res.items():
                v.to_csv(out / f"{k}.csv", index=False)
        else:
            res.to_csv(out / f"{name}.csv", index=False)
    print(f"results -> {out}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="dti", description="Digital Task Intensity pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("corpus", help="build NCO-2015 corpus + NCO-2004 link from the coder form")
    s.add_argument("--xlsx", default=str(C.FORM_XLSX))
    s.set_defaults(func=cmd_corpus)

    s = sub.add_parser("pilot", help="draw a division-stratified prompt-development sample")
    s.add_argument("--n", type=int, default=50)
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(func=cmd_pilot)

    def selection(sp):
        sp.add_argument("--corpus", choices=list(CORPORA), default="nco")
        sp.add_argument("--codes", nargs="+", help="only these occupation codes")
        sp.add_argument("--sample", help="CSV with the corpus key column (e.g. a pilot sample)")
        sp.add_argument("--pilot", type=int, help="draw a stratified NCO sample of this size on the fly")
        sp.add_argument("--seed", type=int, default=0)
        sp.add_argument("--limit", type=int, help="first N occupations only (smoke test)")

    s = sub.add_parser("prompt", help="print the exact messages sent for one occupation")
    selection(s)
    s.set_defaults(func=cmd_prompt)

    s = sub.add_parser("score", help="score a corpus with one model (resumable)")
    s.add_argument("--model", required=True, help="model key in configs/models.yaml")
    s.add_argument("--runs", type=int)
    s.add_argument("--temperature", type=float)
    s.add_argument("--concurrency", type=int)
    s.add_argument("--base-url", dest="base_url")
    selection(s)
    s.set_defaults(func=cmd_score)

    s = sub.add_parser("aggregate", help="consensus across runs -> DTI (NCO: occupation/family/group/NCO-2004; O*NET: ISCO-08)")
    s.add_argument("--corpus", choices=list(CORPORA), default="nco")
    s.add_argument("--models", nargs="+")
    s.add_argument("--prompt-version", dest="prompt_version")
    s.add_argument("--how", choices=["mean", "median"], default="mean")
    s.set_defaults(func=cmd_aggregate)

    s = sub.add_parser("baseline", help="keyword DTI on NCO text (benchmark)")
    s.set_defaults(func=cmd_baseline)

    s = sub.add_parser("reliability", help="stability, cross-model and human-LLM agreement reports")
    s.add_argument("--sd-threshold", type=float, default=0.5)
    s.set_defaults(func=cmd_reliability)

    s = sub.add_parser("onet-download", help="download O*NET files + taxonomy crosswalk")
    s.set_defaults(func=cmd_onet_download)

    s = sub.add_parser("onet-build", help="O*NET corpus for the LLM, conventional measures, ISCO-08 aggregation")
    s.set_defaults(func=cmd_onet_build)

    s = sub.add_parser("gap", help="India (NCO-LLM) vs O*NET correlations and DigitalGap (RQ2)")
    s.add_argument("--model")
    s.add_argument("--prompt-version", dest="prompt_version")
    s.set_defaults(func=cmd_gap)

    s = sub.add_parser("plfs-build", help="harmonise PLFS rounds and attach the DTI")
    s.add_argument("--config", default=str(C.CONFIGS / "plfs.yaml"))
    s.add_argument("--rounds", nargs="+")
    s.add_argument("--model")
    s.add_argument("--prompt-version", dest="prompt_version")
    s.add_argument("--out", default=str(C.PROCESSED / "plfs_harmonised.parquet"))
    s.set_defaults(func=cmd_plfs_build)

    s = sub.add_parser("synth-plfs", help="write SYNTHETIC PLFS-like rounds for a dry run (not research data)")
    s.add_argument("--households", type=int, default=3000)
    s.add_argument("--model")
    s.add_argument("--prompt-version", dest="prompt_version")
    s.set_defaults(func=cmd_synth_plfs)

    s = sub.add_parser("analysis", help="wage models: baseline, robustness, selection, distribution, heterogeneity")
    s.add_argument("--config", default=str(C.CONFIGS / "analysis.yaml"))
    s.add_argument("--input", default=str(C.PROCESSED / "plfs_harmonised.parquet"))
    s.add_argument("--out", default=str(C.REPORTS / "econ"))
    s.add_argument("--skip", nargs="+", help="steps to skip, e.g. dml cqr")
    s.set_defaults(func=cmd_analysis)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
