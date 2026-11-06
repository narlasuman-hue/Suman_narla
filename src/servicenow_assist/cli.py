"""Command-line interface.

Examples::

    python -m src.servicenow_assist lookup INC0012345
    python -m src.servicenow_assist search "VPN keeps disconnecting on laptop"
    python -m src.servicenow_assist search "need access to shared drive" --tables sc_req_item
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from .assistant import DEFAULT_TABLES, IncidentAssistant, Recommendation
from .client import RESOLVED_FILTER, ServiceNowClient, ServiceNowError
from .config import ServiceNowConfig


def format_recommendation(rec: Recommendation) -> str:
    """Render a recommendation as readable text."""
    head = f"{rec.source_number}: {rec.query}" if rec.source_number else f'"{rec.query}"'
    lines = [f"Problem: {head}", ""]
    if not rec.found:
        lines.append("No previously resolved ticket matches this problem closely enough.")
        lines.append("Try different wording, a lower --min-score, or route to the support team.")
        return "\n".join(lines)

    total = len(rec.matches)
    lines.append(f"Same issue was resolved before in {total} ticket(s). Suggested steps:")
    lines.append("")
    for i, step in enumerate(rec.steps, 1):
        seen = f"  [used in {step.count}/{total}]" if total > 1 else ""
        lines.append(f"  {i}. {step.text}{seen}")
    lines.append("")
    lines.append("Based on:")
    for m in rec.matches:
        when = f", resolved {m.resolved_at}" if m.resolved_at else ""
        code = f", {m.close_code}" if m.close_code else ""
        lines.append(
            f"  - {m.number} ({m.confidence} match, {m.score:.2f}{code}{when}): "
            f"{m.short_description}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="servicenow_assist",
        description="Find resolved ServiceNow tickets like yours and show the fix steps.",
    )
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--min-score", type=float, default=0.3,
                        help="similarity (0-1) needed to count as the same issue (default 0.3)")
    parser.add_argument("--max-matches", type=int, default=5,
                        help="similar tickets to draw steps from (default 5)")
    parser.add_argument("--no-work-notes", action="store_true",
                        help="only use close notes, never read work notes")
    parser.add_argument("--tables", nargs="+", choices=sorted(RESOLVED_FILTER),
                        help="tables to search (default: the ticket's own table for lookup, "
                             f"{' '.join(DEFAULT_TABLES)} for search)")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    lookup = sub.add_parser("lookup", help="recommend steps for an existing ticket number")
    lookup.add_argument("number", help="e.g. INC0012345 or RITM0012345")

    search = sub.add_parser("search", help="recommend steps for a problem description")
    search.add_argument("text", nargs="+", help="what the user is reporting")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    try:
        client = ServiceNowClient(ServiceNowConfig.from_env())
        assistant = IncidentAssistant(
            client,
            min_score=args.min_score,
            max_matches=args.max_matches,
            use_work_notes=not args.no_work_notes,
        )
        if args.command == "lookup":
            rec = assistant.recommend_for_ticket(args.number, tables=args.tables)
        else:
            rec = assistant.recommend_for_text(
                " ".join(args.text), tables=args.tables or DEFAULT_TABLES
            )
    except (ValueError, LookupError, ServiceNowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(rec.to_dict(), indent=2) if args.json else format_recommendation(rec))
    return 0 if rec.found else 1
