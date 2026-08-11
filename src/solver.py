from collections import defaultdict
import heapq
import random
from typing import Dict, List, Tuple, Optional

from src.models import Zone


def compute_heuristics(
        zones: Dict[str, Zone], graph: Dict[str, Dict[str, int]], end_hub: str) -> Dict[str, int]:
    """Compute shortest path (ignoring capacities) from all nodes to end_hub to use as A* heuristic."""
    h_values = {node: float('inf') for node in graph}
    h_values[end_hub] = 0

    pq = [(0, end_hub)]
    while pq:
        dist, u = heapq.heappop(pq)

        if dist > h_values[u]:
            continue

        for v in graph[u]:
            if zones[v].zone_type == 'blocked':
                continue

            # Since edges are bidirectional, we can traverse backwards
            cost = 2 if zones[u].zone_type == 'restricted' else 1
            if dist + cost < h_values[v]:
                h_values[v] = dist + cost
                heapq.heappush(pq, (h_values[v], v))

    return h_values


def find_path(
    start: str,
    end: str,
    node_res: Dict[str, Dict[int, int]],
    edge_res: Dict[str, Dict[int, int]],
    zones: Dict[str, Zone],
    graph: Dict[str, Dict[str, int]],
    orig_conns: Dict[str, Dict[str, str]],
    h_values: Dict[str, int]
) -> Optional[List[Tuple[int, str, str]]]:
    """
    Finds a valid path for a single drone avoiding space-time reservations.
    Returns list of elements: (time, location_type ('zone' or 'conn'), location_name)
    """

    # pq elements: (f_score, neg_priority_count, time, current_zone)
    pq = []
    heapq.heappush(pq, (h_values[start], 0, 0, start))

    # visited maps (zone, time) -> (prev_zone, prev_time,
    # intermediate_elements)
    visited = {(start, 0): (None, None, [])}

    # best tie-breaker seen for a given (zone, time)
    best_tie = {(start, 0): 0}

    MAX_T = 200

    while pq:
        f, neg_pri, t, u = heapq.heappop(pq)

        if u == end:
            path_elements = []
            curr = (u, t)
            while curr[0] is not None:
                prev_u, prev_t, elements = visited[curr]
                path_elements = elements + path_elements
                curr = (prev_u, prev_t)
            path_elements = [(0, 'zone', start)] + path_elements
            return path_elements

        if t >= MAX_T:
            continue

        # Action 1: Wait at u
        if u in (start, end) or node_res[u][t + 1] < zones[u].max_drones:
            nxt = (u, t + 1)
            new_neg_pri = neg_pri
            if best_tie.get(nxt, float('inf')) > new_neg_pri:
                best_tie[nxt] = new_neg_pri
                visited[nxt] = (u, t, [(t + 1, 'zone', u)])
                heapq.heappush(
                    pq, (t + 1 + h_values[u], new_neg_pri, t + 1, u))

        # Action 2 & 3: Move
        for v, capacity in graph[u].items():
            if zones[v].zone_type == 'blocked':
                continue

            orig_conn = orig_conns[u][v]
            pri_bonus = -1 if zones[v].zone_type == 'priority' else 0
            new_neg_pri = neg_pri + pri_bonus

            if zones[v].zone_type in ('normal', 'priority', 'start', 'end'):
                if edge_res[orig_conn][t + 1] < capacity:
                    if v in (start,
                             end) or node_res[v][t + 1] < zones[v].max_drones:
                        nxt = (v, t + 1)
                        if best_tie.get(nxt, float('inf')) > new_neg_pri:
                            best_tie[nxt] = new_neg_pri
                            # Include the conn implicitly or just store it.
                            # To correctly reconstruct reservations later, let's prepend a 'conn' element as well!
                            # This makes it super clean.
                            visited[nxt] = (
                                u, t, [
                                    (t + 1, 'conn', orig_conn), (t + 1, 'zone', v)])
                            heapq.heappush(
                                pq, (t + 1 + h_values[v], new_neg_pri, t + 1, v))

            elif zones[v].zone_type == 'restricted':
                if edge_res[orig_conn][t +
                                       1] < capacity and edge_res[orig_conn][t +
                                                                             2] < capacity:
                    if v in (start,
                             end) or node_res[v][t + 2] < zones[v].max_drones:
                        nxt = (v, t + 2)
                        if best_tie.get(nxt, float('inf')) > new_neg_pri:
                            best_tie[nxt] = new_neg_pri
                            visited[nxt] = (
                                u, t, [
                                    (t + 1, 'conn', orig_conn), (t + 2, 'conn', orig_conn), (t + 2, 'zone', v)])
                            heapq.heappush(
                                pq, (t + 2 + h_values[v], new_neg_pri, t + 2, v))

    return None


