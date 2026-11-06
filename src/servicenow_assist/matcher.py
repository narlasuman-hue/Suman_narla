"""Text similarity used to decide whether two tickets describe the same problem.

A small TF-IDF + cosine-similarity implementation in pure Python, so the tool
needs no ML dependencies. Good enough for ticket short descriptions, which are
short and keyword-heavy.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Sequence

STOPWORDS = frozenset(
    """a an and are as at be but by can cannot could do does for from get getting got has
    have i im in is it its me my no not of on or our please so that the their them there
    this to unable us was we were when with working work works you your hi hello team
    issue problem help need needs urgent asap user users""".split()
)

# Words that mean the same thing in tickets; mapped to one canonical token.
SYNONYMS = {
    "pwd": "password", "passwd": "password", "pw": "password",
    "login": "logon", "log": "logon", "signin": "logon", "sign": "logon",
    "locked": "lockout", "lock": "lockout", "lockedout": "lockout",
    "laptop": "computer", "pc": "computer", "desktop": "computer", "workstation": "computer",
    "e-mail": "email", "mail": "email", "outlook": "email",
    "printing": "printer", "print": "printer",
    "slow": "performance", "sluggish": "performance", "lag": "performance",
    "crash": "crashes", "crashed": "crashes", "crashing": "crashes",
    "err": "error", "errors": "error",
    "access": "access", "permission": "access", "permissions": "access",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lower-case, split into words, drop stopwords, normalise synonyms and plurals."""
    tokens = []
    for raw in _TOKEN_RE.findall((text or "").lower()):
        if raw in STOPWORDS or len(raw) < 2:
            continue
        tok = SYNONYMS.get(raw, raw)
        if len(tok) > 4 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]
        tokens.append(tok)
    return tokens


def keywords(text: str, limit: int = 6) -> list[str]:
    """Distinct meaningful words from ``text``, as typed, for a server-side search.

    Unlike :func:`tokenize`, words are not synonym-mapped, because ServiceNow's
    own index only knows the words actually written in tickets.
    """
    out: list[str] = []
    for raw in _TOKEN_RE.findall((text or "").lower()):
        if raw in STOPWORDS or len(raw) < 2 or raw.isdigit() or raw in out:
            continue
        out.append(raw)
    return out[:limit]


def ticket_text(record: dict[str, str]) -> str:
    """Text that describes the *problem* of a ticket (not its resolution).

    The short description is repeated so it outweighs the long description.
    """
    parts = [
        record.get("short_description", ""),
        record.get("short_description", ""),
        record.get("description", ""),
        record.get("category", ""),
        record.get("subcategory", ""),
        record.get("cmdb_ci", ""),
    ]
    return " ".join(p for p in parts if p)


class SimilarityIndex:
    """TF-IDF vectors over a set of documents, queried by cosine similarity."""

    def __init__(self, documents: Sequence[str]):
        self._docs = [Counter(tokenize(d)) for d in documents]
        n = len(self._docs) + 1  # +1 for the query document
        df: Counter = Counter()
        for doc in self._docs:
            df.update(doc.keys())
        self._idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
        self._default_idf = math.log(1 + n) + 1.0
        self._vectors = [self._weigh(doc) for doc in self._docs]

    def _weigh(self, counts: Counter) -> dict[str, float]:
        vec = {t: (1 + math.log(c)) * self._idf.get(t, self._default_idf)
               for t, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def query(self, text: str) -> list[tuple[int, float]]:
        """Return ``(document_index, score)`` pairs, best first. Scores are 0..1."""
        q = self._weigh(Counter(tokenize(text)))
        scores = []
        for i, vec in enumerate(self._vectors):
            score = sum(w * vec.get(t, 0.0) for t, w in q.items())
            scores.append((i, round(score, 4)))
        return sorted(scores, key=lambda s: s[1], reverse=True)
