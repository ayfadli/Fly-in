"""Find candidate routes with Dijkstra + Yen, then give each drone the best one."""

import heapq
from itertools import count

from graph import Graph, ZoneType
from simulation import Simulation

Route = list[str]

_YEN_ROUTES = 15       # how many shortest routes to keep as candidates
_TRIAL_WINDOW = 20     # recent drones to replay when placing the next one


class Pathfinder:
    """Dijkstra finds one route, Yen finds several; each drone then takes the
    route on which a short trial run says it arrives soonest."""

    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def plan(self) -> list[Route]:
        """Return the route each drone should fly (list index = drone id - 1)."""
        routes = self._pick_routes(self._yen(_YEN_ROUTES))
        plan: list[Route] = []
        for _ in range(self.graph.nb_drones):
            plan.append(self._best_next_route(plan, routes))
        return plan

    def _best_next_route(self, plan: list[Route], routes: list[Route]) -> Route:
        """Add one more drone on each candidate route; keep the earliest arrival."""
        best_route, best_arrival = routes[0], None
        for route in routes:
            trial = (plan + [route])[-_TRIAL_WINDOW:]
            try:
                arrival = Simulation(self.graph, trial).arrival_of_last()
            except RuntimeError:            # this route jams the fleet: skip it
                continue
            if best_arrival is None or arrival < best_arrival:
                best_route, best_arrival = route, arrival
        return best_route

    def _turns(self, route: Route) -> int:
        """Turns one lone drone needs to fly this whole route."""
        return sum(self.graph.zones[name].enter_turns for name in route[1:])

    def _dijkstra(self, source: str, banned_zones: frozenset[str],
                  banned_links: frozenset[frozenset[str]]) -> Route | None:
        """Cheapest route (by zone weight) from `source` to the end zone."""
        cost = {source: 0}
        came_from: dict[str, str] = {}
        heap: list[tuple[int, str]] = [(0, source)]
        while heap:
            spent, here = heapq.heappop(heap)
            if spent > cost[here]:
                continue
            for nxt in self.graph.neighbours[here]:
                zone = self.graph.zones[nxt]
                if (nxt in banned_zones or zone.kind is ZoneType.BLOCKED
                        or frozenset((here, nxt)) in banned_links):
                    continue
                total = spent + zone.weight
                if total < cost.get(nxt, 1 << 30):
                    cost[nxt] = total
                    came_from[nxt] = here
                    heapq.heappush(heap, (total, nxt))
        if self.graph.end not in came_from:
            return None
        route = [self.graph.end]
        while route[-1] != source:
            route.append(came_from[route[-1]])
        return route[::-1]

    def _yen(self, k: int) -> list[Route]:
        """Yen's algorithm: the k shortest loopless routes, cheapest first."""
        shortest = self._dijkstra(self.graph.start, frozenset(), frozenset())
        if shortest is None:
            raise ValueError("the end zone is unreachable from the start")
        found: list[Route] = [shortest]
        candidates: list[tuple[int, int, Route]] = []
        tiebreak = count()
        while len(found) < k:
            previous = found[-1]
            for i in range(len(previous) - 1):
                root = previous[:i + 1]
                cut_here = frozenset(
                    frozenset((r[i], r[i + 1])) for r in found
                    if len(r) > i + 1 and r[:i + 1] == root)
                spur = self._dijkstra(root[-1], frozenset(root[:-1]), cut_here)
                if spur is None:
                    continue
                whole = root[:-1] + spur
                if whole not in found and all(whole != c for _, _, c in candidates):
                    heapq.heappush(
                        candidates, (self._turns(whole), next(tiebreak), whole))
            if not candidates:
                break
            found.append(heapq.heappop(candidates)[2])
        return found

    def _pick_routes(self, routes: list[Route]) -> list[Route]:
        """Drop a route that would fly an edge against the traffic already going
        the other way on a kept route -- head-on flow is what can deadlock."""
        kept: list[Route] = []
        used: set[tuple[str, str]] = set()
        for route in routes:
            edges = list(zip(route, route[1:]))
            if any((b, a) in used for a, b in edges):
                continue
            used.update(edges)
            kept.append(route)
        return kept or routes[:1]
