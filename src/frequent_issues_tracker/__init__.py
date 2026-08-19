"""Frequent Issues Tracker - Track and resolve common issues efficiently."""

from .models import Issue, Resolution, ResolutionStep
from .tracker import FrequentIssuesTracker

__version__ = "0.1.0"
__all__ = ["Issue", "Resolution", "ResolutionStep", "FrequentIssuesTracker"]
