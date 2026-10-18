"""Check that quoted evidence actually appears in the occupation description (Q7 grounding)."""

from __future__ import annotations

import re

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def normalize(text: str) -> str:
    text = text.translate(_QUOTES).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_quotes(evidence: str) -> list[str]:
    parts = re.split(r";|\.\.\.|…|\n", evidence)
    return [p.strip().strip("'\"") for p in parts if normalize(p)]


def check_evidence(evidence: str, description: str) -> str:
    """Return 'empty', 'exact' (every quote found), 'partial' (some found) or 'not_found'."""
    quotes = split_quotes(evidence or "")
    if not quotes:
        return "empty"
    haystack = normalize(description)
    found = [normalize(q) in haystack for q in quotes]
    if all(found):
        return "exact"
    return "partial" if any(found) else "not_found"
