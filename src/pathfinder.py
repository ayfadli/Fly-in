"""Pick a few good routes with Dijkstra + Yen, then split the drones over them."""

import heapq
from itertools import count

from src.graph import Graph, ZoneType

Route = list[str]


class Pathfinder:
    """Dijkstra finds one route, Yen finds several, a greedy pass assigns drones."""

    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def plan(self) -> list[Route]:
        """Return the route each drone should fly (list index = drone id - 1)."""
        routes = self._spread_out(self._yen(min(max(self.graph.nb_drones, 3), 15)))
        length = [self._turns(route) for route in routes]
        queued = [0] * len(routes)
        assignment: list[Route] = []
        for _ in range(self.graph.nb_drones):
            best = min(range(len(routes)), key=lambda i: length[i] + queued[i])
            queued[best] += 1
            assignment.append(routes[best])
        return assignment

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

    def _spread_out(self, routes: list[Route]) -> list[Route]:
        """Keep routes that never ask a shared zone for more room than it has."""
        kept: list[Route] = []
        taken: dict[str, int] = {}
        for route in routes:
            middle = route[1:-1]
            if all(self.graph.zones[name].capacity > taken.get(name, 0)
                   for name in middle):
                for name in middle:
                    taken[name] = taken.get(name, 0) + 1
                kept.append(route)
        return kept or routes[:1]
