"""SLA evaluation: is each job's current run finishing by its expected completion time?

Statuses, worst first:

* ``LATE``: past the expected completion time and the run has not completed
  (failed, still running, or not started, e.g. waiting on a failed upstream job)
* ``COMPLETED_LATE``: the run completed, but after the expected completion time
* ``AT_RISK``: not yet due, but failed/blocked by an upstream failure, or due
  within ``AT_RISK_WINDOW`` and not completed
* ``ON_TRACK``: not yet due and nothing blocking it
* ``MET``: completed by the expected completion time

A completed run only counts toward the SLA if it finished within one
schedule period (by ``frequency``) before the expected completion time;
an older success is the *previous* cycle's run.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

LATE = "LATE"
COMPLETED_LATE = "COMPLETED_LATE"
AT_RISK = "AT_RISK"
ON_TRACK = "ON_TRACK"
MET = "MET"

SEVERITY = {LATE: 0, COMPLETED_LATE: 1, AT_RISK: 2, ON_TRACK: 3, MET: 4}
AT_RISK_WINDOW = timedelta(minutes=30)

_PERIOD = {
    "HOURLY": timedelta(hours=1),
    "DAILY": timedelta(days=1),
    "WEEKLY": timedelta(days=7),
    "MONTHLY": timedelta(days=31),
}


def _minutes(delta: timedelta) -> int:
    return max(0, int(delta.total_seconds() // 60))


def evaluate_sla(
    job: Dict[str, Any],
    expected: datetime,
    last_run: Optional[datetime],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Evaluate one job node (as built by ``JobLineageService``) against its SLA.

    ``last_run`` is when the job's latest run started.
    """
    now = now or datetime.utcnow()
    period = _PERIOD.get((job.get("frequency") or "").upper(), _PERIOD["DAILY"])

    completed_at = None
    if job.get("run_status") == "SUCCESS" and last_run is not None:
        completed_at = last_run + timedelta(seconds=job.get("run_duration_seconds") or 0)
    counts = completed_at is not None and completed_at > expected - period

    if counts and completed_at <= expected:
        status, late_by, reason = MET, 0, "Completed on time"
    elif counts:
        status, late_by = COMPLETED_LATE, _minutes(completed_at - expected)
        reason = "Completed after the expected time"
    elif now > expected:
        status, late_by = LATE, _minutes(now - expected)
        reason = {
            "FAILED": "Last run failed",
            "RUNNING": "Still running",
        }.get(job.get("run_status"), "Current run has not completed")
    elif job.get("run_status") == "FAILED":
        status, late_by, reason = AT_RISK, 0, "Last run failed"
    elif job.get("impacted"):
        status, late_by = AT_RISK, 0
        reason = f"Blocked by upstream failure: {', '.join(job['impacted_by'])}"
    elif expected - now <= AT_RISK_WINDOW:
        status, late_by, reason = AT_RISK, 0, "Due within 30 minutes and not completed"
    else:
        status, late_by, reason = ON_TRACK, 0, "Not yet due"

    return {
        "status": status,
        "expected_completion": expected.isoformat(),
        "completed_at": completed_at.isoformat() if counts else None,
        "late_by_minutes": late_by,
        "reason": reason,
    }
