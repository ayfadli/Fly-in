from collections import defaultdict
from typing import Dict, List, Optional

from rich.console import Console

from src.colors import DIM, RESET, colorize, zone_color
from src.drone import Drone
from src.graph import Graph
from src.pathfinder import Pathfinder


class Simulation:
    """Plans every drone's route and replays it turn by turn.

    The mandatory step-by-step movement lines are written to stdout, one
    per turn, exactly as required by the subject. Colored visual feedback
    (per-turn recap and zone occupancy) is written to stderr so it never
    pollutes the parseable output.
    """

    def __init__(self, graph: Graph, console: Optional[Console] = None) -> None:
        self.graph = graph
        self.drones: List[Drone] = []
        self.console = console or Console(stderr=True)

    def setup(self) -> None:
        """Plan a conflict-free timeline for every drone."""
        pathfinder = Pathfinder(self.graph)
        for drone_id, timeline in enumerate(pathfinder.solve(), start=1):
            drone = Drone(drone_id)
            drone.set_timeline(timeline)
            self.drones.append(drone)

    def run(self) -> int:
        """Step through every turn, printing the mandatory output and
        colored visual feedback. Returns the total number of turns."""
        if not self.drones:
            self.setup()

        total_turns = max((d.arrival_turn for d in self.drones), default=0)

        for turn in range(1, total_turns + 1):
            raw_moves = []
            colored_moves = []
            for drone in self.drones:
                label = self._movement_label(drone, turn)
                if label is None:
                    continue
                raw_moves.append(f"D{drone.id}-{label}")
                colored_moves.append(
                    f"D{drone.id}-{self._colorize_label(label)}"
                )

            print(" ".join(raw_moves))
            self._print_visual_feedback(turn, colored_moves)

        self.console.print(
            f"[bold green]All {len(self.drones)} drones delivered "
            f"in {total_turns} turns.[/bold green]"
        )
        return total_turns

    def _print_visual_feedback(
        self, turn: int, colored_moves: List[str]
    ) -> None:
        moves_text = " ".join(colored_moves) if colored_moves else "(wait)"
        occupancy = self._occupied_zones_text(turn)
        self.console.print(
            f"[dim]Turn[/dim] [bold]{turn:>3}[/bold]  {moves_text}"
            f"  [dim]| zones:[/dim] {occupancy}",
            markup=True,
            highlight=False,
        )

    def _occupied_zones_text(self, turn: int) -> str:
        buckets: Dict[str, List[int]] = defaultdict(list)
        for drone in self.drones:
            if drone.arrival_turn <= turn:
                continue
            event = drone.location_before(turn)
            if event is None or event[1] != "zone":
                continue
            buckets[event[2]].append(drone.id)

        if not buckets:
            return "-"

        parts = []
        for name, ids in buckets.items():
            zone = self.graph.zones.get(name)
            label = colorize(name, zone_color(zone)) if zone else name
            drone_ids = ",".join(f"D{i}" for i in ids)
            parts.append(f"{label}({drone_ids})")
        return " ".join(parts)

    def _colorize_label(self, label: str) -> str:
        zone = self.graph.zones.get(label)
        if zone is not None:
            return colorize(label, zone_color(zone))
        return f"{DIM}{label}{RESET}"

    def _movement_label(self, drone: Drone, turn: int) -> Optional[str]:
        """The zone/connection this drone moved to at `turn`, or None if
        it merely waited in place that turn."""
        zone_event: Optional[str] = None
        conn_event: Optional[str] = None
        for event_turn, kind, name in drone.timeline:
            if event_turn != turn:
                continue
            if kind == "zone":
                zone_event = name
            else:
                conn_event = name

        if zone_event is not None:
            if zone_event == self._zone_before(drone, turn):
                return None
            return zone_event
        return conn_event

    @staticmethod
    def _zone_before(drone: Drone, turn: int) -> Optional[str]:
        latest: Optional[str] = None
        for event_turn, kind, name in drone.timeline:
            if kind == "zone" and event_turn < turn:
                latest = name
        return latest
