"""Structured output the LLM must return; mirrors the human coder form (Q1-Q12)."""

from __future__ import annotations

import copy
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field


class DimensionCoding(BaseModel):
    # Field order matters for generation: reason and quote before committing to a score.
    rationale: str = Field(description="One sentence applying the rubric anchors to the text.")
    evidence: str = Field(description="Exact words copied from the description; empty if score is 0.")
    score: int = Field(ge=0, le=4)
    confidence: int = Field(ge=1, le=3)


class Dimensions(BaseModel):
    D1: DimensionCoding
    D2: DimensionCoding
    D3: DimensionCoding
    D4: DimensionCoding
    D5: DimensionCoding


class Coding(BaseModel):
    q1_detail: Literal["Yes", "Partly", "No"]
    dimensions: Dimensions
    q9_overall: int = Field(ge=0, le=10)
    q10_core: Literal["Core", "Supporting", "Not relevant"]
    q11_india_today: Literal["More", "Same", "Less"]
    q12_comment: str = ""


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            return _inline_refs(copy.deepcopy(defs[node["$ref"].split("/")[-1]]), defs)
        return {k: _inline_refs(v, defs) for k, v in node.items() if k != "$defs"}
    if isinstance(node, list):
        return [_inline_refs(v, defs) for v in node]
    return node


def json_schema() -> dict[str, Any]:
    """Coding schema with $refs inlined (some guided-decoding backends do not resolve $defs)."""
    raw = Coding.model_json_schema()
    return _inline_refs(raw, raw.get("$defs", {}))


class ParseError(ValueError):
    pass


def parse_coding(text: str) -> Coding:
    """Parse model output into a Coding, tolerating code fences or text around the JSON object."""
    if not text:
        raise ParseError("empty response")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ParseError("no JSON object in response")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as e:
        raise ParseError(f"invalid JSON: {e}") from e
    try:
        return Coding.model_validate(data)
    except Exception as e:  # pydantic.ValidationError
        raise ParseError(f"schema validation failed: {e}") from e
