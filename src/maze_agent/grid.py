"""Maze board model and text parser.

A board is written as one line per row, with whitespace-separated tokens per cell::

    S  C  C  .  .  .  .  .  C  C
    #  #  #  #  #  C  #  #  #  #
    K:red # . C C M C C # K:green

Tokens:
    ``.`` empty, ``#`` wall, ``C`` coin, ``^`` spikes, ``M`` monster / puzzle,
    ``S`` start, ``T`` treasure (goal), ``K:<color>`` key, ``D:<color>`` locked door.

Cells are ``(row, col)`` tuples, zero based. Game labels such as ``A1`` use the
column letter followed by the 1-based row number, matching the game UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

Cell = Tuple[int, int]

EMPTY = "."
WALL = "#"
COIN = "C"
SPIKE = "^"
MONSTER = "M"
START = "S"
TREASURE = "T"
KEY_PREFIX = "K:"
DOOR_PREFIX = "D:"

MAX_SIZE = 26


class MazeParseError(ValueError):
    """Raised when a board description is malformed."""


@dataclass
class Maze:
    """Static description of a maze board."""

    rows: int
    cols: int
    start: Cell
    treasure: Cell
    walls: set[Cell] = field(default_factory=set)
    coins: set[Cell] = field(default_factory=set)
    spikes: set[Cell] = field(default_factory=set)
    monsters: set[Cell] = field(default_factory=set)
    keys: dict[Cell, str] = field(default_factory=dict)
    doors: dict[Cell, str] = field(default_factory=dict)

    def in_bounds(self, cell: Cell) -> bool:
        r, c = cell
        return 0 <= r < self.rows and 0 <= c < self.cols


def to_label(cell: Cell) -> str:
    """Convert ``(row, col)`` to a game label like ``A1``."""
    r, c = cell
    return f"{chr(ord('A') + c)}{r + 1}"


def from_label(label: str) -> Cell:
    """Convert a game label like ``A1`` or ``j10`` to ``(row, col)``."""
    label = label.strip().upper()
    if len(label) < 2 or not label[0].isalpha() or not label[1:].isdigit():
        raise MazeParseError(f"Invalid cell label: {label!r}")
    return int(label[1:]) - 1, ord(label[0]) - ord("A")


def parse_maze(text: str) -> Maze:
    """Parse a board description into a :class:`Maze`.

    Blank lines and lines starting with ``//`` are ignored.
    """
    grid = [
        line.split()
        for line in text.strip().splitlines()
        if line.strip() and not line.strip().startswith("//")
    ]
    if not grid:
        raise MazeParseError("Board is empty")
    cols = len(grid[0])
    if any(len(row) != cols for row in grid):
        raise MazeParseError("All rows must have the same number of cells")
    if len(grid) > MAX_SIZE or cols > MAX_SIZE:
        raise MazeParseError(f"Board larger than {MAX_SIZE}x{MAX_SIZE}")

    start = treasure = None
    maze = Maze(rows=len(grid), cols=cols, start=(0, 0), treasure=(0, 0))
    for r, row in enumerate(grid):
        for c, token in enumerate(row):
            cell = (r, c)
            upper = token.upper()
            if upper.startswith(KEY_PREFIX):
                maze.keys[cell] = _color(token)
            elif upper.startswith(DOOR_PREFIX):
                maze.doors[cell] = _color(token)
            elif upper == WALL:
                maze.walls.add(cell)
            elif upper == COIN:
                maze.coins.add(cell)
            elif upper == SPIKE:
                maze.spikes.add(cell)
            elif upper == MONSTER:
                maze.monsters.add(cell)
            elif upper == START:
                if start is not None:
                    raise MazeParseError("More than one start cell")
                start = cell
            elif upper == TREASURE:
                if treasure is not None:
                    raise MazeParseError("More than one treasure cell")
                treasure = cell
            elif upper != EMPTY:
                raise MazeParseError(f"Unknown token {token!r} at {to_label(cell)}")
    if start is None or treasure is None:
        raise MazeParseError("Board needs exactly one start 'S' and one treasure 'T'")
    maze.start, maze.treasure = start, treasure
    return maze


def _color(token: str) -> str:
    color = token[2:].strip().lower()
    if not color:
        raise MazeParseError(f"Key/door token needs a color: {token!r}")
    return color
