"""Score the corpus: occupations x runs, resumable, one JSONL line per (occupation, run)."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .config import DIMENSIONS, LLM_OUT
from .evidence import check_evidence
from .llm import make_scorer
from .prompt import prompt_version


def output_path(model_name: str, version: str) -> Path:
    return LLM_OUT / model_name / version / "scores.jsonl"


def completed_keys(path: Path) -> set[tuple[str, int]]:
    """(nco2015, run) pairs already scored successfully; failed ones are retried."""
    done: set[tuple[str, int]] = set()
    if not path.exists():
        return done
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("ok"):
                done.add((rec["nco2015"], rec["run"]))
    return done


async def score_corpus(
    corpus: pd.DataFrame,
    settings: dict[str, Any],
    rubric: dict[str, Any],
    runs: int | None = None,
) -> Path:
    runs = runs or settings["runs"]
    version = prompt_version(rubric)
    path = output_path(settings["name"], version)
    path.parent.mkdir(parents=True, exist_ok=True)

    done = completed_keys(path)
    todo = [
        (row, run)
        for row in corpus.itertuples(index=False)
        for run in range(runs)
        if (row.nco2015, run) not in done
    ]
    total = len(corpus) * runs
    print(f"[{settings['name']}] prompt {version}: {total - len(todo)}/{total} done, {len(todo)} to score -> {path}")
    if not todo:
        return path

    scorer = make_scorer(settings, rubric)
    sem = asyncio.Semaphore(settings.get("concurrency", 8))
    lock = asyncio.Lock()
    counter = {"n": 0, "failed": 0}
    t0 = time.perf_counter()

    with open(path, "a", encoding="utf-8") as out:

        async def one(row, run: int) -> None:
            async with sem:
                res = await scorer.score(row.title, row.description, seed=run)
            rec = {
                "nco2015": row.nco2015,
                "run": run,
                "seed": run,
                "model_name": settings["name"],
                "model": settings["model"],
                "temperature": settings.get("temperature"),
                "prompt_version": version,
                "rubric_version": rubric["version"],
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                **res,
            }
            if res["ok"]:
                rec["evidence_check"] = {
                    d: check_evidence(res["coding"]["dimensions"][d]["evidence"], row.description)
                    for d in DIMENSIONS
                }
            async with lock:
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                counter["n"] += 1
                counter["failed"] += not res["ok"]
                if counter["n"] % 100 == 0 or counter["n"] == len(todo):
                    rate = counter["n"] / (time.perf_counter() - t0)
                    print(f"  {counter['n']}/{len(todo)} scored, {counter['failed']} failed, {rate:.1f}/s")

        await asyncio.gather(*(one(row, run) for row, run in todo))
    return path
