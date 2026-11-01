"""A small BM25 keyword index, written out so you can explain every line in an interview."""

import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "a about an and are as at be by can did do does for from has have how in is it its of on or "
    "that the this to was were what when where which who why with".split()
)


def tokenize(text: str) -> list[str]:
    return [token for token in _TOKEN.findall(text.lower()) if token not in _STOPWORDS]


class BM25:
    """Okapi BM25: rewards rare words, saturates repeated words, normalises by length."""

    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self._k1 = k1
        self._b = b
        self._term_counts = [Counter(tokens) for tokens in documents]
        self._lengths = [len(tokens) for tokens in documents]
        self._average_length = sum(self._lengths) / len(self._lengths) if documents else 0.0

        document_frequency: Counter[str] = Counter()
        for counts in self._term_counts:
            document_frequency.update(counts.keys())
        total = len(documents)
        self._idf = {
            term: math.log(1 + (total - freq + 0.5) / (freq + 0.5))
            for term, freq in document_frequency.items()
        }

    def scores(self, query_tokens: list[str]) -> list[float]:
        results = []
        for counts, length in zip(self._term_counts, self._lengths):
            score = 0.0
            for term in set(query_tokens):
                frequency = counts.get(term)
                if not frequency:
                    continue
                norm = 1 - self._b + self._b * length / (self._average_length or 1.0)
                boost = frequency * (self._k1 + 1) / (frequency + self._k1 * norm)
                score += self._idf[term] * boost
            results.append(score)
        return results

    def top(self, query_tokens: list[str], n: int) -> list[int]:
        """Indices of the best-matching documents (score > 0), best first."""
        scores = self.scores(query_tokens)
        scored = [(score, index) for index, score in enumerate(scores) if score > 0]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [index for _, index in scored[:n]]
