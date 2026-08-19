"""Data models for the frequent issues tracker."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ResolutionStep:
    """A single step in resolving an issue."""

    order: int
    description: str
    details: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None

    def __str__(self) -> str:
        return f"Step {self.order}: {self.description}"


@dataclass
class Resolution:
    """Complete resolution path for an issue."""

    issue_id: str
    title: str
    description: str
    steps: List[ResolutionStep] = field(default_factory=list)
    success_rate: float = 0.0
    times_used: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    def add_step(self, step: ResolutionStep) -> None:
        """Add a resolution step."""
        self.steps.append(step)
        self.steps.sort(key=lambda s: s.order)

    def __str__(self) -> str:
        return f"{self.title} ({self.times_used} uses, {self.success_rate:.0%} success)"


@dataclass
class Issue:
    """A tracked issue with metadata."""

    issue_id: str
    title: str
    description: str
    category: str
    severity: str  # low, medium, high, critical
    occurrences: int = 0
    resolution_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_occurred_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    def add_occurrence(self) -> None:
        """Record another occurrence of this issue."""
        self.occurrences += 1
        self.last_occurred_at = datetime.now()

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.title} ({self.occurrences} occurrences)"
