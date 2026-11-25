"""Route planner: collect as many coins as possible, avoid spikes, fetch keys, reach treasure.

Strategy (greedy with a safety check):

1. Run Dijkstra over ``(cell, keys held)`` from the current position. Path cost is
   compared lexicographically as ``(damage, monsters faced, steps)``, so the planner
   always prefers a longer safe path over a short path through spikes.
2. Among remaining coins and keys, pick the cheapest target whose leg still leaves
   a safe way to finish (reach the treasure with at least ``min_hearts_left``
   hearts and within ``max_steps``).
3. Walk there, collecting any coins/keys passed on the way; repeat.
4. When no target is worth/safe to take, go to the treasure.

The scoring rules of the real game are not public, so damage values are
configurable through :class:`Rules`.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import FrozenSet, Tuple

from .grid import Cell, Maze, to_label

State = Tuple[Cell, FrozenSet[str]]
Cost = Tuple[int, int, int]  # (damage, monsters faced, steps)

DIRECTIONS = {(-1, 0): "UP", (1, 0): "DOWN", (0, -1): "LEFT", (0, 1): "RIGHT"}


@dataclass(frozen=True)
class Rules:
    """Game assumptions. Tune these to match the league's scoring."""

    hearts: int = 5
    spike_damage: int = 1
    # Monsters are puzzles solved by the puzzle sub-agents; set to 1 if a fight costs a heart.
    monster_damage: int = 0
    min_hearts_left: int = 1
    max_steps: int | None = None
    # Entering the treasure usually ends the game, so never walk through it early.
    treasure_ends_game: bool = True
    # Route optimisation: random restarts after local search (0 = greedy route only),
    # capped by a wall-clock budget so the Lambda never times out.
    optimize_rounds: int = 30
    optimize_seconds: float = 5.0


@dataclass
class Plan:
    """Result of :func:`plan_route`."""

    path: list[Cell]
    coins: list[Cell] = field(default_factory=list)
    keys: list[str] = field(default_factory=list)
    spikes_hit: list[Cell] = field(default_factory=list)
    monsters: list[Cell] = field(default_factory=list)
    hearts_left: int = 0
    reached_treasure: bool = False
    coins_missed: list[Cell] = field(default_factory=list)

    @property
    def moves(self) -> list[str]:
        """Directions between consecutive cells (UP/DOWN/LEFT/RIGHT)."""
        return [DIRECTIONS[(b[0] - a[0], b[1] - a[1])] for a, b in zip(self.path, self.path[1:])]

    def to_dict(self) -> dict:
        return {
            "reached_treasure": self.reached_treasure,
            "steps": len(self.path) - 1,
            "coins_collected": len(self.coins),
            "coins_missed": [to_label(c) for c in self.coins_missed],
            "keys": self.keys,
            "spikes_hit": [to_label(c) for c in self.spikes_hit],
            "monsters_to_fight": [to_label(c) for c in self.monsters],
            "hearts_left": self.hearts_left,
            "path": [to_label(c) for c in self.path],
            "moves": self.moves,
        }


class _Walker:
    """Mutable game state while building a plan."""

    def __init__(self, maze: Maze, rules: Rules) -> None:
        self.maze = maze
        self.rules = rules
        self.pos = maze.start
        self.keys: frozenset[str] = frozenset()
        self.coins_left: set[Cell] = set(maze.coins)
        self.keys_left: dict[Cell, str] = dict(maze.keys)
        self.cleared: set[Cell] = set()
        self.damage = 0
        self.plan = Plan(path=[])
        self.walk([maze.start])  # pick up anything on the start cell (e.g. when re-planning)

    @property
    def steps(self) -> int:
        return len(self.plan.path) - 1

    def walk(self, cells: list[Cell]) -> None:
        for cell in cells:
            self.plan.path.append(cell)
            if cell in self.coins_left:
                self.coins_left.discard(cell)
                self.plan.coins.append(cell)
            if cell in self.keys_left:
                color = self.keys_left.pop(cell)
                self.keys = self.keys | {color}
                self.plan.keys.append(color)
            if cell in self.maze.spikes:
                self.damage += self.rules.spike_damage
                self.plan.spikes_hit.append(cell)
            if cell in self.maze.monsters and cell not in self.cleared:
                self.damage += self.rules.monster_damage
                self.cleared.add(cell)
                self.plan.monsters.append(cell)
        self.pos = cells[-1] if cells else self.pos


def _step_cost(maze: Maze, rules: Rules, cell: Cell, cleared: set[Cell], cost: Cost) -> Cost:
    damage, monsters, steps = cost
    if cell in maze.spikes:
        damage += rules.spike_damage
    if cell in maze.monsters and cell not in cleared:
        damage += rules.monster_damage
        monsters += 1
    return damage, monsters, steps + 1


