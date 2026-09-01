*This project has been created as part of the 42 curriculum by `<your-42-login>`.*

# Fly-in

Route a fleet of drones from a start zone to an end zone through a network of
connected zones, in as few simulation turns as possible, while respecting every
movement and capacity rule.

## Description

The program reads a **map file** describing a graph of *zones* joined by
bidirectional *connections*, then:

1. **parses** the file into a `Graph`;
2. **plans** the routes with **Dijkstra + Yen's k-shortest paths**, then gives
   each drone the route it reaches the end soonest on;
3. **simulates** the fleet turn by turn, letting a drone wait whenever the next
   zone or connection is full;
4. **prints** the mandatory `D<id>-<destination>` lines (one line per turn) on
   stdout, plus a coloured recap on stderr.

Zone types change the cost of entering a zone: `normal` and `priority` take one
turn, `restricted` takes two, `blocked` cannot be entered. `priority` zones are
preferred by the router. Zones and connections may cap how many drones they hold
at once (`max_drones`, `max_link_capacity`); the start and end zones are
unlimited.

## Instructions

```bash
make install        # install dev tools (mypy, flake8) with uv
make run ARGS=maps/easy/02_simple_fork.txt
make debug ARGS=maps/hard/01_maze_nightmare.txt   # same, under pdb
make lint           # flake8 + mypy
make lint-strict    # flake8 + mypy --strict
make clean
```

Directly, without `make`:

```bash
python3 -m src maps/medium/03_priority_puzzle.txt          # full output
python3 -m src maps/medium/03_priority_puzzle.txt 2>/dev/null   # mandatory lines only
```

Requires **Python 3.10+**. Only the standard library is used for the graph
logic (no `networkx`, `graphlib`, …).

## Algorithm and implementation strategy

The design follows the classic "find routes, then share the fleet over them"
shape. Capacity is **not** handled by the planner; it is handled by the
simulation, where it is just a "is there room to step forward? if not, wait"
check — much easier to follow than a single all-knowing search.

### 1. Dijkstra — one cheapest route (`Pathfinder._dijkstra`)

Standard priority-queue Dijkstra over the zones. The cost of an edge is the
**weight of the zone being entered**:

| zone type   | weight | meaning                          |
|-------------|:------:|----------------------------------|
| `normal`    |   10   | one turn                         |
| `priority`  |    9   | one turn, but preferred          |
| `restricted`|   20   | two turns                        |
| `blocked`   |   —    | skipped entirely                 |

The `9` is the whole of "priority zones should be preferred": an otherwise-equal
route through a priority zone comes out cheaper.

### 2. Yen — the k shortest loopless routes (`Pathfinder._yen`)

