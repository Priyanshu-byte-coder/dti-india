"""Command line entry point: `dti <command>`. Run `dti -h` for the list."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import pandas as pd

from . import config as C


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
    from .corpus import load_corpus, pilot_sample

    corpus = load_corpus(C.CORPUS_CSV)
    if getattr(args, "sample", None):
        corpus = pd.read_csv(args.sample, dtype=str)[["nco2015"]].merge(corpus, on="nco2015")
    if getattr(args, "codes", None):
        corpus = corpus[corpus["nco2015"].isin(args.codes)]
    if getattr(args, "pilot", None):
        corpus = pilot_sample(corpus, args.pilot, seed=args.seed)
    if getattr(args, "limit", None):
        corpus = corpus.head(args.limit)
    return corpus


def cmd_pilot(args) -> None:
    from .corpus import load_corpus, pilot_sample

    sample = pilot_sample(load_corpus(C.CORPUS_CSV), args.n, seed=args.seed)
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
    asyncio.run(score_corpus(_corpus(args), settings, C.load_rubric(), runs=settings["runs"]))


def cmd_aggregate(args) -> None:
    from .aggregate import aggregate_level, build_dti, consensus, load_runs
    from .crosswalk import nco2004_link
    from .corpus import load_corpus

    rubric = C.load_rubric()
    paths = sorted(C.LLM_OUT.glob("*/*/scores.jsonl"))
    if args.models:
        paths = [p for p in paths if p.parts[-3] in args.models]
    runs = load_runs(paths, prompt_version=args.prompt_version)
    cons = consensus(runs)

    corpus = load_corpus(C.CORPUS_CSV)
    occ = pd.concat(
        [build_dti(g, rubric["aggregation"]["weights"]) for _, g in cons.groupby(["model_name", "prompt_version"])],
        ignore_index=True,
    )
    meta = corpus[["nco2015", "title", "family4", "group3", "division", "skill_level"]]
    occ = occ.merge(meta, on="nco2015", how="left")

    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    runs.to_csv(C.PROCESSED / "llm_runs_long.csv", index=False)
    occ.to_csv(C.PROCESSED / "dti_occupation_nco2015.csv", index=False)

    levels = corpus[["nco2015", "family4", "group3"]].merge(nco2004_link(corpus), on="nco2015")
    for level, name in [("family4", "dti_family4_nco2015"), ("group3", "dti_group3_nco2015"), ("nco2004_g3", "dti_group3_nco2004")]:
        agg = aggregate_level(occ, levels[["nco2015", level, "link"]], level, how=args.how)
        agg.to_csv(C.PROCESSED / f"{name}.csv", index=False)
    print(f"{runs['model_name'].nunique()} model(s), {occ['nco2015'].nunique()} occupations -> {C.PROCESSED}")


def cmd_baseline(args) -> None:
    from .baseline import keyword_baseline
    from .corpus import load_corpus

    out = keyword_baseline(load_corpus(C.CORPUS_CSV))
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    out.to_csv(C.PROCESSED / "keyword_baseline_nco2015.csv", index=False)
    print(f"keyword baseline: {out['kw_any'].mean():.1%} of occupations mention a digital keyword")


def cmd_reliability(args) -> None:
    from . import reliability as R

    C.REPORTS.mkdir(parents=True, exist_ok=True)
    runs = pd.read_csv(C.PROCESSED / "llm_runs_long.csv", dtype={"nco2015": str})
    cons = pd.read_csv(C.PROCESSED / "dti_occupation_nco2015.csv", dtype={"nco2015": str})

    R.run_stability(runs).to_csv(C.REPORTS / "stability_runs.csv", index=False)
    R.unstable_occupations(cons, args.sd_threshold).to_csv(C.REPORTS / "unstable_occupations.csv", index=False)
    R.summary_q9_vs_dimensions(cons).to_csv(C.REPORTS / "q9_vs_equal_weight.csv", index=False)
    if cons["model_name"].nunique() > 1:
        R.cross_model(cons).to_csv(C.REPORTS / "cross_model.csv", index=False)

    forms = list(C.HUMAN.glob("*.xlsx"))
    if forms:
        from .human import read_all

        human = read_all(C.HUMAN)
        human.to_csv(C.PROCESSED / "human_codings_long.csv", index=False)
        R.human_vs_llm(human, cons).to_csv(C.REPORTS / "human_vs_llm.csv", index=False)
        R.multi_rater_alpha(human, cons).to_csv(C.REPORTS / "alpha_multi_rater.csv", index=False)
        print(f"human forms: {human['coder_id'].nunique()} coder(s), {len(human)} codings")
    print(f"reports -> {C.REPORTS}")


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
        sp.add_argument("--codes", nargs="+", help="score only these NCO-2015 codes")
        sp.add_argument("--sample", help="CSV with an nco2015 column (e.g. a pilot sample)")
        sp.add_argument("--pilot", type=int, help="draw a stratified sample of this size on the fly")
        sp.add_argument("--seed", type=int, default=0)
        sp.add_argument("--limit", type=int, help="first N occupations only (smoke test)")

    s = sub.add_parser("prompt", help="print the exact messages sent for one occupation")
    selection(s)
    s.set_defaults(func=cmd_prompt)

    s = sub.add_parser("score", help="score occupations with one model (resumable)")
    s.add_argument("--model", required=True, help="model key in configs/models.yaml")
    s.add_argument("--runs", type=int)
    s.add_argument("--temperature", type=float)
    s.add_argument("--concurrency", type=int)
    s.add_argument("--base-url", dest="base_url")
    selection(s)
    s.set_defaults(func=cmd_score)

    s = sub.add_parser("aggregate", help="consensus across runs -> DTI at occupation, family, group and NCO-2004 level")
    s.add_argument("--models", nargs="+")
    s.add_argument("--prompt-version", dest="prompt_version")
    s.add_argument("--how", choices=["mean", "median"], default="mean")
    s.set_defaults(func=cmd_aggregate)

    s = sub.add_parser("baseline", help="keyword DTI on NCO text (benchmark)")
    s.set_defaults(func=cmd_baseline)

    s = sub.add_parser("reliability", help="stability, cross-model and human-LLM agreement reports")
    s.add_argument("--sd-threshold", type=float, default=0.5)
    s.set_defaults(func=cmd_reliability)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
