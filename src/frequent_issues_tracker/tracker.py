"""Main tracker class for managing frequent issues."""

from typing import List, Optional

from .models import Issue, Resolution, ResolutionStep
from .storage import InMemoryStorage, StorageBackend


class FrequentIssuesTracker:
    """Track and manage frequent issues and their resolutions."""

    def __init__(self, storage: Optional[StorageBackend] = None):
        self.storage = storage or InMemoryStorage()

    def create_issue(
        self,
        issue_id: str,
        title: str,
        description: str,
        category: str,
        severity: str,
        tags: Optional[List[str]] = None,
        notes: str = "",
    ) -> Issue:
        """Create a new tracked issue."""
        issue = Issue(
            issue_id=issue_id,
            title=title,
            description=description,
            category=category,
            severity=severity,
            tags=tags or [],
            notes=notes,
        )
        self.storage.save_issue(issue)
        return issue

    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Retrieve an issue by ID."""
        return self.storage.get_issue(issue_id)

    def list_issues(self, category: Optional[str] = None, severity: Optional[str] = None) -> List[Issue]:
        """List issues with optional filtering."""
        issues = self.storage.get_all_issues()
        if category:
            issues = [i for i in issues if i.category == category]
        if severity:
            issues = [i for i in issues if i.severity == severity]
        return sorted(issues, key=lambda x: x.occurrences, reverse=True)

    def record_occurrence(self, issue_id: str) -> bool:
        """Record an occurrence of an issue."""
        issue = self.storage.get_issue(issue_id)
        if issue:
            issue.add_occurrence()
            self.storage.save_issue(issue)
            return True
        return False

    def delete_issue(self, issue_id: str) -> bool:
        """Delete an issue."""
        issue = self.storage.get_issue(issue_id)
        if issue:
            self.storage.delete_issue(issue_id)
            if issue.resolution_id:
                self.storage.delete_resolution(issue.resolution_id)
            return True
        return False

    def create_resolution(
        self,
        issue_id: str,
        title: str,
        description: str,
    ) -> Resolution:
        """Create a new resolution for an issue."""
        resolution = Resolution(
            issue_id=issue_id,
            title=title,
            description=description,
        )
        self.storage.save_resolution(resolution)
        issue = self.storage.get_issue(issue_id)
        if issue:
            issue.resolution_id = issue_id
            self.storage.save_issue(issue)
        return resolution

    def get_resolution(self, resolution_id: str) -> Optional[Resolution]:
        """Retrieve a resolution by ID."""
        return self.storage.get_resolution(resolution_id)

    def add_resolution_step(
        self,
        resolution_id: str,
        step_description: str,
        order: int,
        details: Optional[str] = None,
        estimated_duration_minutes: Optional[int] = None,
    ) -> bool:
        """Add a step to a resolution."""
        resolution = self.storage.get_resolution(resolution_id)
        if resolution:
            step = ResolutionStep(
                order=order,
                description=step_description,
                details=details,
                estimated_duration_minutes=estimated_duration_minutes,
            )
            resolution.add_step(step)
            self.storage.save_resolution(resolution)
            return True
        return False

    def mark_resolution_used(self, resolution_id: str, successful: bool = True) -> bool:
        """Mark a resolution as used and update success rate."""
        resolution = self.storage.get_resolution(resolution_id)
        if resolution:
            resolution.times_used += 1
            if successful:
                resolution.success_rate = (
                    (resolution.success_rate * (resolution.times_used - 1) + 1)
                    / resolution.times_used
                )
            else:
                resolution.success_rate = (
                    (resolution.success_rate * (resolution.times_used - 1))
                    / resolution.times_used
                )
            self.storage.save_resolution(resolution)
            return True
        return False

    def get_top_issues(self, limit: int = 10) -> List[Issue]:
        """Get the most frequent issues."""
        issues = self.storage.get_all_issues()
        return sorted(issues, key=lambda x: x.occurrences, reverse=True)[:limit]

    def get_critical_issues(self) -> List[Issue]:
        """Get all critical severity issues."""
        return self.list_issues(severity="critical")

    def get_unresolved_issues(self) -> List[Issue]:
        """Get issues without a resolution."""
        return [i for i in self.storage.get_all_issues() if i.resolution_id is None]

    def get_stats(self) -> dict:
        """Get overall tracker statistics."""
        all_issues = self.storage.get_all_issues()
        all_resolutions = self.storage.get_all_resolutions()

        total_occurrences = sum(i.occurrences for i in all_issues)
        resolved_issues = [i for i in all_issues if i.resolution_id]
        unresolved_issues = [i for i in all_issues if not i.resolution_id]

        return {
            "total_issues": len(all_issues),
            "total_occurrences": total_occurrences,
            "resolved_issues": len(resolved_issues),
            "unresolved_issues": len(unresolved_issues),
            "total_resolutions": len(all_resolutions),
            "critical_issues": len([i for i in all_issues if i.severity == "critical"]),
            "average_resolution_success_rate": (
                sum(r.success_rate for r in all_resolutions) / len(all_resolutions)
                if all_resolutions
                else 0
            ),
        }