def _dijkstra(
    maze: Maze,
    rules: Rules,
    start: Cell,
    keys: frozenset[str],
    cleared: set[Cell],
    allow_treasure: bool,
) -> tuple[dict[State, Cost], dict[State, State]]:
    origin: State = (start, keys)
    dist: dict[State, Cost] = {origin: (0, 0, 0)}
    prev: dict[State, State] = {}
    heap: list[tuple[Cost, State]] = [((0, 0, 0), origin)]
    while heap:
        cost, state = heapq.heappop(heap)
        if cost > dist[state]:
            continue
        (r, c), held = state
        if (r, c) == maze.treasure and state != origin:
            continue  # the game ends on the treasure; do not expand past it
        for dr, dc in DIRECTIONS:
            nxt = (r + dr, c + dc)
            if not maze.in_bounds(nxt) or nxt in maze.walls:
                continue
            if nxt in maze.doors and maze.doors[nxt] not in held:
                continue
            if nxt == maze.treasure and not allow_treasure:
                continue
            new_keys = held | {maze.keys[nxt]} if nxt in maze.keys else held
            new_state = (nxt, new_keys)
            new_cost = _step_cost(maze, rules, nxt, cleared, cost)
            if new_state not in dist or new_cost < dist[new_state]:
                dist[new_state] = new_cost
                prev[new_state] = state
                heapq.heappush(heap, (new_cost, new_state))
    return dist, prev


def _best_state(dist: dict[State, Cost], cell: Cell) -> State | None:
    states = [s for s in dist if s[0] == cell]
    return min(states, key=lambda s: dist[s]) if states else None


def _path_to(prev: dict[State, State], state: State) -> list[Cell]:
    cells = []
    while state in prev:
        cells.append(state[0])
        state = prev[state]
    return cells[::-1]


def _finish(maze: Maze, rules: Rules, pos: Cell, keys: frozenset[str], cleared: set[Cell]):
    """Cheapest (cost, path) from ``pos`` to the treasure, or None if unreachable."""
    dist, prev = _dijkstra(maze, rules, pos, keys, cleared, allow_treasure=True)
    state = _best_state(dist, maze.treasure)
    if state is None:
        return None
    return dist[state], _path_to(prev, state)


def _leg_damage(maze: Maze, rules: Rules, cells: list[Cell], cleared: set[Cell]) -> set[Cell]:
    return {c for c in cells if c in maze.monsters and c not in cleared}


def _affordable(rules: Rules, cost: Cost, damage: int, steps: int) -> bool:
    """True if taking ``cost`` on top of ``damage``/``steps`` stays within the rules."""
    if rules.hearts - damage - cost[0] < rules.min_hearts_left:
        return False
    return rules.max_steps is None or steps + cost[2] <= rules.max_steps


def plan_route(maze: Maze, rules: Rules | None = None) -> Plan:
    """Plan a full route for ``maze`` under ``rules``.

    Builds a greedy route, then (unless ``rules.optimize_rounds`` is 0) reorders its
    stops with local search to cut steps and fit in any coins it missed.
    """
    rules = rules or Rules()
    plan = _greedy_route(maze, rules)
    if rules.optimize_rounds > 0:
        from .optimizer import optimize_plan

        plan = optimize_plan(maze, rules, plan)
    return plan


def _greedy_route(maze: Maze, rules: Rules) -> Plan:
    """Nearest-target-first route with a safety check on every leg."""
    w = _Walker(maze, rules)
    allow_treasure_mid = not rules.treasure_ends_game
    # If the treasure cannot be reached safely at all, fall back to collecting safe coins.
    start_finish = _finish(maze, rules, w.pos, w.keys, w.cleared)
    coins_only = start_finish is None or not _affordable(rules, start_finish[0], 0, 0)

    while True:
        dist, prev = _dijkstra(maze, rules, w.pos, w.keys, w.cleared, allow_treasure_mid)
        best = None
        for target in list(w.coins_left) + list(w.keys_left):
            state = _best_state(dist, target)
            if state is None:
                continue
            cost = dist[state]
            leg = _path_to(prev, state)
            finish_cost: Cost = (0, 0, 0)
            if not coins_only:
                cleared_after = w.cleared | _leg_damage(maze, rules, leg, w.cleared)
                finish = _finish(maze, rules, target, state[1], cleared_after)
                if finish is None:
                    continue
                finish_cost = finish[0]
            total_damage = w.damage + cost[0] + finish_cost[0]
            if rules.hearts - total_damage < rules.min_hearts_left:
                continue
            if rules.max_steps is not None and w.steps + cost[2] + finish_cost[2] > rules.max_steps:
                continue
            rank = (cost, 0 if target in w.keys_left else 1)
            if best is None or rank < best[0]:
                best = (rank, leg)
        if best is None:
            break
        w.walk(best[1])

    finish = None if coins_only else _finish(maze, rules, w.pos, w.keys, w.cleared)
    if finish is not None and _affordable(rules, finish[0], w.damage, w.steps):
        w.walk(finish[1])
        w.plan.reached_treasure = True
    w.plan.hearts_left = rules.hearts - w.damage
    w.plan.coins_missed = sorted(w.coins_left)
    return w.plan