[Yen's algorithm](https://en.wikipedia.org/wiki/Yen%27s_algorithm) built on top
of Dijkstra. It keeps the routes it has accepted (`found`) and a heap of
candidates; for every prefix (`root`) of the last accepted route it removes the
links already taken from that prefix, reruns Dijkstra for the rest (`spur`), and
splices `root + spur`. We ask for `k = min(max(nb_drones, 3), 15)` routes.

### 3. Keep the compatible routes (`Pathfinder._pick_routes`)

From Yen's list, drop a route only if it would fly some connection **against**
the traffic a kept route already sends the other way. Head-on flow on a full
corridor is the one thing that can deadlock the wait-based simulation; routes
that merge or run parallel are always safe because the sim serialises them.

### 4. Give each drone the route it arrives on soonest (`Pathfinder.plan`)

Drones are placed one at a time. For each drone we add it to every candidate
route in turn, **replay the last few drones of the fleet** (`_TRIAL_WINDOW`),
and keep the route on which this drone reaches the end earliest. This is a
greedy insertion heuristic: it naturally fills short routes first, then spreads
onto slower parallel routes exactly when doing so would help — including
splitting the fleet across several restricted corridors, which is what lets the
challenger map beat its reference record.

### 5. Simulation (`Simulation._step`)

Capacity is **not** handled by the planner; it lives here, as a plain "is there
room to step forward? if not, wait" check — much easier to follow than a single
all-knowing search. Each turn:

1. every drone **mid-crossing** of a restricted connection **lands** (it must —
   it cannot linger on a connection);
2. then, repeatedly, any waiting drone **steps forward** if its next zone and
   next connection both have room, drones nearest the goal moving first, until
   nobody else can move. A drone leaving a zone frees that slot in the same
   turn.

Entering a `restricted` zone is shown as two lines: `D<id>-<connection>` on the
turn the drone leaves, then `D<id>-<zone>` on the turn it arrives.

If a whole turn passes with no drone able to move, the plan is infeasible and
the program stops with a `deadlock` error instead of looping forever.

### Complexity and memory

* Dijkstra: `O(E log V)`. Yen runs it `O(k · V)` times — a few thousand cheap
  Dijkstra runs on the largest provided map, well under a second.
* Planning replays a **bounded** window of drones per candidate route, so
  `plan()` is `O(drones · k · window · turns)` — linear in the fleet size.
  1000 drones plan and run in ~0.5 s; the 25-drone challenger, in ~0.25 s.
* Routes are chosen **once**; the final simulation is a single pass.
* Simulation: `O(turns · drones²)` worst case (one long single-file queue).
  Memory is `O(zones + drones)`.

## Visual representation

* **stdout** carries only the required, parseable movement lines.
* **stderr** carries a coloured recap: one `turn N  D1-zoneA D2-zoneB …` line
  per turn (each destination painted with its declared `color`), then a final
  `delivered N drones in T turns`. Redirect `2>/dev/null` to get the clean
  machine output.

## Performance

Turns for the provided maps against the subject's reference targets:

| map                               | drones | turns | target | met |
|-----------------------------------|:------:|:-----:|:------:|:---:|
| easy/01_linear_path               |   2    |   4   |  ≤ 6   |  ✓  |
| easy/02_simple_fork               |   4    |   4   |  ≤ 6   |  ✓  |
| easy/03_basic_capacity            |   4    |   4   |  ≤ 8   |  ✓  |
| medium/01_dead_end_trap           |   5    |   8   |  ≤ 15  |  ✓  |
| medium/02_circular_loop           |   6    |  15   |  ≤ 20  |  ✓  |
| medium/03_priority_puzzle         |   5    |   7   |  ≤ 12  |  ✓  |
| hard/01_maze_nightmare            |   8    |  13   |  ≤ 45  |  ✓  |
| hard/02_capacity_hell             |  12    |  16   |  ≤ 60  |  ✓  |
| hard/03_ultimate_challenge        |  15    |  26   |  ≤ 35  |  ✓  |
| challenger/01_the_impossible_dream |  25   |  43   | beat 45 | ✓ |

Both **bonus** targets are met: every provided map is at or under its reference
target, and the challenger map is solved in **43 turns**, beating the reference
record of 45.

## Project layout

```
src/
  __main__.py     CLI entry point: python3 -m src <map_file>
  graph.py        Zone, Connection, Graph + the map-file parser
  pathfinder.py   Pathfinder: Dijkstra, Yen, route filtering, drone assignment
  simulation.py   Drone, Simulation: the turn-by-turn loop and coloured recap
maps/             example maps (easy / medium / hard / challenger)
```

`Pathfinder` calls `Simulation` as a black-box oracle while planning ("how soon
would this drone arrive on that route?"), so the module depends on `simulation`.

## Resources

* Dijkstra, *A note on two problems in connexion with graphs* (1959).
* J. Y. Yen, *Finding the k shortest loopless paths in a network*,
  Management Science (1971) — <https://en.wikipedia.org/wiki/Yen%27s_algorithm>
* 42 `lem-in` — same "share a fleet over a set of paths" problem shape.

### Use of AI

AI was used as a pair-programming aid for: comparing path-planning strategies
(time-expanded search vs. Dijkstra + Yen) and settling on Dijkstra + Yen with a
wait-based simulation; drafting the first version of Yen's algorithm and the
turn-scheduling loop, which were then read through, tested and rewritten by
hand; working out why the challenger map stalled (the route filter was
collapsing every route onto one corridor) and moving to the simulate-and-place
assignment; and generating the throwaway map files used to check parser error
handling. Every line committed is understood and can be explained.
