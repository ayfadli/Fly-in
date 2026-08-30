from typing import Dict, FrozenSet, Set
import re
import sys
from rich.console import Console

from src.connection import Connection
from src.graph import Graph
from src.zone import Zone, ZoneType


class MapParser:
    def __init__(self, filepath: str):
        """Initializes the parser with the map file path."""
        self.filepath: str = filepath

        self.nb_drones: int = 0
        self.zones: Dict[str, Zone] = {}
        self.connections: Dict[str, Connection] = {}

        self.start_hub_name: str = ""
        self.end_hub_name: str = ""

        self.has_start: bool = False
        self.has_end: bool = False
        # self.has_nb_drones: bool = False

        self.has_parsed_drones: bool = False
        self.has_parsed_zones: bool = False

        self._connected_pairs: Set[FrozenSet[str]] = set()

    def parse(self) -> None:#nb_drones: 4
        """The main method that opens the file and routes each line."""
        console = Console(stderr=True)

        try:
            with open(self.filepath, "r") as map_file:
                for n, line in enumerate(map_file, start=1):
                    line = line.split("#")[0].strip()
                    if not line:
                        continue

                    if not self.has_parsed_drones:
                        if not line.startswith("nb_drones:"):
                            raise ValueError(
                                "The first valid line must define nb_drones."
                            )
                        self._parse_drones(line, n)
                        self.has_parsed_drones = True
                        continue



                    if self.has_start and line.startswith("start_hub:"):
                        raise ValueError(
                            "The start_hub cannot be declared twice."
                        )

                    if self.has_end and line.startswith("end_hub:"):
                        raise ValueError(
                            "The end_hub cannot be declared twice."
                        )


                    if line.startswith(("start_hub", "hub", "end_hub")):
                        self._parse_zone(line, n)
                        self.has_parsed_zones = True
                        continue

                    if self.has_parsed_drones and not self.has_parsed_zones:
                        raise ValueError("Invalid zones declaration or duplicate nb_drones definition.")

                    if not self.has_parsed_zones:
                        raise ValueError(
                            "Connections declared before any zones."
                        )

                    elif line.startswith("connection:"):
                        self._parse_connection(line, n)
                    else:
                        raise ValueError(f"Unknown syntax: '{line.strip('')}'")

        except ValueError as e:
            console.print(
                f"[cyan]{self.filepath}[/]:[yellow]{n}[/]: "
                f"[bold red]error: {e}[/]"
            )
            sys.exit(1)
        except FileNotFoundError:
            console.print(
                f"[bold red]error: File not found: '{self.filepath}'[/]"
            )
            sys.exit(1)
        except PermissionError:
            console.print(
                f"[bold red]error: Permission denied: '{self.filepath}'[/]"
            )
            sys.exit(1)
        except IsADirectoryError:
            console.print(
                "[bold red]error: Expected a file but got a directory: "
                f"'{self.filepath}'[/]"
            )
            sys.exit(1)
        except Exception as e:
            console.print(
                f"[bold red]error: An unexpected error occurred: {e}[/]"
            )
            sys.exit(1)

        if not self.has_start or not self.has_end:
            console.print("[bold red]error: Missing a start or end zone ![/]")
            sys.exit(1)

    def build_graph(self) -> Graph:
        """Assemble the parsed zones and connections into an OOP Graph."""
        graph = Graph()
        graph.nb_drones = self.nb_drones
        for zone in self.zones.values():
            graph.add_zone(zone)
        for connection in self.connections.values():
            graph.add_connection(connection)
        return graph

    def _parse_drones(self, line: str, line_number: int) -> None:
        """Extracts the number of drones."""
        nb_drones = (
            line.strip().replace(" ", "").split("nb_drones:")[1].strip()
        )
        if nb_drones is None or not nb_drones:
            raise ValueError("Required metadata nb_drones is missing.")
        try:
            self.nb_drones = int(nb_drones)
        except ValueError:
            raise ValueError(
                f"Invalid number of drones: '{nb_drones}'. "
                "Expected an integer."
            )

        if self.nb_drones <= 0:
            raise ValueError(
                f"Invalid value for 'nb_drones': '{nb_drones}'. "
                "Expected a positive integer."
            )
        #self.has_nb_drones = True

    def _parse_zone(self, line: str, line_number: int) -> None:
        """Extracts the zone and its optional metadata."""
        is_start = False
        is_end = False

        prefix = next(
            (
                p
                for p in ("hub: ", "start_hub: ", "end_hub: ")
                if line.strip().startswith(p)
            ),
            None,
        )
        if prefix is None:
            raise ValueError(
                "Incomplete zone data. Expected: "
                "'hub_type: <zone_name> x: int y: int ...'."
            )

        match = re.search(r"^[^:]+:\s*(.*?)\s+-?\d+\s+-?\d+", line.strip())

        coor = re.search(r"(-?\d+)\s+(-?\d+)", line)
        if not coor:
            raise ValueError("Invalid coordinates.")
        x_str, y_str = coor.groups()
        x, y = int(x_str), int(y_str)

        metadata = {}

        metadata_match = re.search(r"\[([^\]]+)\]\s*$", line.strip())

        if metadata_match:
            metadata_content = metadata_match.group(1)

            metadata = dict(
                re.findall(
                    r"(\w+)\s*=\s*([^\s\]]+)",
                    metadata_content
                )
            )

            for key, value in metadata.items():
                if "=" in value:
                    raise ValueError(
                        f"Invalid metadata option: {metadata_content}. "
                        "Expected a single '=' separator."
                    )

                if key not in ("zone", "color", "max_drones"):
                    raise ValueError(
                        f"Invalid metadata option: {key}"
                    )


            if not metadata:
                raise ValueError(
                    f"Expected a value for metadata option {metadata_match}."
                )

        if prefix.startswith("start_hub:"):
            is_start = True
            self.has_start = True
        elif prefix.startswith("end_hub:"):
            is_end = True
            self.has_end = True

        color = metadata.get("color", None)
        zone_type_str = metadata.get("zone", "normal")
        if zone_type_str not in (
            "normal", "blocked", "restricted", "priority"
        ):
            raise ValueError(
                f"Invalid zone type '{zone_type_str}'. "
                "Expected one of: normal, blocked, restricted, priority."
            )
        zone_type = ZoneType(zone_type_str)

        if not is_start and not is_end:
            try:
                max_drones = int(metadata.get("max_drones", 1))
            except ValueError:
                raise ValueError(
                    f"The max_drones cannot be a string "
                    f"'{metadata.get('max_drones', 1)}'."
                )
            if max_drones < 1:
                raise ValueError("The max_drones must be a positive int > 0.")
        else:
            max_drones = 1

        if match:
            hub_name = match.group(1)
            if "-" in hub_name or " " in hub_name:
                raise ValueError(
                    f"The zone name cannot contain '-' or space: '{hub_name}'."
                )
            if hub_name in self.zones:
                raise ValueError(f"Duplicate zone name '{hub_name}' found.")
        else:
            raise ValueError(f"A hub name is required in line {line_number}.")

        self.zones[hub_name] = Zone(
            name=hub_name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            max_drones=max_drones,
            is_start=is_start,
            is_end=is_end,
        )


        if is_start:
            self.start_hub_name = hub_name
        if is_end:
            self.end_hub_name = hub_name
            start_zone = self.zones[self.start_hub_name]
            end_zone = self.zones[hub_name]
            if start_zone.x == end_zone.x and start_zone.y == end_zone.y:
                raise ValueError(
                    "The graph must have a unique start and a unique end zone."
                )


    def _parse_connection(self, line: str, line_number: int) -> None:
        """Extracts a connection and its optional metadata."""

        match = re.search(r"^[^:]+:\s*(\S+)", line.strip())
        if match is None:
            raise ValueError(f"Invalid syntax for Connection: {line}.")

        parts = match.group(1).split("-")
        if len(parts) > 1 and not parts[1]:
            raise ValueError(
                "Missing zone name in connection. "
                "Expected format: <zone1>-<zone2>"
            )

        zones = [p for p in match.group(1).split("-") if p]
        if len(zones) != 2:
            raise ValueError(
                "A single connection can only ever link exactly two zones."
            )

        for zone in zones:
            if zone not in self.zones:
                raise ValueError(
                    f"This zone: '{zone}' is undeclared "
                    "and cannot be used in a connection."
                )

        zoneA, zoneB = zones
        if zoneA == zoneB:
            raise ValueError(
                f"Invalid connection '{zoneA}-{zoneB}'. "
                "A zone cannot connect to itself."
            )

        metadata = {}

        metadata_match = re.search(r"\[([^\]]+)\]\s*$", line.strip())

        if metadata_match:
            metadata = dict(
                re.findall(
                    r"(\w+)\s*=\s*([^\s\]]+)",
                    metadata_match.group(1)
                )
            )

            if not metadata:
                raise ValueError(
                    f"Invalid Metadata for connection '{zoneA}-{zoneB}'."
                )

            for key, value in metadata.items():
                if "=" in value:
                    raise ValueError(
                        f"Invalid metadata option: {metadata_match}. "
                        "Expected a single '=' separator."
                    )
                if key != "max_link_capacity":
                    raise ValueError(f"Invalid metadata option: {key}")

            if not metadata:
                raise ValueError(
                    f"Expected a value for metadata option {metadata_match}."
                )

        try:
            capacity = int(metadata.get("max_link_capacity", 1))
        except ValueError:
            raise ValueError(
                f"The max_link_capacity cannot be a string "
                f"'{metadata.get('max_link_capacity', 1)}'."
            )

        if capacity < 1:
            raise ValueError(
                "The max_link_capacity must be a positive int > 0."
            )

        pair = frozenset((zoneA, zoneB))
        if pair in self._connected_pairs:
            raise ValueError(
                f"Duplicate connection '{zoneA}-{zoneB}'. "
                "This path already exists."
            )
        self._connected_pairs.add(pair)

        declared_name = match.group(1)
        self.connections[declared_name] = Connection(
            zone_a=zoneA,
            zone_b=zoneB,
            max_link_capacity=capacity,
            name=declared_name,
        )
