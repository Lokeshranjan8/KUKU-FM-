"""Small retrieval layer over a local law knowledge base.

The model only gets to cite laws that were retrieved here, so it can't invent
sections. Retrieval is plain BM25 over a hand-written JSON file - no vector DB
needed at this size, and it's easy to debug (you can see why something matched).
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "laws.json"

STOPWORDS = set(
    """a an the and or but if of to in on at by for with from as is are was were be been
    being it its this that these those i me my we our you your he him his she her they them
    their what which who whom when where why how all any both each few more most other some
    such no nor not only own same so than too very can will just should now had has have do
    does did doing would could there here then also about into over after before again
    because while until up down out off once am got get""".split()
)


def _stem(word: str) -> str:
    # very rough stemming so "stolen", "stole", "steal" land close together
    for suffix in ("ing", "ed", "es", "s", "en"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [_stem(w) for w in words if w not in STOPWORDS and len(w) > 1]


class LawIndex:
    def __init__(self, entries: list[dict], k1: float = 1.4, b: float = 0.6):
        self.entries = entries
        self.k1, self.b = k1, b
        # keywords are repeated so they count more than the summary text
        self.docs = [
            tokenize(f"{e['title']} {e['summary']} {e['keywords']} {e['keywords']}")
            for e in entries
        ]
        self.doc_freqs = [Counter(d) for d in self.docs]
        self.avg_len = sum(len(d) for d in self.docs) / len(self.docs)
        df = Counter(term for d in self.docs for term in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def score(self, query_terms: list[str], i: int) -> float:
        freqs, length = self.doc_freqs[i], len(self.docs[i])
        total = 0.0
        for term in set(query_terms):
            tf = freqs.get(term, 0)
            if not tf:
                continue
            norm = tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / self.avg_len))
            total += self.idf[term] * norm
        return total

    def search(self, query: str, k: int = 6, min_score: float = 2.0) -> list[dict]:
        terms = tokenize(query)
        if not terms:
            return []
        scored = sorted(
            ((self.score(terms, i), i) for i in range(len(self.entries))),
            reverse=True,
        )
        return [
            {**self.entries[i], "score": round(s, 2)}
            for s, i in scored[:k]
            if s >= min_score
        ]


@lru_cache(maxsize=1)
def get_index() -> LawIndex:
    return LawIndex(json.loads(DATA_FILE.read_text(encoding="utf-8")))


def retrieve(query: str, k: int = 6) -> list[dict]:
    """Top matching laws for the story, plus the few procedure entries every case needs."""
    index = get_index()
    results = index.search(query, k=k)
    seen = {r["id"] for r in results}
    for entry in index.entries:
        if entry.get("always") and entry["id"] not in seen:
            results.append({**entry, "score": 0.0})
    return results


def format_context(results: list[dict]) -> str:
    lines = []
    for r in results:
        old = f" (earlier: {r['old_law']})" if r.get("old_law") else ""
        lines.append(
            f"[{r['id']}] {r['act']}, section {r['section']}{old} - {r['title']}: "
            f"{r['summary']} Source: {r['source_url']}"
        )
    return "\n".join(lines)
