"""AWS Lambda entry point for the *pathway* sub-agent.

Accepts three event shapes:

* Bedrock Agents action group, function-details style (``event["parameters"]``)
* Bedrock Agents action group, OpenAPI style (``event["requestBody"]``)
* Direct invoke / test event: ``{"maze": "...", "hearts": 5, ...}``

Parameters:
    maze (str, required): board text, see :mod:`maze_agent.grid`.
    start (str): override start cell label, e.g. ``F5`` (re-plan mid-game).
    hearts (int): hearts currently left.
    collected (str): comma-separated labels of coins already taken.
    keys (str): comma-separated key colors already held.
    max_steps (int), spike_damage (int), monster_damage (int): rule overrides.
"""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from typing import Any

from .grid import MazeParseError, from_label, parse_maze
from .planner import Rules, plan_route

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_INT_PARAMS = ("hearts", "max_steps", "spike_damage", "monster_damage", "min_hearts_left")


def solve(params: dict[str, Any]) -> dict[str, Any]:
    """Plan a route from plain parameters. Returns a JSON-serialisable dict."""
    maze_text = params.get("maze")
    if not maze_text:
        return {"error": "Missing required parameter 'maze'"}
    try:
        maze = parse_maze(str(maze_text))
        rules = Rules()
        overrides = {k: int(params[k]) for k in _INT_PARAMS if params.get(k) not in (None, "")}
        rules = replace(rules, **overrides)

        if params.get("start"):
            maze.start = from_label(str(params["start"]))
        for label in _split(params.get("collected")):
            maze.coins.discard(from_label(label))
        # Keys already held: drop them from the board and unlock their doors.
        held = {c.lower() for c in _split(params.get("keys"))}
        maze.keys = {cell: color for cell, color in maze.keys.items() if color not in held}
        maze.doors = {cell: color for cell, color in maze.doors.items() if color not in held}
    except (MazeParseError, ValueError, TypeError) as exc:
        return {"error": f"Invalid input: {exc}"}

    plan = plan_route(maze, rules)
    return plan.to_dict()


def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    logger.info("Pathway request keys: %s", list(event.keys()))
    params = _extract_params(event)
    result = solve(params)
    body = json.dumps(result)

    if "actionGroup" not in event:
        return {"statusCode": 400 if "error" in result else 200, "body": body}

    response: dict[str, Any] = {"actionGroup": event["actionGroup"]}
    if "apiPath" in event:
        response.update(
            apiPath=event["apiPath"],
            httpMethod=event.get("httpMethod", "POST"),
            httpStatusCode=400 if "error" in result else 200,
            responseBody={"application/json": {"body": body}},
        )
    else:
        response.update(
            function=event.get("function", "plan_route"),
            functionResponse={"responseBody": {"TEXT": {"body": body}}},
        )
    return {
        "messageVersion": "1.0",
        "response": response,
        "sessionAttributes": event.get("sessionAttributes", {}),
        "promptSessionAttributes": event.get("promptSessionAttributes", {}),
    }


def _extract_params(event: dict[str, Any]) -> dict[str, Any]:
    if isinstance(event.get("parameters"), list):
        return {p["name"]: p.get("value") for p in event["parameters"]}
    body = event.get("requestBody", {}).get("content", {}).get("application/json", {})
    if isinstance(body.get("properties"), list):
        return {p["name"]: p.get("value") for p in body["properties"]}
    return event


def _split(value: Any) -> list:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).replace(";", ",").split(",") if v.strip()]
