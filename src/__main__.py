"""Entry point: ``python3 -m src <map_file>`` — parse, plan, simulate."""

import sys

from src.graph import MapParser, ParseError
from src.pathfinder import Pathfinder
from src.simulation import Simulation


def main() -> None:
    """Route the drones described by the map file given on the command line."""
    if len(sys.argv) != 2:
        sys.exit("usage: python3 -m src <map_file>")
    try:
        graph = MapParser(sys.argv[1]).parse()
        plan = Pathfinder(graph).plan()
        Simulation(graph, plan).run()
    except (ParseError, ValueError, RuntimeError) as err:
        sys.exit(f"error: {err}")


if __name__ == "__main__":
    main()
