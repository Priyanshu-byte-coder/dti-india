"""Keyword baseline DTI on NCO text, in the spirit of Stöllinger & Guarascio (2025).

They flag an O*NET core task as digital if it contains a digital keyword and score an
occupation by its share of digital tasks. Here each sentence of the NCO description
plays the role of a task. This is a transparent benchmark for the LLM scores, and it
also drives the mock backend used to test the pipeline without a GPU.
"""

from __future__ import annotations

import re

import pandas as pd

# Keyword groups double as a crude per-dimension mapping for the mock backend.
KEYWORDS: dict[str, list[str]] = {
    "D1": [r"computers?", r"computeri[sz]ed", r"keyboard", r"terminal", r"billing machine",
           r"point of sale", r"data entry", r"word process\w*", r"tablet", r"mobile phone"],
    "D2": [r"database\w*", r"spreadsheet\w*", r"electronic (?:data|records?|files?)",
           r"digital (?:data|records?|files?)", r"data (?:processing|analysis)", r"internet"],
    "D3": [r"e-?mails?", r"online", r"website\w*", r"web", r"portal\w*", r"video ?conferenc\w*",
           r"social media", r"electronic mail"],
    "D4": [r"software", r"programm(?:ing|er)s?", r"cad", r"gis", r"cnc", r"plc",
           r"computer[- ]aided", r"computer[- ]controlled", r"automat(?:ed|ion) (?:systems?|equipment)",
           r"networks? (?:administration|server)", r"servers?"],
    "D5": [r"digital", r"multimedia", r"animation", r"graphic design\w*", r"web design\w*",
           r"develops? (?:software|applications?|programs?)"],
}

_PATTERNS = {dim: re.compile(r"\b(?:" + "|".join(words) + r")\b", re.I) for dim, words in KEYWORDS.items()}
_ANY = re.compile(r"\b(?:" + "|".join(w for ws in KEYWORDS.values() for w in ws) + r")\b", re.I)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


def keyword_hits(text: str) -> dict[str, list[str]]:
    return {dim: [m.group(0) for m in pat.finditer(text)] for dim, pat in _PATTERNS.items()}


def keyword_share(text: str) -> float:
    sents = sentences(text)
    if not sents:
        return 0.0
    return sum(bool(_ANY.search(s)) for s in sents) / len(sents)


def keyword_baseline(corpus: pd.DataFrame) -> pd.DataFrame:
    out = corpus[["nco2015", "family4", "group3", "division"]].copy()
    out["kw_share"] = corpus["description"].map(keyword_share)
    out["kw_any"] = (out["kw_share"] > 0).astype(int)
    hits = corpus["description"].map(keyword_hits)
    for dim in KEYWORDS:
        out[f"kw_{dim}"] = hits.map(lambda h, d=dim: len(h[d]))
    return out
