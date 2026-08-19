#!/usr/bin/env python
"""Demo script for the Frequent Issues Tracker."""

from frequent_issues_tracker import FrequentIssuesTracker


def main():
    """Run a demonstration of the frequent issues tracker."""
    tracker = FrequentIssuesTracker()

    print("=== Frequent Issues Tracker Demo ===\n")

    # Create some issues
    print("1. Creating issues...\n")

    tracker.create_issue(
        issue_id="AUTH_001",
        title="Login timeout after 15 minutes",
        description="Users get logged out unexpectedly during active sessions",
        category="authentication",
        severity="high",
        tags=["auth", "session", "ux"],
    )

    tracker.create_issue(
        issue_id="DB_001",
        title="Database connection pool exhaustion",
        description="Connections max out under load, causing cascading timeouts",
        category="database",
        severity="critical",
        tags=["database", "production", "scaling"],
    )

    tracker.create_issue(
        issue_id="PERF_001",
        title="API response time degradation",
        description="API endpoints responding slower than expected (>2s)",
        category="performance",
        severity="medium",
        tags=["api", "performance", "optimization"],
    )

    # Record occurrences
    print("2. Recording issue occurrences...\n")
    for _ in range(3):
        tracker.record_occurrence("AUTH_001")
    for _ in range(7):
        tracker.record_occurrence("DB_001")
    for _ in range(2):
        tracker.record_occurrence("PERF_001")

    # Create resolutions
    print("3. Creating resolutions...\n")

    # Auth resolution
    auth_res = tracker.create_resolution(
        issue_id="AUTH_001",
        title="Implement sliding session window",
        description="Extend session timeout on each user action",
    )

    tracker.add_resolution_step(
        resolution_id="AUTH_001",
        order=1,
        step_description="Update SessionConfig.TIMEOUT",
        details="Change from 15 to 30 minutes",
        estimated_duration_minutes=5,
    )

    tracker.add_resolution_step(
        resolution_id="AUTH_001",
        order=2,
        step_description="Implement session refresh on API calls",
        details="Update middleware to extend session on each request",
        estimated_duration_minutes=30,
    )

    # DB resolution
    db_res = tracker.create_resolution(
        issue_id="DB_001",
        title="Increase connection pool size",
        description="Scale database connections to handle peak load",
    )

    tracker.add_resolution_step(
        resolution_id="DB_001",
        order=1,
        step_description="Check current pool configuration",
        details="Query current max_connections setting",
        estimated_duration_minutes=5,
    )

    tracker.add_resolution_step(
        resolution_id="DB_001",
        order=2,
        step_description="Increase pool size in config",
        details="Set max_connections = 100 (from 50)",
        estimated_duration_minutes=5,
    )

    tracker.add_resolution_step(
        resolution_id="DB_001",
        order=3,
        step_description="Deploy and monitor",
        details="Deploy to production and watch connection metrics",
        estimated_duration_minutes=20,
    )

    # Mark resolutions as used
    print("4. Tracking resolution effectiveness...\n")
    tracker.mark_resolution_used("AUTH_001", successful=True)
    tracker.mark_resolution_used("AUTH_001", successful=True)
    tracker.mark_resolution_used("DB_001", successful=True)

    # Display results
    print("5. Displaying statistics...\n")

    stats = tracker.get_stats()
    print(f"Total Issues: {stats['total_issues']}")
    print(f"Total Occurrences: {stats['total_occurrences']}")
    print(f"Resolved: {stats['resolved_issues']}")
    print(f"Unresolved: {stats['unresolved_issues']}")
    print(f"Critical Issues: {stats['critical_issues']}")
    print(f"Avg Resolution Success Rate: {stats['average_resolution_success_rate']:.1%}\n")

    # Top issues
    print("=== Top Issues ===")
    for issue in tracker.get_top_issues(limit=3):
        print(f"  [{issue.severity.upper()}] {issue.title}: {issue.occurrences} occurrences")

    # Critical issues
    print("\n=== Critical Issues ===")
    for issue in tracker.get_critical_issues():
        status = "✓ Resolved" if issue.resolution_id else "✗ Unresolved"
        print(f"  {issue.title} - {status}")

    # Show resolutions with steps
    print("\n=== Resolution Details ===")
    for issue in tracker.list_issues()[:2]:
        if issue.resolution_id:
            res = tracker.get_resolution(issue.resolution_id)
            print(f"\n  Issue: {issue.title}")
            print(f"  Resolution: {res.title}")
            print(f"  Success Rate: {res.success_rate:.0%}")
            print(f"  Times Used: {res.times_used}")
            print(f"  Steps:")
            for step in res.steps:
                duration = f" (~{step.estimated_duration_minutes}m)" if step.estimated_duration_minutes else ""
                print(f"    {step.order}. {step.description}{duration}")


if __name__ == "__main__":
    main()
