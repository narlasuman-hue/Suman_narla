"""Tests for the maze pathway planner and its Lambda handler."""

import json
from pathlib import Path

import pytest

from src.maze_agent import MazeParseError, Rules, from_label, parse_maze, plan_route, to_label
from src.maze_agent.lambda_handler import lambda_handler, solve

BOARD = (Path(__file__).parent.parent / "src/maze_agent/boards/league_maze_1.txt").read_text()


def _adjacent(path):
    return all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(path, path[1:]))


def test_labels_round_trip():
    assert to_label((0, 0)) == "A1"
    assert to_label((9, 9)) == "J10"
    assert from_label("j10") == (9, 9)
    with pytest.raises(MazeParseError):
        from_label("10J")


def test_parse_maze_league_board():
    maze = parse_maze(BOARD)
    assert (maze.rows, maze.cols) == (10, 10)
    assert maze.start == from_label("A1")
    assert maze.treasure == from_label("A10")
    assert len(maze.coins) == 32
    assert maze.keys[from_label("A3")] == "red"
    assert maze.doors[from_label("C10")] == "red"


@pytest.mark.parametrize(
    "text",
    ["", "S C\nT", "S X T", "S T S", "S . .", "S K: T"],
)
def test_parse_maze_rejects_bad_boards(text):
    with pytest.raises(MazeParseError):
        parse_maze(text)


def test_plan_route_league_board_collects_everything_without_spikes():
    maze = parse_maze(BOARD)
    plan = plan_route(maze)
    assert plan.reached_treasure
    assert plan.path[0] == maze.start and plan.path[-1] == maze.treasure
    assert _adjacent(plan.path)
    assert not any(c in maze.walls for c in plan.path)
    assert len(plan.coins) == 32
    assert plan.spikes_hit == []
    assert plan.hearts_left == 5
    assert set(plan.keys) == {"red", "green"}
    # The red key must be picked up before walking through the red door.
    red_key = plan.path.index(from_label("A3"))
    assert red_key < plan.path.index(from_label("C10"))


def test_plan_route_prefers_long_safe_path_over_spikes():
    maze = parse_maze(
        """
        S ^ T
        . # .
        . . .
        """
    )
    plan = plan_route(maze)
    assert plan.spikes_hit == []
    assert plan.moves == ["DOWN", "DOWN", "RIGHT", "RIGHT", "UP", "UP"]


def test_plan_route_crosses_spikes_only_when_needed_and_affordable():
    maze = parse_maze("S ^ C T")
    plan = plan_route(maze, Rules(hearts=2))
    assert plan.reached_treasure
    assert [to_label(c) for c in plan.spikes_hit] == ["B1"]
    assert plan.hearts_left == 1

    blocked = plan_route(maze, Rules(hearts=1))
    assert not blocked.reached_treasure
    assert blocked.hearts_left == 1


def test_plan_route_respects_step_limit():
    maze = parse_maze(BOARD)
    plan = plan_route(maze, Rules(max_steps=60))
    assert plan.reached_treasure
    assert len(plan.path) - 1 <= 60
    assert 0 < len(plan.coins) < 32


def test_plan_route_falls_back_to_safe_coins_when_treasure_too_costly():
    maze = parse_maze(BOARD)
    plan = plan_route(maze, Rules(monster_damage=1))
    assert not plan.reached_treasure
    assert plan.hearts_left >= 1
    assert len(plan.coins) > 0


def test_solve_replans_mid_game():
    result = solve({"maze": BOARD, "start": "F5", "keys": "red", "collected": "B1,C1", "hearts": 3})
    assert result["path"][0] == "F5"
    assert result["path"][-1] == "A10"
    assert "red" not in result["keys"]
    assert result["coins_collected"] == 30


def test_solve_reports_errors():
    assert "error" in solve({})
    assert "error" in solve({"maze": "S X T"})


def test_lambda_handler_bedrock_function_event():
    event = {
        "actionGroup": "pathway",
        "function": "plan_route",
        "parameters": [{"name": "maze", "type": "string", "value": BOARD}],
        "sessionAttributes": {"a": "b"},
    }
    out = lambda_handler(event)
    assert out["messageVersion"] == "1.0"
    assert out["sessionAttributes"] == {"a": "b"}
    body = json.loads(out["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
    assert body["reached_treasure"] is True


def test_lambda_handler_bedrock_openapi_event():
    event = {
        "actionGroup": "pathway",
        "apiPath": "/plan",
        "httpMethod": "POST",
        "requestBody": {
            "content": {"application/json": {"properties": [{"name": "maze", "value": BOARD}]}}
        },
    }
    out = lambda_handler(event)
    assert out["response"]["httpStatusCode"] == 200
    body = json.loads(out["response"]["responseBody"]["application/json"]["body"])
    assert body["path"][-1] == "A10"


def test_lambda_handler_direct_invoke_error():
    out = lambda_handler({"maze": ""})
    assert out["statusCode"] == 400
