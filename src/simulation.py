from typing import List, Tuple, Dict
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.text import Text

from src.models import Zone


def run_simulation(
        paths: List[List[Tuple[int, str, str]]], zones: Dict[str, Zone]):
    console = Console()

    if not paths:
        console.print("[red]No paths found to simulate.[/red]")
        return

    makespan = max(p[-1][0] for p in paths)
    nb_drones = len(paths)

    # Pre-process paths to quickly get drone location at each turn
    # paths[d] is a list of (turn, type, name)

    drone_states = defaultdict(dict)
    for d_idx, path in enumerate(paths):
        d_id = d_idx + 1
        for step in path:
            t, loc_type, name = step
            drone_states[d_id][t] = (loc_type, name)

    for t in range(1, makespan + 1):
        moves = []

        # Determine drone movements for this turn
        for d in range(1, nb_drones + 1):
            if t in drone_states[d]:
                loc_type, name = drone_states[d][t]

                # Check if it moved or waited
                # It waited if loc_type is 'zone' and previous state at t-1 was
                # also 'zone' with same name
                if t - 1 in drone_states[d]:
                    prev_type, prev_name = drone_states[d][t - 1]
                    if loc_type == 'zone' and prev_type == 'zone' and name == prev_name:
                        continue  # wait

                # It moved! (either to a connection, or to a zone from connection, or to a zone from zone)
                # The output format is D<ID>-<name>
                moves.append(f"D{d}-{name}")

        # 1. Output the mandatory movement line
        if moves:
            print(" ".join(moves))

        # 2. Output the visual representation
        # To make it nice, we collect where everyone is at the end of turn t
        console.print(f"\n[bold magenta]--- Turn {t} ---[/bold magenta]")

        zone_occupancy = defaultdict(list)
        for d in range(1, nb_drones + 1):
            # Find the latest state <= t
            curr_t = t
            while curr_t not in drone_states[d] and curr_t >= 0:
                curr_t -= 1
            if curr_t >= 0:
                loc_type, name = drone_states[d][curr_t]
                if loc_type == 'zone':
                    zone_occupancy[name].append(f"D{d}")
                elif loc_type == 'conn':
                    zone_occupancy[f"Connection {name}"].append(f"D{d}")

        table = Table(
            show_header=True,
            header_style="bold cyan",
            title="Zone States")
        table.add_column("Location")
        table.add_column("Type")
        table.add_column("Drones")

        # Sort locations: start -> other zones -> connections -> end
        sorted_locations = []
        for loc in zone_occupancy.keys():
            if loc.startswith("Connection"):
                sorted_locations.append((3, loc))
            else:
                z = zones[loc]
                if z.is_start:
                    sorted_locations.append((1, loc))
                elif z.is_end:
                    sorted_locations.append((4, loc))
                else:
                    sorted_locations.append((2, loc))

        sorted_locations.sort()

        for _, loc in sorted_locations:
            drones_str = ", ".join(zone_occupancy[loc])
            if loc.startswith("Connection"):
                table.add_row(loc, "Connection", drones_str)
            else:
                z = zones[loc]
                color = z.color if z.color else "white"
                loc_text = Text(loc, style=color)
                type_text = Text(z.zone_type, style=color)
                table.add_row(loc_text, type_text, drones_str)

        console.print(table)
        console.print("")

    console.print(
        f"[bold green]✅ Simulation complete in {makespan} turns![/bold green]")