def modify_reservations(path: List[Tuple[int,
                                         str,
                                         str]],
                        node_res: Dict[str,
                                       Dict[int,
                                            int]],
                        edge_res: Dict[str,
                                       Dict[int,
                                            int]],
                        delta: int):
    """Adds (delta=1) or removes (delta=-1) a path from reservations."""
    if not path:
        return

    for i in range(1, len(path)):
        t, loc_type, name = path[i]

        if loc_type == 'conn':
            edge_res[name][t] += delta
        elif loc_type == 'zone':
            # if we didn't move (it's a wait)
            if path[i - 1][1] == 'zone' and path[i - 1][2] == name:
                node_res[name][t] += delta
            else:
                # it's an arrival from a connection
                node_res[name][t] += delta


def solve_routing(zones: Dict[str,
                              Zone],
                  graph: Dict[str,
                              Dict[str,
                                   int]],
                  orig_conns: Dict[str,
                                   Dict[str,
                                        str]],
                  nb_drones: int,
                  start: str,
                  end: str) -> List[List[Tuple[int,
                                               str,
                                               str]]]:
    h_values = compute_heuristics(zones, graph, end)

    node_res = defaultdict(lambda: defaultdict(int))
    edge_res = defaultdict(lambda: defaultdict(int))

    paths = []

    # 1. Initial Solution (Prioritized Planning)
    for d in range(nb_drones):
        path = find_path(
            start,
            end,
            node_res,
            edge_res,
            zones,
            graph,
            orig_conns,
            h_values)
        if path is None:
            raise ValueError(f"Could not find path for drone {d+1}")
        paths.append(path)
        modify_reservations(path, node_res, edge_res, 1)

    best_makespan = max(p[-1][0] for p in paths)
    best_paths = [p[:] for p in paths]

    # 2. Large Neighborhood Search (LNS)
    no_improve = 0
    for _ in range(500):
        if no_improve > 100:
            break

        # Pick 1 or 2 drones to replan
        num_replan = min(2, nb_drones)
        idx_to_replan = random.sample(range(nb_drones), num_replan)

        for idx in idx_to_replan:
            modify_reservations(paths[idx], node_res, edge_res, -1)

        random.shuffle(idx_to_replan)

        new_subpaths = {}
        success = True
        for idx in idx_to_replan:
            new_path = find_path(
                start,
                end,
                node_res,
                edge_res,
                zones,
                graph,
                orig_conns,
                h_values)
            if new_path is None:
                success = False
                break
            new_subpaths[idx] = new_path
            modify_reservations(new_path, node_res, edge_res, 1)

        if not success:
            # Revert
            for idx in new_subpaths:
                modify_reservations(new_subpaths[idx], node_res, edge_res, -1)
            for idx in idx_to_replan:
                modify_reservations(paths[idx], node_res, edge_res, 1)
            no_improve += 1
            continue

        # Check makespan
        current_makespan = 0
        for i, p in enumerate(paths):
            if i not in idx_to_replan:
                current_makespan = max(current_makespan, p[-1][0])
        for p in new_subpaths.values():
            current_makespan = max(current_makespan, p[-1][0])

        if current_makespan < best_makespan:
            best_makespan = current_makespan
            for idx in idx_to_replan:
                paths[idx] = new_subpaths[idx]
            best_paths = [p[:] for p in paths]
            no_improve = 0
        elif current_makespan == best_makespan:
            # Accept to explore plateau
            for idx in idx_to_replan:
                paths[idx] = new_subpaths[idx]
            no_improve += 1
        else:
            # Revert
            for idx in idx_to_replan:
                modify_reservations(new_subpaths[idx], node_res, edge_res, -1)
                modify_reservations(paths[idx], node_res, edge_res, 1)
            no_improve += 1

    return best_paths
