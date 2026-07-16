import sys
import argparse
from parser import MapParser

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fly-in: Autonomous Drone Routing Simulation"
        )

    parser.add_argument("map_file",
                        type=str,
                        help="Path to the map file (e.g., maps/easy_2.txt)")

    args = parser.parse_args()

    try:
        map_parser = MapParser(args.map_file)
        map_parser.parse()
        print(f"Successfully loaded {map_parser.nb_drones} drones.")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
