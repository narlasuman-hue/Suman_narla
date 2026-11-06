"""Find previously resolved tickets like the user's and recommend their fix."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

from .client import ServiceNowClient
from .matcher import SimilarityIndex, keywords, ticket_text
from .steps import Step, extract_steps, merge_steps

logger = logging.getLogger(__name__)

DEFAULT_TABLES = ("incident", "sc_req_item")


@dataclass
class Match:
    """A resolved ticket judged to be the same problem."""

    number: str
    table: str
    short_description: str
    score: float
    close_code: str
    resolved_at: str
    steps: list[str]

    @property
    def confidence(self) -> str:
        if self.score >= 0.6:
            return "high"
        if self.score >= 0.4:
            return "medium"
        return "low"


@dataclass
class Recommendation:
    """Result of a lookup: the similar tickets and the consolidated steps."""

    query: str
    source_number: str | None = None
    matches: list[Match] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return bool(self.matches)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "source_number": self.source_number,
            "found": self.found,
            "steps": [{"text": s.text, "seen_in": s.sources} for s in self.steps],
            "matches": [{**asdict(m), "confidence": m.confidence} for m in self.matches],
        }


class IncidentAssistant:
    """Looks up similar resolved tickets and returns the steps that fixed them.

    Args:
        client: ServiceNow client used to read tickets.
        min_score: Similarity (0..1) a past ticket needs to count as the same issue.
        max_matches: How many similar tickets to draw steps from.
        candidate_limit: How many keyword hits to pull from ServiceNow before ranking.
        use_work_notes: Read work notes when a ticket's close notes have no usable steps.
    """

    def __init__(
        self,
        client: ServiceNowClient,
        min_score: float = 0.3,
        max_matches: int = 5,
        candidate_limit: int = 50,
        use_work_notes: bool = True,
    ):
        self.client = client
        self.min_score = min_score
        self.max_matches = max_matches
        self.candidate_limit = candidate_limit
        self.use_work_notes = use_work_notes

    # -- public API ----------------------------------------------------------------

    def recommend_for_ticket(
        self, number: str, tables: Sequence[str] | None = None
    ) -> Recommendation:
        """Recommend steps for an existing incident or request, e.g. ``INC0012345``."""
        record = self.client.get_record(number)
        if record is None:
            raise LookupError(f"{number} was not found in ServiceNow")
        tables = tables or (record["_table"],)
        text = ticket_text(record)
        rec = self._recommend(text, tables, exclude=record.get("number"))
        rec.query = record.get("short_description") or text
        rec.source_number = record.get("number")
        return rec

    def recommend_for_text(
        self, text: str, tables: Sequence[str] = DEFAULT_TABLES
    ) -> Recommendation:
        """Recommend steps for a problem described in free text."""
        if not text or not text.strip():
            raise ValueError("Describe the problem to search for")
        return self._recommend(text, tables)

    # -- internals -----------------------------------------------------------------

    def _recommend(
        self, text: str, tables: Sequence[str], exclude: str | None = None
    ) -> Recommendation:
        candidates = self._candidates(text, tables, exclude)
        rec = Recommendation(query=text)
        if not candidates:
            return rec

        index = SimilarityIndex([ticket_text(c) for c in candidates])
        for i, score in index.query(text):
            if score < self.min_score or len(rec.matches) >= self.max_matches:
                break
            steps = self._resolution_steps(candidates[i])
            if not steps:
                continue  # resolved, but nobody wrote down how
            c = candidates[i]
            rec.matches.append(Match(
                number=c.get("number", ""),
                table=c.get("_table", ""),
                short_description=c.get("short_description", ""),
                score=score,
                close_code=c.get("close_code", ""),
                resolved_at=c.get("resolved_at") or c.get("sys_updated_on", ""),
                steps=steps,
            ))
        rec.steps = merge_steps({m.number: m.steps for m in rec.matches})
        return rec

    def _candidates(
        self, text: str, tables: Sequence[str], exclude: str | None
    ) -> list[dict[str, Any]]:
        """Keyword-search each table, widening the search if nothing comes back."""
        words = keywords(text)
        if not words:
            return []
        seen, out = set(), []
        for table in tables:
            rows: list[dict[str, Any]] = []
            # Fewer words = broader search; try narrow first, widen if nothing matches.
            for n in sorted({min(n, len(words)) for n in (6, 3, 2)}, reverse=True):
                rows = self.client.search_resolved(
                    table, " ".join(words[:n]), self.candidate_limit, exclude_number=exclude
                )
                if rows:
                    break
            for row in rows:
                number = row.get("number")
                if number not in seen and number != exclude:
                    seen.add(number)
                    out.append(row)
        logger.info("%d candidate tickets for %r", len(out), " ".join(words))
        return out

    def _resolution_steps(self, record: dict[str, Any]) -> list[str]:
        steps = extract_steps(record.get("close_notes", ""))
        if steps or not self.use_work_notes or not record.get("sys_id"):
            return steps
        notes = self.client.get_work_notes(record["sys_id"])
        # The last notes before closure usually describe the fix.
        for note in reversed(notes):
            steps = extract_steps(note)
            if steps:
                return steps
        return []

