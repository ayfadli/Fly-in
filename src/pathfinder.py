import heapq
import random
from itertools import count
from typing import Dict, List, Optional, Tuple

from src.drone import Event
from src.graph import Graph
from src.zone import ZoneType

MAX_TURN_HORIZON = 200
LNS_ITERATIONS = 500
LNS_PATIENCE = 100
_UNREACHABLE = 10 ** 6
_WORST_PRIORITY = 1 << 30

State = Tuple[str, int]


class Pathfinder:
    """Time-expanded A* search with a Large Neighborhood Search polish.

    Every drone is routed on a (zone, turn) state space so that zone and
    connection capacities, as well as the atomic two-turn transit through
    restricted zones, are respected by construction. Capacity usage is
    tracked directly on the Zone/Connection reservation tables, so once a
    drone's path is accepted the graph itself remembers the occupied slots
    for every later search.
    """

    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self._heuristic = self._build_heuristic()

    def solve(self) -> List[List[Event]]:
        """Plan a conflict-free timeline for every drone in the graph."""
        if self.graph.start is None or self.graph.end is None:
            raise ValueError("The graph has no start/end zone.")

        paths: List[List[Event]] = []
        for drone_index in range(self.graph.nb_drones):
            path = self._find_single_path()
            if path is None:
                raise ValueError(
                    f"No valid route found for drone {drone_index + 1}."
                )
            paths.append(path)
            self._reserve(path, 1)

        best_paths = self._improve_with_lns(paths)
        return best_paths

    def _improve_with_lns(
        self, paths: List[List[Event]]
    ) -> List[List[Event]]:
        """Repeatedly replan a couple of drones to shrink the makespan."""
        nb_drones = self.graph.nb_drones
        best_makespan = max(path[-1][0] for path in paths)
        best_paths = [path[:] for path in paths]

        no_improvement = 0
        for _ in range(LNS_ITERATIONS):
            if no_improvement > LNS_PATIENCE or nb_drones < 2:
                break

            replan_size = min(2, nb_drones)
            indices = random.sample(range(nb_drones), replan_size)
            for index in indices:
                self._reserve(paths[index], -1)
            random.shuffle(indices)

            replanned: Dict[int, List[Event]] = {}
            for index in indices:
                new_path = self._find_single_path()
                if new_path is None:
                    break
                replanned[index] = new_path
                self._reserve(new_path, 1)

            if len(replanned) != len(indices):
                for path in replanned.values():
                    self._reserve(path, -1)
                for index in indices:
                    self._reserve(paths[index], 1)
                no_improvement += 1
                continue

            candidate_makespan = max(
                max(
                    (
                        paths[i][-1][0]
                        for i in range(nb_drones)
                        if i not in replanned
                    ),
                    default=0,
                ),
                max(path[-1][0] for path in replanned.values()),
            )

            if candidate_makespan <= best_makespan:
                for index, new_path in replanned.items():
                    paths[index] = new_path
                if candidate_makespan < best_makespan:
                    best_makespan = candidate_makespan
                    best_paths = [path[:] for path in paths]
                    no_improvement = 0
                else:
                    no_improvement += 1
            else:
                for path in replanned.values():
                    self._reserve(path, -1)
                for index in indices:
                    self._reserve(paths[index], 1)
                no_improvement += 1

        return best_paths

    def _reserve(self, path: List[Event], delta: int) -> None:
        """Add (or remove, with delta=-1) a path from the capacity tables."""
        for turn, kind, name in path[1:]:
            if kind == "conn":
                self.graph.connection_named(name).reserve(turn, delta)
            else:
                self.graph.zones[name].reserve(turn, delta)

    def _find_single_path(self) -> Optional[List[Event]]:
        """A* search for one drone through the (zone, turn) state space."""
        assert self.graph.start is not None and self.graph.end is not None
        start_name = self.graph.start.name
        end_name = self.graph.end.name

        counter = count()
        visited: Dict[State, Tuple[Optional[str], Optional[int], List[Event]]]
        visited = {(start_name, 0): (None, None, [])}
        best_priority: Dict[State, int] = {(start_name, 0): 0}
        queue: List[Tuple[int, int, int, int, str]] = [
            (
                self._heuristic.get(start_name, 0),
                0,
                next(counter),
                0,
                start_name,
            )
        ]

        def reconstruct(zone_name: str, turn: int) -> List[Event]:
            prev_zone, prev_turn, added = visited[(zone_name, turn)]
            if prev_zone is None or prev_turn is None:
                return added
            return reconstruct(prev_zone, prev_turn) + added

        def consider(
            from_zone: str,
            from_turn: int,
            to_zone: str,
            to_turn: int,
            priority_score: int,
            events: List[Event],
        ) -> None:
            state = (to_zone, to_turn)
            if best_priority.get(state, _WORST_PRIORITY) <= priority_score:
                return
            best_priority[state] = priority_score
            visited[state] = (from_zone, from_turn, events)
            f_score = to_turn + self._heuristic.get(to_zone, 0)
            heapq.heappush(
                queue,
                (f_score, priority_score, next(counter), to_turn, to_zone),
            )

        while queue:
            _, priority_score, _, turn, zone_name = heapq.heappop(queue)

            if zone_name == end_name:
                path = [(0, "zone", start_name)]
                path.extend(reconstruct(zone_name, turn))
                return path

            if turn >= MAX_TURN_HORIZON:
                continue

            zone = self.graph.zones[zone_name]
            if zone.has_room_at(turn + 1):
                consider(
                    zone_name,
                    turn,
                    zone_name,
                    turn + 1,
                    priority_score,
                    [(turn + 1, "zone", zone_name)],
                )

            for neighbor in self.graph.neighbors(zone_name):
                if neighbor.zone_type == ZoneType.BLOCKED:
                    continue
                connection = self.graph.connection_between(
                    zone_name, neighbor.name
                )
                assert connection is not None
                bonus = -1 if neighbor.zone_type == ZoneType.PRIORITY else 0
                priority = priority_score + bonus

                if neighbor.zone_type == ZoneType.RESTRICTED:
                    arrival = turn + 2
                    if (
                        connection.has_room_at(turn + 1)
                        and connection.has_room_at(turn + 2)
                        and neighbor.has_room_at(arrival)
                    ):
                        consider(
                            zone_name,
                            turn,
                            neighbor.name,
                            arrival,
                            priority,
                            [
                                (turn + 1, "conn", connection.name),
                                (turn + 2, "conn", connection.name),
                                (arrival, "zone", neighbor.name),
                            ],
                        )
                else:
                    arrival = turn + 1
                    if connection.has_room_at(
                        arrival
                    ) and neighbor.has_room_at(arrival):
                        consider(
                            zone_name,
                            turn,
                            neighbor.name,
                            arrival,
                            priority,
                            [
                                (arrival, "conn", connection.name),
                                (arrival, "zone", neighbor.name),
                            ],
                        )

        return None

    def _build_heuristic(self) -> Dict[str, int]:
        """Backward Dijkstra from `end`, ignoring capacity: an A* h(n)."""
        assert self.graph.end is not None
        end_name = self.graph.end.name
        distances: Dict[str, float] = {
            name: float("inf") for name in self.graph.zones
        }
        distances[end_name] = 0.0
        queue: List[Tuple[float, str]] = [(0.0, end_name)]

        while queue:
            dist, current = heapq.heappop(queue)
            if dist > distances[current]:
                continue
            cost = float(self.graph.zones[current].zone_type.move_cost)
            if cost < 0:
                continue
            for neighbor in self.graph.neighbors(current):
                if neighbor.zone_type == ZoneType.BLOCKED:
                    continue
                new_dist = dist + cost
                if new_dist < distances[neighbor.name]:
                    distances[neighbor.name] = new_dist
                    heapq.heappush(queue, (new_dist, neighbor.name))

        return {
            name: int(dist) if dist != float("inf") else _UNREACHABLE
            for name, dist in distances.items()
        }
