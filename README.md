*This project has been created as part of the 42 curriculum by `<your-42-login>`.*

# Fly-in

Route a fleet of drones from a start zone to an end zone through a network of
connected zones, in as few simulation turns as possible, while respecting every
movement and capacity rule.

## Description

The program reads a **map file** describing a graph of *zones* joined by
bidirectional *connections*, then:

1. **parses** the file into a `Graph`;
2. **plans** one route per drone with **Dijkstra + Yen's k-shortest paths**;
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

### 3. Spread the fleet out (`Pathfinder._spread_out`, `Pathfinder.plan`)

* **Keep** a Yen route only while every zone it shares with an already-kept
  route still has spare capacity — a zone that holds *N* drones carries at most
  *N* of our routes. (A map with a single forced corridor keeps exactly one
  route; that is correct.)
* **Assign** each drone to the route with the smallest `length + queued`, i.e.
  "the route where I would arrive soonest counting the drones already queued
  ahead of me". Short routes fill up first, then longer ones take over once they
  would actually be faster.

### 4. Simulation (`Simulation._step`)

Each turn:

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
* Routes are computed **once**, never recomputed during the simulation.
* Simulation: `O(turns · drones²)` worst case (one long single-file queue);
  fine for the provided maps (≤ 25 drones). Memory is `O(zones + drones)`.

## Visual representation

* **stdout** carries only the required, parseable movement lines.
* **stderr** carries a coloured recap: one `turn N  D1-zoneA D2-zoneB …` line
  per turn (each destination painted with its declared `color`), then a final
  `delivered N drones in T turns`. Redirect `2>/dev/null` to get the clean
  machine output.

## Performance

Turns for the provided maps (reference targets from the subject in brackets):

| map                              | drones | turns | target |
|----------------------------------|:------:|:-----:|:------:|
| easy/01_linear_path              |   2    |   4   |  ≤ 6   |
| easy/02_simple_fork              |   4    |   4   |  ≤ 6   |
| easy/03_basic_capacity           |   4    |   4   |  ≤ 8   |
| medium/01_dead_end_trap          |   5    |   8   |  ≤ 15  |
| medium/02_circular_loop          |   6    |  15   |  ≤ 20  |
| medium/03_priority_puzzle        |   5    |   7   |  ≤ 12  |
| hard/01_maze_nightmare           |   8    |  13   |  ≤ 45  |
| hard/02_capacity_hell            |  12    |  16   |  ≤ 60  |
| hard/03_ultimate_challenge       |  15    |  26   |  ≤ 35  |
| challenger/01_the_impossible_dream |  25  |  67   | (45, optional) |

Every graded map meets its reference target. The optional challenger map is not
optimised for — the fixed-route model queues its 25 drones through the map's
single-file gates rather than interleaving them.

## Project layout

```
src/
  __main__.py     CLI entry point: python3 -m src <map_file>
  graph.py        Zone, Connection, Graph + the map-file parser
  pathfinder.py   Pathfinder: Dijkstra, Yen, route spreading, drone assignment
  simulation.py   Drone, Simulation: the turn-by-turn loop and coloured recap
maps/             example maps (easy / medium / hard / challenger)
```

## Resources

* Dijkstra, *A note on two problems in connexion with graphs* (1959).
* J. Y. Yen, *Finding the k shortest loopless paths in a network*,
  Management Science (1971) — <https://en.wikipedia.org/wiki/Yen%27s_algorithm>
* 42 `lem-in` — same "share a fleet over a set of paths" problem shape.

### Use of AI

AI was used as a pair-programming aid for: comparing path-planning strategies
(time-expanded search vs. Dijkstra + Yen) and settling on the simplest one that
still meets the targets; drafting the first version of Yen's algorithm and the
turn-scheduling loop, which were then read through, tested and rewritten by
hand; and generating the throwaway map files used to check parser error
handling. Every line committed is understood and can be explained.
