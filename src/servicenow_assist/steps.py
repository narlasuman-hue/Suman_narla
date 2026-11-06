"""Pull actionable resolution steps out of close notes and work notes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

# "1.", "1)", "Step 1:", "-", "*", "•" at line start.
_LIST_ITEM_RE = re.compile(r"^\s*(?:(?:step\s*)?\d{1,2}\s*[.):-]|[-*•])\s+", re.IGNORECASE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
_WS_RE = re.compile(r"\s+")

# Sentences that describe ticket admin, not a fix.
_NOISE_RE = re.compile(
    r"^(?:closing|closed|resolving|resolved|ticket|incident|request)\b"
    r"|\b(?:user confirmed|confirmed (?:with|by) (?:the )?user|no further (?:action|issues?)"
    r"|please reopen|auto[- ]?closed|thank(?:s| you))\b",
    re.IGNORECASE,
)
_MIN_STEP_CHARS = 12


@dataclass
class Step:
    """One resolution step, with the tickets it was seen in."""

    text: str
    sources: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.sources)


def _clean(line: str) -> str:
    line = _LIST_ITEM_RE.sub("", line)
    line = _WS_RE.sub(" ", line).strip(" -*•\t")
    return line[0].upper() + line[1:] if line else line


def _is_noise(text: str) -> bool:
    return len(text) < _MIN_STEP_CHARS or bool(_NOISE_RE.search(text))


def extract_steps(text: str) -> list[str]:
    """Split free-text resolution notes into an ordered list of steps.

    Numbered or bulleted lines are used as-is. Plain prose is split into
    sentences. Administrative sentences ("Closing ticket", "User confirmed")
    are dropped.
    """
    if not text:
        return []
    lines = [ln for ln in text.splitlines() if ln.strip()]
    listed = [ln for ln in lines if _LIST_ITEM_RE.match(ln)]
    if len(listed) >= 2:
        candidates = listed
    else:
        candidates = []
        for ln in lines:
            candidates.extend(_SENTENCE_SPLIT_RE.split(ln.strip()))
    steps = []
    for cand in candidates:
        step = _clean(cand).rstrip(".")
        if step and not _is_noise(step):
            steps.append(step)
    return steps


def _key(step: str) -> str:
    """Normalised form used to spot the same step written slightly differently."""
    return " ".join(re.findall(r"[a-z0-9]+", step.lower()))


def merge_steps(per_ticket: dict[str, Iterable[str]]) -> list[Step]:
    """Combine steps from several tickets, keeping order and counting repeats.

    ``per_ticket`` maps ticket number -> its steps, in order of relevance (best
    match first). Steps keep the order in which they first appear; each records
    which tickets used it, so callers can show "seen in 3 of 4 similar tickets".
    """
    merged: dict[str, Step] = {}
    for number, steps in per_ticket.items():
        for text in steps:
            key = _key(text)
            if not key:
                continue
            if key not in merged:
                merged[key] = Step(text=text)
            if number not in merged[key].sources:
                merged[key].sources.append(number)
    return list(merged.values())
