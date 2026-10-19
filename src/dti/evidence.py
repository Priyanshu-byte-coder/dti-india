"""Check that quoted evidence actually appears in the occupation description (Q7 grounding)."""

from __future__ import annotations

import re

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})
_STOP = {"a", "an", "and", "the", "of", "or", "to", "in", "on", "for", "with", "by", "as", "at", "etc"}


def normalize(text: str) -> str:
    text = text.translate(_QUOTES).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_quotes(evidence: str) -> list[str]:
    parts = re.split(r";|\.\.\.|…|\n", evidence)
    return [p.strip().strip("'\"") for p in parts if normalize(p)]


def _in_order(quote: str, haystack: str) -> bool:
    """All content words of the quote occur in the description, in the same order, within a
    short window: accepts a quote that drops small words ('design, develop, evaluate' for
    'design, develop, and evaluate') but not invented wording."""
    words = [w for w in quote.split() if w not in _STOP]
    if not words:
        return False
    tokens = haystack.split()
    for start in (i for i, t in enumerate(tokens) if t == words[0]):
        pos, ok = start, True
        for w in words[1:]:
            window = tokens[pos + 1 : pos + 4]  # next content word within 3 tokens
            if w in window:
                pos = pos + 1 + window.index(w)
            else:
                ok = False
                break
        if ok:
            return True
    return False


def check_evidence(evidence: str, description: str) -> str:
    """Return 'empty', 'exact' (every quote found verbatim), 'close' (every quote found with
    small words dropped), 'partial' (some found) or 'not_found'."""
    quotes = split_quotes(evidence or "")
    if not quotes:
        return "empty"
    haystack = normalize(description)
    exact = [normalize(q) in haystack for q in quotes]
    if all(exact):
        return "exact"
    found = [e or _in_order(normalize(q), haystack) for q, e in zip(quotes, exact)]
    if all(found):
        return "close"
    return "partial" if any(found) else "not_found"
