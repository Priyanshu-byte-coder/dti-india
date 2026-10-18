"""Build the scoring prompt from the rubric. The prompt hash versions every LLM output."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .schema import json_schema


def system_prompt(rubric: dict[str, Any]) -> str:
    lines = [
        "You are a trained coder in a research study measuring the digital task intensity of "
        "Indian occupations. You apply a fixed coding rubric to official occupation descriptions "
        "from India's National Classification of Occupations 2015 (NCO-2015). You are a measurement "
        "instrument: apply the rubric literally and consistently, exactly as a human coder would.",
        "",
        "RULES",
    ]
    lines += [f"{i}. {rule}" for i, rule in enumerate(rubric["rules"], 1)]

    lines += ["", "SCORE SCALE (used for every dimension)"]
    lines += [f"{k} = {v}" for k, v in rubric["scale"].items()]

    lines += ["", "DIMENSIONS"]
    for d in rubric["dimensions"]:
        lines.append(f"{d['id']} ({d['question']}). {d['name']}: {d['definition']}")
        lines += [f"  {k}: {v}" for k, v in d["anchors"].items()]

    oq = rubric["other_questions"]
    lines += [
        "",
        "OTHER QUESTIONS",
        oq["q1_detail"],
        oq["evidence"],
        oq["confidence"],
        oq["q9_overall"],
        oq["q10_core"],
        oq["q11_india_today"],
        oq["q12_comment"],
        "",
        "OUTPUT",
        "Return one JSON object and nothing else. For each dimension D1-D5 give: 'rationale' "
        "(one sentence), 'evidence' (words copied verbatim from the description, several short "
        "quotes may be separated by '; ', empty string if the score is 0), 'score' (0-4) and "
        "'confidence' (1-3). Also give q1_detail, q9_overall, q10_core, q11_india_today and "
        "q12_comment. Never quote words that are not in the description.",
    ]
    return "\n".join(lines)


def user_prompt(title: str, description: str) -> str:
    return (
        "Code this occupation.\n\n"
        f"Occupation title: {title}\n"
        f"Occupation description: {description}"
    )


def build_messages(rubric: dict[str, Any], title: str, description: str) -> list[dict[str, str]]:
    ex = rubric["worked_example"]
    return [
        {"role": "system", "content": system_prompt(rubric)},
        {"role": "user", "content": user_prompt(ex["title"], ex["description"])},
        {"role": "assistant", "content": json.dumps(ex["coding"], ensure_ascii=False)},
        {"role": "user", "content": user_prompt(title, description)},
    ]


def prompt_version(rubric: dict[str, Any]) -> str:
    """Short hash of everything that defines the instrument (prompt text, example, schema)."""
    payload = json.dumps(
        {
            "system": system_prompt(rubric),
            "example": rubric["worked_example"],
            "schema": json_schema(),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]
