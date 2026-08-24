import argparse
import sys

from rich.console import Console

from src.parser import MapParser
from src.simulation import Simulation


def main() -> None:
    """Parse CLI arguments and run the drone routing simulation."""
    arg_parser = argparse.ArgumentParser(
        description="Fly-in: Autonomous Drone Routing Simulation"
    )
    arg_parser.add_argument(
        "map_file",
        type=str,
        help="Path to the map file (e.g., maps/easy/01_linear_path.txt)",
    )
    args = arg_parser.parse_args()

    console = Console(stderr=True)

    try:
        map_parser = MapParser(args.map_file)
        map_parser.parse()
        console.print(
            f"[green]Loaded {map_parser.nb_drones} drones "
            f"from {args.map_file}.[/green]"
        )

        graph = map_parser.build_graph()

        console.print("[yellow]Computing conflict-free flight paths...[/]")
        simulation = Simulation(graph, console=console)
        simulation.run()

    except ValueError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
