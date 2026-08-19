"""Tests for the frequent issues tracker."""

import pytest
from datetime import datetime
from frequent_issues_tracker import (
    FrequentIssuesTracker,
    Issue,
    Resolution,
    ResolutionStep,
)
from frequent_issues_tracker.storage import InMemoryStorage, FileStorage
import tempfile
import shutil


@pytest.fixture
def tracker():
    """Create a fresh tracker for each test."""
    return FrequentIssuesTracker()


@pytest.fixture
def file_tracker():
    """Create a tracker with file storage."""
    temp_dir = tempfile.mkdtemp()
    tracker = FrequentIssuesTracker(FileStorage(temp_dir))
    yield tracker
    shutil.rmtree(temp_dir)


class TestIssueCreation:
    def test_create_issue(self, tracker):
        """Test creating a new issue."""
        issue = tracker.create_issue(
            issue_id="AUTH_001",
            title="Login timeout",
            description="Users getting logged out after 15 minutes",
            category="authentication",
            severity="high",
            tags=["auth", "timeout"],
        )

        assert issue.issue_id == "AUTH_001"
        assert issue.title == "Login timeout"
        assert issue.occurrences == 0
        assert issue.severity == "high"

    def test_get_issue(self, tracker):
        """Test retrieving an issue."""
        created = tracker.create_issue(
            issue_id="DB_001",
            title="Connection pool exhausted",
            description="Database connection pool running out of connections",
            category="database",
            severity="critical",
        )

        retrieved = tracker.get_issue("DB_001")
        assert retrieved is not None
        assert retrieved.issue_id == created.issue_id
        assert retrieved.title == created.title

    def test_get_nonexistent_issue(self, tracker):
        """Test retrieving a non-existent issue."""
        assert tracker.get_issue("NONEXISTENT") is None


class TestOccurrenceTracking:
    def test_record_occurrence(self, tracker):
        """Test recording issue occurrences."""
        tracker.create_issue(
            issue_id="API_001",
            title="Slow API response",
            description="API responses over 5 seconds",
            category="performance",
            severity="medium",
        )

        tracker.record_occurrence("API_001")
        tracker.record_occurrence("API_001")
        tracker.record_occurrence("API_001")

        issue = tracker.get_issue("API_001")
        assert issue.occurrences == 3

    def test_record_nonexistent_occurrence(self, tracker):
        """Test recording occurrence on non-existent issue."""
        result = tracker.record_occurrence("NONEXISTENT")
        assert result is False


class TestIssueFiltering:
    def test_list_by_category(self, tracker):
        """Test filtering issues by category."""
        tracker.create_issue(
            issue_id="AUTH_001",
            title="Login issue",
            category="authentication",
            description="Test",
            severity="high",
        )
        tracker.create_issue(
            issue_id="DB_001",
            title="Database issue",
            category="database",
            description="Test",
            severity="high",
        )

        auth_issues = tracker.list_issues(category="authentication")
        assert len(auth_issues) == 1
        assert auth_issues[0].issue_id == "AUTH_001"

    def test_list_by_severity(self, tracker):
        """Test filtering issues by severity."""
        tracker.create_issue(
            issue_id="CRITICAL_001",
            title="Critical issue",
            category="test",
            description="Test",
            severity="critical",
        )
        tracker.create_issue(
            issue_id="LOW_001",
            title="Low issue",
            category="test",
            description="Test",
            severity="low",
        )

        critical = tracker.list_issues(severity="critical")
        assert len(critical) == 1
        assert critical[0].severity == "critical"

    def test_list_sorted_by_occurrences(self, tracker):
        """Test issues are sorted by occurrences."""
        tracker.create_issue(
            issue_id="ISSUE_1",
            title="Issue 1",
            category="test",
            description="Test",
            severity="high",
        )
        tracker.create_issue(
            issue_id="ISSUE_2",
            title="Issue 2",
            category="test",
            description="Test",
            severity="high",
        )

        tracker.record_occurrence("ISSUE_2")
        tracker.record_occurrence("ISSUE_2")

        issues = tracker.list_issues()
        assert issues[0].issue_id == "ISSUE_2"


