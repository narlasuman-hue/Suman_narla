"""Storage backends for the frequent issues tracker."""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import Issue, Resolution, ResolutionStep


class StorageBackend(ABC):
    """Abstract storage backend."""

    @abstractmethod
    def save_issue(self, issue: Issue) -> None:
        """Save an issue."""
        pass

    @abstractmethod
    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Retrieve an issue by ID."""
        pass

    @abstractmethod
    def get_all_issues(self) -> List[Issue]:
        """Retrieve all issues."""
        pass

    @abstractmethod
    def delete_issue(self, issue_id: str) -> None:
        """Delete an issue by ID."""
        pass

    @abstractmethod
    def save_resolution(self, resolution: Resolution) -> None:
        """Save a resolution."""
        pass

    @abstractmethod
    def get_resolution(self, resolution_id: str) -> Optional[Resolution]:
        """Retrieve a resolution by ID."""
        pass

    @abstractmethod
    def get_all_resolutions(self) -> List[Resolution]:
        """Retrieve all resolutions."""
        pass

    @abstractmethod
    def delete_resolution(self, resolution_id: str) -> None:
        """Delete a resolution by ID."""
        pass


class InMemoryStorage(StorageBackend):
    """In-memory storage backend."""

    def __init__(self):
        self.issues: Dict[str, Issue] = {}
        self.resolutions: Dict[str, Resolution] = {}

    def save_issue(self, issue: Issue) -> None:
        self.issues[issue.issue_id] = issue

    def get_issue(self, issue_id: str) -> Optional[Issue]:
        return self.issues.get(issue_id)

    def get_all_issues(self) -> List[Issue]:
        return list(self.issues.values())

    def delete_issue(self, issue_id: str) -> None:
        self.issues.pop(issue_id, None)

    def save_resolution(self, resolution: Resolution) -> None:
        self.resolutions[resolution.issue_id] = resolution

    def get_resolution(self, resolution_id: str) -> Optional[Resolution]:
        return self.resolutions.get(resolution_id)

    def get_all_resolutions(self) -> List[Resolution]:
        return list(self.resolutions.values())

    def delete_resolution(self, resolution_id: str) -> None:
        self.resolutions.pop(resolution_id, None)


class FileStorage(StorageBackend):
    """File-based JSON storage backend."""

    def __init__(self, base_dir: str = ".issues_tracker"):
        self.base_dir = Path(base_dir)
        self.issues_dir = self.base_dir / "issues"
        self.resolutions_dir = self.base_dir / "resolutions"
        self.issues_dir.mkdir(parents=True, exist_ok=True)
        self.resolutions_dir.mkdir(parents=True, exist_ok=True)

    def _issue_to_dict(self, issue: Issue) -> dict:
        return {
            "issue_id": issue.issue_id,
            "title": issue.title,
            "description": issue.description,
            "category": issue.category,
            "severity": issue.severity,
            "occurrences": issue.occurrences,
            "resolution_id": issue.resolution_id,
            "created_at": issue.created_at.isoformat(),
            "last_occurred_at": issue.last_occurred_at.isoformat(),
            "tags": issue.tags,
            "notes": issue.notes,
        }

    def _dict_to_issue(self, data: dict) -> Issue:
        return Issue(
            issue_id=data["issue_id"],
            title=data["title"],
            description=data["description"],
            category=data["category"],
            severity=data["severity"],
            occurrences=data.get("occurrences", 0),
            resolution_id=data.get("resolution_id"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            last_occurred_at=datetime.fromisoformat(
                data.get("last_occurred_at", datetime.now().isoformat())
            ),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
        )

    def _resolution_to_dict(self, resolution: Resolution) -> dict:
        return {
            "issue_id": resolution.issue_id,
            "title": resolution.title,
            "description": resolution.description,
            "steps": [
                {
                    "order": step.order,
                    "description": step.description,
                    "details": step.details,
                    "estimated_duration_minutes": step.estimated_duration_minutes,
                }
                for step in resolution.steps
            ],
            "success_rate": resolution.success_rate,
            "times_used": resolution.times_used,
            "last_updated": resolution.last_updated.isoformat(),
        }

    def _dict_to_resolution(self, data: dict) -> Resolution:
        steps = [
            ResolutionStep(
                order=s["order"],
                description=s["description"],
                details=s.get("details"),
                estimated_duration_minutes=s.get("estimated_duration_minutes"),
            )
            for s in data.get("steps", [])
        ]
        return Resolution(
            issue_id=data["issue_id"],
            title=data["title"],
            description=data["description"],
            steps=steps,
            success_rate=data.get("success_rate", 0.0),
            times_used=data.get("times_used", 0),
            last_updated=datetime.fromisoformat(
                data.get("last_updated", datetime.now().isoformat())
            ),
        )

    def save_issue(self, issue: Issue) -> None:
        issue_file = self.issues_dir / f"{issue.issue_id}.json"
        with open(issue_file, "w") as f:
            json.dump(self._issue_to_dict(issue), f, indent=2)

    def get_issue(self, issue_id: str) -> Optional[Issue]:
        issue_file = self.issues_dir / f"{issue_id}.json"
        if issue_file.exists():
            with open(issue_file) as f:
                return self._dict_to_issue(json.load(f))
        return None

    def get_all_issues(self) -> List[Issue]:
        issues = []
        for issue_file in self.issues_dir.glob("*.json"):
            with open(issue_file) as f:
                issues.append(self._dict_to_issue(json.load(f)))
        return issues

    def delete_issue(self, issue_id: str) -> None:
        issue_file = self.issues_dir / f"{issue_id}.json"
        issue_file.unlink(missing_ok=True)

    def save_resolution(self, resolution: Resolution) -> None:
        res_file = self.resolutions_dir / f"{resolution.issue_id}.json"
        with open(res_file, "w") as f:
            json.dump(self._resolution_to_dict(resolution), f, indent=2)

    def get_resolution(self, resolution_id: str) -> Optional[Resolution]:
        res_file = self.resolutions_dir / f"{resolution_id}.json"
        if res_file.exists():
            with open(res_file) as f:
                return self._dict_to_resolution(json.load(f))
        return None

    def get_all_resolutions(self) -> List[Resolution]:
        resolutions = []
        for res_file in self.resolutions_dir.glob("*.json"):
            with open(res_file) as f:
                resolutions.append(self._dict_to_resolution(json.load(f)))
        return resolutions

    def delete_resolution(self, resolution_id: str) -> None:
        res_file = self.resolutions_dir / f"{resolution_id}.json"
        res_file.unlink(missing_ok=True)
