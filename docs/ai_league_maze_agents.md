# AWS AI League maze: supervisor and sub-agent design

Goal: score high by collecting the most coins, avoiding spikes, solving monster puzzles,
picking up keys and finishing on the treasure.

```
                 ┌──────────────────────────────┐
  game state ──▶ │  Supervisor agent            │ ──▶ next move(s)
                 └──┬──────────┬──────────┬─────┘
                    │          │          │
            Pathway agent  Web search  Code execution
            (Lambda:       agent       agent
            maze_agent)    (facts,     (math, logic,
                           trivia)     ciphers, code)
```

## 1. Pathway sub-agent (Lambda, in this repo)

Code: `src/maze_agent/` and the handler is
`src.maze_agent.lambda_handler.lambda_handler`.

**Don't let the LLM plan the route.** LLMs miscount grid cells. Have the supervisor
turn the board into text and let this deterministic planner pick the route.

Board format: one row per line, cells separated by spaces:

| Token | Meaning | Token | Meaning |
|---|---|---|---|
| `.` | empty | `^` | spikes |
| `#` | wall | `M` | monster / puzzle |
| `C` | coin | `S` / `T` | start / treasure |
| `K:red` | key | `D:red` | locked door |

See `src/maze_agent/boards/league_maze_1.txt` for the board from the screenshot.

Parameters: `maze` (required), `start`, `hearts`, `collected`, `keys`, `max_steps`,
`spike_damage`, `monster_damage`, `min_hearts_left`, `optimize_rounds`. Pass `start`/`collected`/`keys`
to re-plan after a puzzle or anything unexpected.

How the route is built (`planner.py` then `optimizer.py`):

1. **Greedy:** go to the nearest coin/key that still leaves a safe way to the chest.
2. **Reorder:** improve the order of stops with local search (move 1-3 stops, reverse
   sections) plus restarts that shake up the route, capped at `optimize_seconds` (5 s).
3. **Fill in:** fit in any coins the route missed if hearts and `max_steps` allow.
4. **Step limit:** also plan over every coin and drop the ones that cost the most steps
   until the route fits, then keep whichever result collects more coins.

Results for the screenshot board (0 spikes in every case):

| Setting | Greedy only | Optimised |
|---|---|---|
| No limit | 32 coins, 135 steps | **32 coins, 77 steps** |
| `max_steps=70` | n/a | 30 coins, 69 steps, chest |
| `max_steps=60` | 20 coins, 59 steps | **25 coins**, 59 steps, chest |
| `max_steps=40` | 16 coins (chest out of reach) | 18 coins |
| `monster_damage=1` | 28 coins, 85 steps | 28 coins, **65 steps** |

`optimize_rounds=0` skips step 2-4 and returns the greedy route in about 0.3 s.

### Deploy

```bash
mkdir -p build && cp -r src/maze_agent build/
(cd build && zip -r ../pathway_lambda.zip maze_agent)
# Runtime: Python 3.12+, Handler: maze_agent.lambda_handler.lambda_handler
```

No third-party dependencies. Give it 512 MB of memory and a **30-second timeout** (route
optimisation uses up to about 5 seconds).

Bedrock Agents action group (function details):

| Name | Type | Required | Description |
|---|---|---|---|
| maze | string | yes | Board text, one row per line, tokens `. # C ^ M S T K:color D:color` |
| start | string | no | Current cell label, e.g. F5 |
| hearts | integer | no | Hearts left |
| collected | string | no | Comma-separated coin cells already taken |
| keys | string | no | Comma-separated key colors already held |
| max_steps | integer | no | Move limit, if the game has one |

## 2. Supervisor prompt

```text
You are the supervisor playing a grid maze. Score = coins collected, keys, solved
puzzles and reaching the treasure. Spikes cost hearts. Never run out of hearts.

Process every turn:
1. Turn the board into the pathway format: one line per row (row 1 first), one
   token per column A..J: . # C ^ M S T K:<color> D:<color>. Put S on the
   hero's current cell. Double-check every row has exactly the same number of tokens.
2. Call the pathway agent with maze, hearts, keys held and coins already collected.
3. Follow its "moves" exactly. Do not invent your own route.
4. When a monster/puzzle appears, read it carefully and pick the agent for it:
   - facts, trivia, definitions, current events → web search agent
   - arithmetic, logic, sequences, ciphers, counting, code → code execution agent
   - simple and certain → answer directly
   Check the answer is in the exact format the puzzle asks for before submitting.
5. After a puzzle, a lost heart, or any move that did not land where expected,
   call the pathway agent again with the current state.
Never step on a spike unless the pathway agent's route says so.
Keep responses short: the move or answer, nothing else.
```

## 3. Web search agent prompt

```text
You answer factual questions for a maze puzzle. Search, then answer with the
shortest exact answer (a word, number or name). If the puzzle has options,
return the option text exactly. If sources disagree, use the most authoritative
one and say which. Never guess without searching.
```

## 4. Code execution agent prompt

```text
You solve maze puzzles by writing and running Python code. Use it for maths,
logic grids, number sequences, ciphers (Caesar, base64, reversal), anagrams,
counting and date calculations. Always run the code; never compute in your head.
Return only the final answer in the format the puzzle asks for, then one
line explaining how you got it.
```

## Score tips

- Re-plan after every surprise. A full optimised plan takes about 2-3 seconds; pass
  `optimize_rounds=0` for a sub-second greedy re-plan if time matters more than steps.
- If the game has a move or time limit, set `max_steps` to it. The planner then
  drops far-away coins first.
- If monster fights turn out to cost hearts, set `monster_damage=1`. The planner
  then keeps at least `min_hearts_left` hearts and collects only coins it can
  reach safely.
- Keep the agents' answers short. Long answers waste tokens and time.
