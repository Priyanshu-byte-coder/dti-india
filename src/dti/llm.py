"""LLM backends. Every real model is reached through an OpenAI-compatible chat endpoint
(vLLM on the GPU server, or a hosted API), so one client covers all of them."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from .baseline import keyword_hits
from .prompt import build_messages
from .schema import Coding, ParseError, json_schema, parse_coding


class OpenAICompatScorer:
    def __init__(self, settings: dict[str, Any], rubric: dict[str, Any]):
        from openai import AsyncOpenAI

        self.settings = settings
        self.rubric = rubric
        self.client = AsyncOpenAI(
            base_url=settings["base_url"],
            api_key=os.environ.get(settings.get("api_key_env", ""), "EMPTY"),
            timeout=settings.get("timeout", 300),
        )

    def _response_format(self) -> dict[str, Any] | None:
        mode = self.settings.get("structured_output", "json_schema")
        if mode == "json_schema":
            return {"type": "json_schema", "json_schema": {"name": "coding", "schema": json_schema()}}
        if mode == "json_object":
            return {"type": "json_object"}
        return None

    async def score(self, title: str, description: str, seed: int) -> dict[str, Any]:
        s = self.settings
        kwargs: dict[str, Any] = dict(
            model=s["model"],
            messages=build_messages(self.rubric, title, description),
            temperature=s["temperature"],
            top_p=s["top_p"],
            max_tokens=s["max_tokens"],
            seed=seed,
        )
        if (fmt := self._response_format()) is not None:
            kwargs["response_format"] = fmt
        if s.get("extra_body"):
            kwargs["extra_body"] = s["extra_body"]

        errors: list[str] = []
        for attempt in range(1, s.get("max_attempts", 3) + 1):
            t0 = time.perf_counter()
            raw = ""
            try:
                resp = await self.client.chat.completions.create(**kwargs)
                raw = resp.choices[0].message.content or ""
                coding = parse_coding(raw)
                usage = resp.usage.model_dump() if resp.usage else None
                return _result(coding, raw, attempt, time.perf_counter() - t0, usage, errors)
            except ParseError as e:
                errors.append(f"attempt {attempt}: {e}")
            except Exception as e:  # network / server errors
                errors.append(f"attempt {attempt}: {type(e).__name__}: {e}")
                await asyncio.sleep(min(2**attempt, 30))
        return _result(None, raw, attempt, None, None, errors)


class MockScorer:
    """Keyword-driven stand-in that exercises the pipeline end to end. Not research data."""

    def __init__(self, settings: dict[str, Any], rubric: dict[str, Any]):
        self.settings = settings

    async def score(self, title: str, description: str, seed: int) -> dict[str, Any]:
        hits = keyword_hits(description)
        dims = {}
        for dim, words in hits.items():
            score = min(4, len(words) + (1 if words and seed % 2 else 0))
            dims[dim] = {
                "rationale": "keyword mock",
                "evidence": "; ".join(dict.fromkeys(words)) if score else "",
                "score": score,
                "confidence": 2,
            }
        total = sum(d["score"] for d in dims.values())
        coding = Coding.model_validate(
            {
                "q1_detail": "Yes" if len(description.split()) > 40 else "Partly",
                "dimensions": dims,
                "q9_overall": min(10, round(total / 2)),
                "q10_core": "Core" if total >= 12 else ("Supporting" if total else "Not relevant"),
                "q11_india_today": "Same",
                "q12_comment": "",
            }
        )
        return _result(coding, coding.model_dump_json(), 1, 0.0, None, [])


def _result(coding, raw, attempts, latency, usage, errors) -> dict[str, Any]:
    return {
        "ok": coding is not None,
        "coding": coding.model_dump() if coding is not None else None,
        "raw": raw,
        "attempts": attempts,
        "latency_s": latency,
        "usage": usage,
        "errors": errors,
    }


def make_scorer(settings: dict[str, Any], rubric: dict[str, Any]):
    if settings.get("backend") == "mock":
        return MockScorer(settings, rubric)
    return OpenAICompatScorer(settings, rubric)
