# Frequent Issues Tracker

A comprehensive Python system for tracking, categorizing, and managing common issues along with their resolution steps.

## Overview

The Frequent Issues Tracker helps teams:
- **Track** recurring issues and their occurrences
- **Categorize** issues by type, severity, and custom tags
- **Document** resolution procedures with step-by-step instructions
- **Measure** success rates of resolutions
- **Analyze** patterns and trends in issue frequency

## Features

### Issue Management
- Create and track issues with rich metadata
- Categorize issues (e.g., authentication, database, performance)
- Set severity levels (low, medium, high, critical)
- Tag issues for flexible organization
- Record occurrences and track temporal data
- Add notes and additional context

### Resolution Management
- Create detailed resolution procedures
- Define multi-step resolution processes with ordering
- Include detailed instructions and estimated durations
- Track resolution success rates
- Monitor how many times each resolution was used

### Analytics & Reporting
- Get the top occurring issues
- Find unresolved issues
- Filter by category, severity, or tags
- Generate statistics and reports
- Identify critical issues

### Storage Options
- **In-Memory Storage**: Fast, ephemeral storage for testing and temporary usage
- **File Storage**: JSON-based persistent storage for production use

## Installation

The module is included in the `suman-narla` package. Ensure it's installed:

```bash
pip install -e .
```

## Quick Start

### Basic Usage

```python
from frequent_issues_tracker import FrequentIssuesTracker

# Create a tracker
tracker = FrequentIssuesTracker()

# Create an issue
issue = tracker.create_issue(
    issue_id="AUTH_001",
    title="Login timeout",
    description="Users getting logged out after 15 minutes",
    category="authentication",
    severity="high",
    tags=["auth", "session"],
)

# Record an occurrence
tracker.record_occurrence("AUTH_001")

# Create a resolution
resolution = tracker.create_resolution(
    issue_id="AUTH_001",
    title="Extend session timeout",
    description="Increase session timeout and implement refresh tokens",
)

# Add resolution steps
tracker.add_resolution_step(
    resolution_id="AUTH_001",
    order=1,
    step_description="Update SessionConfig.SESSION_TIMEOUT to 3600",
    details="Change from 900 seconds (15 min) to 3600 seconds (1 hour)",
    estimated_duration_minutes=5,
)

tracker.add_resolution_step(
    resolution_id="AUTH_001",
    order=2,
    step_description="Implement refresh token endpoint",
    details="Add POST /api/auth/refresh endpoint",
    estimated_duration_minutes=30,
)

# Mark resolution as used
tracker.mark_resolution_used("AUTH_001", successful=True)

# Get statistics
stats = tracker.get_stats()
print(f"Total issues: {stats['total_issues']}")
print(f"Resolution success rate: {stats['average_resolution_success_rate']:.0%}")
```

### Using File Storage

```python
from frequent_issues_tracker import FrequentIssuesTracker
from frequent_issues_tracker.storage import FileStorage

# Create tracker with persistent storage
storage = FileStorage(base_dir=".issues_tracker")
tracker = FrequentIssuesTracker(storage)

# Use normally - data persists across runs
```

## API Reference

### FrequentIssuesTracker

#### Issue Operations

**`create_issue(issue_id, title, description, category, severity, tags=None, notes="")`**
- Creates a new issue
- Returns: `Issue` object

**`get_issue(issue_id)`**
- Retrieves an issue by ID
- Returns: `Issue` or `None`

**`list_issues(category=None, severity=None)`**
- Lists all issues with optional filtering
- Returns: Sorted list (by occurrences, descending)

**`record_occurrence(issue_id)`**
- Records an occurrence of an issue
- Returns: `bool` (success)

**`delete_issue(issue_id)`**
- Deletes an issue (also removes its resolution)
- Returns: `bool` (success)

#### Resolution Operations

**`create_resolution(issue_id, title, description)`**
- Creates a resolution for an issue
- Returns: `Resolution` object

**`get_resolution(resolution_id)`**
- Retrieves a resolution by ID
- Returns: `Resolution` or `None`

**`add_resolution_step(resolution_id, step_description, order, details=None, estimated_duration_minutes=None)`**
- Adds a step to a resolution
- Returns: `bool` (success)

**`mark_resolution_used(resolution_id, successful=True)`**
- Records resolution usage and updates success rate
- Returns: `bool` (success)

#### Analytics Operations

**`get_top_issues(limit=10)`**
- Returns most frequent issues
- Returns: List of `Issue` objects

**`get_critical_issues()`**
- Returns all critical severity issues
- Returns: List of `Issue` objects

**`get_unresolved_issues()`**
- Returns issues without resolutions
- Returns: List of `Issue` objects

**`get_stats()`**
- Returns comprehensive statistics
- Returns: Dictionary with metrics

### Data Models

