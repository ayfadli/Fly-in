"""Play the planned routes out turn by turn and print the movement lines."""

import sys
from collections import defaultdict
from collections.abc import Iterator

from graph import Graph, ZoneType

Route = list[str]
Move = tuple[int, str]

_ANSI = {"red": 31, "crimson": 31, "maroon": 31, "darkred": 31, "green": 32,
         "lime": 32, "yellow": 33, "orange": 33, "gold": 33, "brown": 33,
         "blue": 34, "magenta": 35, "purple": 35, "violet": 35, "cyan": 36,
         "gray": 90, "grey": 90, "black": 90, "rainbow": 95}


def paint(text: str, color: str | None) -> str:
    """Wrap `text` in an ANSI colour, or return it unchanged."""
    code = _ANSI.get((color or "").lower())
    return f"\033[{code}m{text}\033[0m" if code is not None else text


class Drone:
    """A drone following its route one zone per turn."""

    def __init__(self, number: int, route: Route) -> None:
        self.id = number
        self.route = route
        self.step = 0
        self.flying = False

    @property
    def at(self) -> str:
        """The zone the drone currently occupies."""
        return self.route[self.step]

    @property
    def done(self) -> bool:
        """Whether the drone has reached the end of its route."""
        return self.step == len(self.route) - 1


class Simulation:
    """Turn loop that moves the drones while respecting every capacity."""

    def __init__(self, graph: Graph, plan: list[Route]) -> None:
        self.graph = graph
        self.drones = [Drone(i, route) for i, route in enumerate(plan, 1)]

    def run(self, show: bool = True) -> int:
        """Play every drone to the end, printing turns; return the count."""
        turn = 0
        for turn, moves in self._play():
            print(" ".join(f"D{i}-{dest}" for i, dest in moves))
            if show:
                self._recap(turn, moves)
        if show:
            print(paint(f"delivered {len(self.drones)} drones in {turn} turns",
                        "green"), file=sys.stderr)
        return turn

    def arrival_of_last(self) -> int:
        """Turn the most recently added drone lands (used when planning)."""
        target = self.drones[-1]
        last = 0
        for last, _ in self._play():
            if target.done:
                break
        return last

    def _play(self) -> Iterator[tuple[int, list[Move]]]:
        """Yield `(turn, moves)` for each turn until all drones land."""
        turn = 0
        while not all(drone.done for drone in self.drones):
            turn += 1
            moves = self._step(turn)
            if not moves:
                raise RuntimeError(
                    f"deadlock at turn {turn}: no drone can move")
            yield turn, moves

    def _step(self, turn: int) -> list[Move]:
        """Advance every drone that can move; return (id, dest) pairs."""
        zone_count: defaultdict[str, int] = defaultdict(int)
        for drone in self.drones:
            if not drone.done:
                target = (drone.route[drone.step + 1]
                          if drone.flying else drone.at)
                zone_count[target] += 1
        link_count: defaultdict[str, int] = defaultdict(int)
        moves: dict[int, str] = {}

        for drone in self.drones:            # drones mid-crossing land now
            if drone.flying:
                drone.step += 1
                drone.flying = False
                link = self.graph.link(drone.route[drone.step - 1], drone.at)
                link_count[link.name] += 1
                moves[drone.id] = drone.at

        moving = True
        while moving:                        # step the rest forward, repeat
            moving = False
            ordered = sorted(
                self.drones, key=lambda d: len(d.route) - d.step)
            for drone in ordered:
                if drone.done or drone.id in moves or drone.flying:
                    continue
                nxt = drone.route[drone.step + 1]
                zone = self.graph.zones[nxt]
                link = self.graph.link(drone.at, nxt)
                if (zone_count[nxt] >= zone.capacity
                        or link_count[link.name] >= link.capacity):
                    continue
                zone_count[drone.at] -= 1
                zone_count[nxt] += 1
                link_count[link.name] += 1
                moving = True
                if zone.kind is ZoneType.RESTRICTED:
                    drone.flying = True      # lands next turn (2-turn cross)
                    moves[drone.id] = link.name
                else:
                    drone.step += 1
                    moves[drone.id] = drone.at
        return sorted(moves.items())

    def _recap(self, turn: int, moves: list[Move]) -> None:
        """Print a coloured one-line summary of the turn to stderr."""
        painted = " ".join(
            f"D{i}-{paint(dest, self._color(dest))}" for i, dest in moves)
        print(f"turn {turn:>3}  {painted or '(waiting)'}", file=sys.stderr)

    def _color(self, name: str) -> str | None:
        """The declared colour of `name` if it is a zone, else None."""
        zone = self.graph.zones.get(name)
        return zone.color if zone else None
