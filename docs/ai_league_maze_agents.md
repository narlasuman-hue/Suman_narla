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
`spike_damage`, `monster_damage`, `min_hearts_left`. Pass `start`/`collected`/`keys`
to re-plan after a puzzle or anything unexpected.

Result for the screenshot board: **all 32 coins, both keys, 0 spikes, 5/5 hearts,
135 steps**. With `max_steps=60` it returns the best route within that limit (20 coins).

### Deploy

```bash
mkdir -p build && cp -r src/maze_agent build/
(cd build && zip -r ../pathway_lambda.zip maze_agent)
# Runtime: Python 3.12+, Handler: maze_agent.lambda_handler.lambda_handler
```

No third-party dependencies. Give it 256 MB of memory and a 10-second timeout.

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

- Re-plan after every surprise. The planner runs in under half a second.
- If the game has a move or time limit, set `max_steps` to it. The planner then
  drops far-away coins first.
- If monster fights turn out to cost hearts, set `monster_damage=1`. The planner
  then keeps at least `min_hearts_left` hearts and collects only coins it can
  reach safely.
- Keep the agents' answers short. Long answers waste tokens and time.