#### Issue
```python
@dataclass
class Issue:
    issue_id: str
    title: str
    description: str
    category: str
    severity: str  # low, medium, high, critical
    occurrences: int = 0
    resolution_id: Optional[str] = None
    created_at: datetime
    last_occurred_at: datetime
    tags: List[str] = []
    notes: str = ""
```

#### Resolution
```python
@dataclass
class Resolution:
    issue_id: str
    title: str
    description: str
    steps: List[ResolutionStep] = []
    success_rate: float = 0.0
    times_used: int = 0
    last_updated: datetime
```

#### ResolutionStep
```python
@dataclass
class ResolutionStep:
    order: int
    description: str
    details: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
```

## Examples

### Example 1: Database Connection Pool Issue

```python
tracker = FrequentIssuesTracker()

# Create issue
issue = tracker.create_issue(
    issue_id="DB_POOL_001",
    title="Connection pool exhausted",
    description="Database connections maxed out, causing timeouts",
    category="database",
    severity="critical",
    tags=["production", "database", "performance"],
)

# Record multiple occurrences
for _ in range(5):
    tracker.record_occurrence("DB_POOL_001")

# Create resolution
resolution = tracker.create_resolution(
    issue_id="DB_POOL_001",
    title="Increase connection pool size",
    description="Scale up database connection pool configuration",
)

# Add detailed steps
steps = [
    ("Check current pool size", "Query database configuration", 5),
    ("Update pool size in config", "Set max_connections to 50", 5),
    ("Restart application", "Deploy new configuration", 10),
    ("Monitor connections", "Watch for connection usage", 5),
]

for order, desc, details, duration in enumerate(steps, 1):
    tracker.add_resolution_step(
        resolution_id="DB_POOL_001",
        order=order,
        step_description=desc,
        details=details,
        estimated_duration_minutes=duration,
    )

# Mark resolution successful
tracker.mark_resolution_used("DB_POOL_001", successful=True)
```

### Example 2: Analytics Report

```python
tracker = FrequentIssuesTracker()

# ... populate tracker with issues ...

# Get statistics
stats = tracker.get_stats()

print("=== Issue Tracker Report ===")
print(f"Total Issues: {stats['total_issues']}")
print(f"Total Occurrences: {stats['total_occurrences']}")
print(f"Resolved: {stats['resolved_issues']}")
print(f"Unresolved: {stats['unresolved_issues']}")
print(f"Critical Issues: {stats['critical_issues']}")
print(f"Avg Resolution Success Rate: {stats['average_resolution_success_rate']:.1%}")

# Top issues
print("\n=== Top 5 Issues ===")
for issue in tracker.get_top_issues(limit=5):
    print(f"- {issue.title}: {issue.occurrences} occurrences")

# Unresolved issues
print("\n=== Unresolved Issues ===")
for issue in tracker.get_unresolved_issues():
    print(f"- [{issue.severity.upper()}] {issue.title}")
```

## Testing

Run the test suite with coverage:

```bash
pytest tests/test_frequent_issues_tracker.py -v --cov=src --cov-report=html
```

## Storage Architecture

### Storage Backend Interface

Both storage implementations conform to the `StorageBackend` interface, allowing easy switching:

```python
# In-memory (default, great for testing)
tracker = FrequentIssuesTracker()

# File-based (production, persistent)
from frequent_issues_tracker.storage import FileStorage
tracker = FrequentIssuesTracker(FileStorage(".issues_tracker"))

# Custom implementation
class CustomStorage(StorageBackend):
    # Implement abstract methods
    pass

tracker = FrequentIssuesTracker(CustomStorage())
```

## Best Practices

1. **Use consistent issue IDs**: Follow a naming convention like `CATEGORY_NNN` (e.g., `AUTH_001`)
2. **Set appropriate severity levels**: Reserve "critical" for production-impacting issues
3. **Tag strategically**: Use tags for cross-cutting concerns (e.g., "production", "performance")
4. **Document resolutions thoroughly**: Include specific details and expected outcomes
5. **Track success rates**: Mark each resolution usage as successful or failed for accurate metrics
6. **Review regularly**: Use the statistics and reports to identify patterns
7. **Escalate critical issues**: Use `get_critical_issues()` in monitoring systems

## Performance Considerations

- **In-memory storage**: Best for up to ~10,000 issues, no I/O overhead
- **File storage**: Scales well, one JSON file per issue/resolution
- **Filtering**: Issues sorted by occurrences; consider caching for large datasets
- **Statistics**: Computed on-demand; cache if called frequently

## Future Enhancements

Potential features for future versions:
- Database backend (SQLite, PostgreSQL)
- REST API layer
- Web dashboard for visualization
- Issue assignment and ownership tracking
- Integration with issue tracking systems (Jira, GitHub Issues)
- Automated alerting for critical issues
- Bulk import/export capabilities
- Advanced analytics and machine learning for pattern detection

## License

Mozilla Public License 2.0 - See LICENSE file
