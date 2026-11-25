"""Route optimisation: reorder the stops of a plan to cut steps and fit in missed coins.

The greedy planner visits the nearest coin first, which strands coins and forces
long back-tracks. This module treats the route as an ordered list of stops
(coins and keys, then the treasure) and improves the order with local search:

* **or-opt**: move a run of 1-3 stops elsewhere (optionally reversed)
* **2-opt**: reverse a section of the route
* **insertion**: add coins the route missed wherever they fit within the limits
* **iterated restarts**: shake a good route (double-bridge move) and re-optimise

Every candidate order is scored by walking it with real shortest paths per key set,
so doors stay locked until their key has been collected. A route is only accepted
if it keeps ``min_hearts_left`` hearts and fits within ``max_steps``.
"""

from __future__ import annotations

import heapq
import random
import time
from dataclasses import replace
from typing import Tuple

from .grid import Cell, Maze
from .planner import DIRECTIONS, Plan, Rules, _Walker

Score = Tuple[int, int, int]  # (damage, monsters faced, steps)
Leg = Tuple[Cell, ...]

_SEED = 7


class _Router:
    """Cached shortest paths between cells for a fixed set of keys."""

    def __init__(self, maze: Maze, rules: Rules) -> None:
        self.maze = maze
        self.rules = rules
        self._trees: dict[tuple, dict[Cell, Cell]] = {}
        self._legs: dict[tuple, Leg | None] = {}

    def leg(
        self, src: Cell, keys: frozenset[str], cleared: frozenset[Cell], dst: Cell
    ) -> Leg | None:
        key = (src, keys, cleared, dst)
        if key not in self._legs:
            prev = self._tree(src, keys, cleared)
            if dst not in prev:
                self._legs[key] = None
            else:
                cells = []
                cur = dst
                while cur != src:
                    cells.append(cur)
                    cur = prev[cur]
                self._legs[key] = tuple(reversed(cells))
        return self._legs[key]

    def _tree(self, src: Cell, keys: frozenset[str], cleared: frozenset[Cell]) -> dict[Cell, Cell]:
        """Dijkstra from ``src`` minimising (damage, monsters, steps); returns parents.

        Monsters already beaten (``cleared``) are free to walk through.
        """
        tree_key = (src, keys, cleared)
        if tree_key in self._trees:
            return self._trees[tree_key]
        maze, rules = self.maze, self.rules
        dist: dict[Cell, Score] = {src: (0, 0, 0)}
        prev: dict[Cell, Cell] = {}
        heap = [((0, 0, 0), src)]
        while heap:
            cost, cell = heapq.heappop(heap)
            if cost > dist[cell] or (cell == maze.treasure and cell != src):
                continue
            for dr, dc in DIRECTIONS:
                nxt = (cell[0] + dr, cell[1] + dc)
                if not maze.in_bounds(nxt) or nxt in maze.walls:
                    continue
                if nxt in maze.doors and maze.doors[nxt] not in keys:
                    continue
                damage, monsters, steps = cost
                if nxt in maze.spikes:
                    damage += rules.spike_damage
                if nxt in maze.monsters and nxt not in cleared:
                    damage += rules.monster_damage
                    monsters += 1
                new = (damage, monsters, steps + 1)
                if nxt not in dist or new < dist[nxt]:
                    dist[nxt] = new
                    prev[nxt] = cell
                    heapq.heappush(heap, (new, nxt))
        self._trees[tree_key] = prev
        return prev


class _Evaluator:
    """Scores an order of stops by walking it."""

    def __init__(self, maze: Maze, rules: Rules, finish: bool) -> None:
        self.maze = maze
        self.rules = rules
        self.finish = finish
        self.router = _Router(maze, rules)

    def score(self, order: list[Cell]) -> Score | None:
        walked = self.walk(order)
        return None if walked is None else walked[0]

    def walk(self, order: list[Cell]) -> tuple[Score, list[Leg]] | None:
        maze, rules = self.maze, self.rules
        pos, keys = maze.start, frozenset()
        taken: set[Cell] = {maze.start}
        cleared: frozenset[Cell] = frozenset()
        damage = monsters = steps = 0
        legs: list[Leg] = []
        stops = order + [maze.treasure] if self.finish else order
        for stop in stops:
            if stop in taken and stop != maze.treasure:
                continue  # already collected on an earlier leg
            leg = self.router.leg(pos, keys, cleared, stop)
            if leg is None:
                return None
            for cell in leg:
                taken.add(cell)
                if cell in maze.keys:
                    keys = keys | {maze.keys[cell]}
                if cell in maze.spikes:
                    damage += rules.spike_damage
                if cell in maze.monsters and cell not in cleared:
                    cleared = cleared | {cell}
                    monsters += 1
                    damage += rules.monster_damage
            steps += len(leg)
            if rules.hearts - damage < rules.min_hearts_left:
                return None
            if rules.max_steps is not None and steps > rules.max_steps:
                return None
            legs.append(leg)
            pos = stop
        return (damage, monsters, steps), legs


def _stops_in_order(maze: Maze, plan: Plan) -> list[Cell]:
    """Coins and keys in the order the plan first reaches them."""
    seen: set[Cell] = set()
    order = []
    for cell in plan.path[1:]:
        if cell not in seen and (cell in maze.coins or cell in maze.keys):
            seen.add(cell)
            order.append(cell)
    return order


