import sys
import argparse
from rich.console import Console

from src.parser import MapParser
from src.solver import solve_routing
from src.simulation import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fly-in: Autonomous Drone Routing Simulation"
    )

    parser.add_argument(
        "map_file",
        type=str,
        help="Path to the map file (e.g., maps/easy_2.txt)",
    )

    args = parser.parse_args()
    console = Console(stderr=True)

    try:
        # 1. Parse the map
        map_parser = MapParser(args.map_file)
        map_parser.parse()
        console.print(
            f"[green]Successfully loaded {map_parser.nb_drones} drones from {args.map_file}.[/green]")

        # 2. Find optimal routes using Space-Time A* + LNS
        console.print("[yellow]Computing optimal flight paths...[/yellow]")
        paths = solve_routing(
            zones=map_parser.zones,
            graph=map_parser.graph,
            orig_conns=map_parser.orig_conns,
            nb_drones=map_parser.nb_drones,
            start=map_parser.start_hub_name,
            end=map_parser.end_hub_name
        )

        # 3. Run the simulation
        run_simulation(paths, map_parser.zones)

    except ValueError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