class TestResolutions:
    def test_create_resolution(self, tracker):
        """Test creating a resolution."""
        tracker.create_issue(
            issue_id="AUTH_001",
            title="Login timeout",
            description="Test",
            category="authentication",
            severity="high",
        )

        resolution = tracker.create_resolution(
            issue_id="AUTH_001",
            title="Session timeout fix",
            description="Increase session timeout and add refresh tokens",
        )

        assert resolution.issue_id == "AUTH_001"
        assert resolution.title == "Session timeout fix"
        assert resolution.times_used == 0

    def test_add_resolution_step(self, tracker):
        """Test adding steps to a resolution."""
        tracker.create_issue(
            issue_id="DB_001",
            title="Connection pool issue",
            description="Test",
            category="database",
            severity="critical",
        )

        resolution = tracker.create_resolution(
            issue_id="DB_001",
            title="Fix pool exhaustion",
            description="Test",
        )

        tracker.add_resolution_step(
            resolution_id="DB_001",
            step_description="Check connection pool size",
            order=1,
            estimated_duration_minutes=5,
        )
        tracker.add_resolution_step(
            resolution_id="DB_001",
            step_description="Increase pool size",
            order=2,
            estimated_duration_minutes=10,
        )

        resolution = tracker.get_resolution("DB_001")
        assert len(resolution.steps) == 2
        assert resolution.steps[0].order == 1
        assert resolution.steps[1].order == 2

    def test_get_unresolved_issues(self, tracker):
        """Test finding unresolved issues."""
        tracker.create_issue(
            issue_id="ISSUE_1",
            title="Issue with resolution",
            category="test",
            description="Test",
            severity="high",
        )
        tracker.create_issue(
            issue_id="ISSUE_2",
            title="Issue without resolution",
            category="test",
            description="Test",
            severity="high",
        )

        tracker.create_resolution(
            issue_id="ISSUE_1", title="Resolution 1", description="Test"
        )

        unresolved = tracker.get_unresolved_issues()
        assert len(unresolved) == 1
        assert unresolved[0].issue_id == "ISSUE_2"

    def test_mark_resolution_used_success(self, tracker):
        """Test marking resolution as successfully used."""
        tracker.create_issue(
            issue_id="TEST_001",
            title="Test issue",
            category="test",
            description="Test",
            severity="high",
        )
        tracker.create_resolution(issue_id="TEST_001", title="Test fix", description="Test")

        tracker.mark_resolution_used("TEST_001", successful=True)
        tracker.mark_resolution_used("TEST_001", successful=True)
        tracker.mark_resolution_used("TEST_001", successful=False)

        resolution = tracker.get_resolution("TEST_001")
        assert resolution.times_used == 3
        assert resolution.success_rate == pytest.approx(2 / 3)


class TestStats:
    def test_get_top_issues(self, tracker):
        """Test getting the most frequent issues."""
        for i in range(5):
            tracker.create_issue(
                issue_id=f"ISSUE_{i}",
                title=f"Issue {i}",
                category="test",
                description="Test",
                severity="high",
            )

        for i in range(3):
            tracker.record_occurrence("ISSUE_0")
        for i in range(2):
            tracker.record_occurrence("ISSUE_1")

        top = tracker.get_top_issues(limit=2)
        assert len(top) == 2
        assert top[0].issue_id == "ISSUE_0"
        assert top[0].occurrences == 3

    def test_get_critical_issues(self, tracker):
        """Test filtering critical issues."""
        tracker.create_issue(
            issue_id="CRITICAL_1",
            title="Critical issue",
            category="test",
            description="Test",
            severity="critical",
        )
        tracker.create_issue(
            issue_id="HIGH_1",
            title="High issue",
            category="test",
            description="Test",
            severity="high",
        )

        critical = tracker.get_critical_issues()
        assert len(critical) == 1
        assert critical[0].severity == "critical"

    def test_get_stats(self, tracker):
        """Test getting tracker statistics."""
        tracker.create_issue(
            issue_id="ISSUE_1",
            title="Issue 1",
            category="test",
            description="Test",
            severity="critical",
        )
        tracker.create_issue(
            issue_id="ISSUE_2",
            title="Issue 2",
            category="test",
            description="Test",
            severity="high",
        )

        tracker.record_occurrence("ISSUE_1")
        tracker.create_resolution(issue_id="ISSUE_1", title="Fix 1", description="Test")

        stats = tracker.get_stats()
        assert stats["total_issues"] == 2
        assert stats["total_occurrences"] == 1
        assert stats["critical_issues"] == 1
        assert stats["resolved_issues"] == 1
        assert stats["unresolved_issues"] == 1
        assert stats["total_resolutions"] == 1


class TestDeletion:
    def test_delete_issue(self, tracker):
        """Test deleting an issue."""
        tracker.create_issue(
            issue_id="DELETE_1",
            title="To delete",
            category="test",
            description="Test",
            severity="high",
        )

        result = tracker.delete_issue("DELETE_1")
        assert result is True
        assert tracker.get_issue("DELETE_1") is None

    def test_delete_issue_with_resolution(self, tracker):
        """Test deleting an issue also deletes its resolution."""
        tracker.create_issue(
            issue_id="DELETE_2",
            title="To delete",
            category="test",
            description="Test",
            severity="high",
        )
        tracker.create_resolution(issue_id="DELETE_2", title="Fix", description="Test")

        tracker.delete_issue("DELETE_2")
        assert tracker.get_resolution("DELETE_2") is None


class TestFileStorage:
    def test_persistence(self, file_tracker):
        """Test that file storage persists data."""
        file_tracker.create_issue(
            issue_id="PERSIST_1",
            title="Persistent issue",
            category="test",
            description="Test",
            severity="high",
        )

        retrieved = file_tracker.get_issue("PERSIST_1")
        assert retrieved is not None
        assert retrieved.title == "Persistent issue"

    def test_resolution_persistence(self, file_tracker):
        """Test that resolutions persist in file storage."""
        file_tracker.create_issue(
            issue_id="PERSIST_2",
            title="Issue for resolution",
            category="test",
            description="Test",
            severity="high",
        )
        file_tracker.create_resolution(
            issue_id="PERSIST_2",
            title="Persistent resolution",
            description="Test",
        )

        retrieved = file_tracker.get_resolution("PERSIST_2")
        assert retrieved is not None
        assert retrieved.title == "Persistent resolution"