def _local_search(order: list[Cell], best: Score, ev: _Evaluator, deadline: float):
    improved = True
    while improved and time.monotonic() < deadline:
        improved = False
        n = len(order)
        # or-opt: relocate a run of 1-3 stops, forwards or reversed
        for size in (1, 2, 3):
            for i in range(n - size + 1):
                run, rest = order[i : i + size], order[:i] + order[i + size :]
                variants = (run, run[::-1]) if size > 1 else (run,)
                for j in range(len(rest) + 1):
                    if j == i:
                        continue
                    for variant in variants:
                        cand = rest[:j] + variant + rest[j:]
                        score = ev.score(cand)
                        if score is not None and score < best:
                            order, best, improved = cand, score, True
                            break
                    if improved:
                        break
                if improved or time.monotonic() > deadline:
                    break
            if improved:
                break
        if improved:
            continue
        # 2-opt: reverse a section
        for i in range(n - 1):
            for j in range(i + 2, n + 1):
                cand = order[:i] + order[i:j][::-1] + order[j:]
                score = ev.score(cand)
                if score is not None and score < best:
                    order, best, improved = cand, score, True
                    break
            if improved or time.monotonic() > deadline:
                break
    return order, best


def _insert_missed(order: list[Cell], missed: list[Cell], ev: _Evaluator):
    """Cheapest feasible insertion of each missed coin; returns the new order."""
    for coin in sorted(missed):
        best = None
        for j in range(len(order) + 1):
            cand = order[:j] + [coin] + order[j:]
            score = ev.score(cand)
            if score is not None and (best is None or score < best[0]):
                best = (score, cand)
        if best is not None:
            order = best[1]
    return order


def _double_bridge(order: list[Cell], rng: random.Random) -> list[Cell]:
    if len(order) < 8:
        return order[::-1]
    a, b, c = sorted(rng.sample(range(1, len(order)), 3))
    return order[:a] + order[c:] + order[b:c] + order[a:b]


def _collected(maze: Maze, ev: _Evaluator, order: list[Cell]) -> int:
    walked = ev.walk(order)
    if walked is None:
        return -1
    cells = {c for leg in walked[1] for c in leg}
    return len(cells & maze.coins)


def _improve(maze: Maze, rules: Rules, ev: _Evaluator, order: list[Cell], deadline: float):
    """Local search plus iterated restarts and missed-coin insertion."""
    best = ev.score(order)
    if best is None:
        return None
    order, best = _local_search(order, best, ev, deadline)
    rng = random.Random(_SEED)
    for _ in range(rules.optimize_rounds):
        if time.monotonic() > deadline:
            break
        # Try to fit in coins the route still misses, then shake and re-optimise.
        missed = sorted(maze.coins - set(order))
        if missed:
            grown = _insert_missed(order, missed, ev)
            if _collected(maze, ev, grown) > _collected(maze, ev, order):
                order, best = _local_search(grown, ev.score(grown), ev, deadline)
        kicked = _double_bridge(order, rng)
        score = ev.score(kicked)
        if score is None:
            continue
        cand, cand_best = _local_search(kicked, score, ev, deadline)
        if cand_best < best and _collected(maze, ev, cand) >= _collected(maze, ev, order):
            order, best = cand, cand_best
    return order


def _fit_to_limit(maze: Maze, rules: Rules, finish: bool, deadline: float):
    """Optimise a route over every coin ignoring ``max_steps``, then drop the stops
    whose removal saves the most steps until the route fits the limit."""
    from .planner import _greedy_route

    free_rules = replace(rules, max_steps=None)
    free = _Evaluator(maze, free_rules, finish)
    order = _stops_in_order(maze, _greedy_route(maze, free_rules))
    score = free.score(order)
    if score is None:
        return None
    order, score = _local_search(order, score, free, deadline)
    while score[2] > rules.max_steps:
        best = None
        for i in range(len(order)):
            cand = order[:i] + order[i + 1 :]
            cand_score = free.score(cand)
            if cand_score is not None and (best is None or cand_score < best[0]):
                best = (cand_score, cand)
        if best is None:
            return None
        score, order = best
    return order


def optimize_plan(maze: Maze, rules: Rules, plan: Plan) -> Plan:
    """Return a plan that collects at least as many coins as ``plan`` in no more steps."""
    start_time = time.monotonic()
    budget = rules.optimize_seconds
    ev = _Evaluator(maze, rules, finish=plan.reached_treasure)
    candidates = []

    greedy_order = _improve(maze, rules, ev, _stops_in_order(maze, plan), start_time + budget / 2)
    if greedy_order is not None:
        candidates.append(greedy_order)
    if rules.max_steps is not None and plan.coins_missed:
        fitted = _fit_to_limit(maze, rules, plan.reached_treasure, start_time + budget * 0.75)
        if fitted is not None:
            fitted = _improve(maze, rules, ev, fitted, start_time + budget)
            if fitted is not None:
                candidates.append(fitted)
    if not candidates:
        return plan  # greedy route uses moves the evaluator can't reproduce; keep it

    def rank(o: list[Cell]):
        score = ev.score(o)
        return (-_collected(maze, ev, o), score)

    order = min(candidates, key=rank)
    walked = ev.walk(order)
    if walked is None:
        return plan
    w = _Walker(maze, rules)
    for leg in walked[1]:
        w.walk(list(leg))
    w.plan.reached_treasure = plan.reached_treasure
    w.plan.hearts_left = rules.hearts - w.damage
    w.plan.coins_missed = sorted(w.coins_left)
    better = (len(w.plan.coins), -len(w.plan.spikes_hit), -len(w.plan.path)) > (
        len(plan.coins),
        -len(plan.spikes_hit),
        -len(plan.path),
    )
    return w.plan if better else plan
