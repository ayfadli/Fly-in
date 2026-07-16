from typing import Dict, List
from models import Zone, Connection
import re
import sys
from rich.console import Console


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

        self.has_parsed_drones: bool = False
        self.has_parsed_zones: bool = False


    def parse(self) -> None:
        """The main method that opens the file and routes each line."""
        console = Console(stderr=True)

        try:
            with open(self.filepath, 'r') as map_file:
                for n, line in enumerate(map_file, start=1):
                    line = line.split('#')[0].strip()
                    if not line:
                        continue

                    if not self.has_parsed_drones:
                        if not line.startswith("nb_drones:"):
                            raise ValueError (f"The first valid line must define nb_drones.")
                        self._parse_drones(line, n)
                        self.has_parsed_drones = True
                        continue

                    if line.startswith(("start_hub", "hub", "end_hub")):
                        self._parse_zone(line, n)
                        self.has_parsed_zones = True
                        continue

                    if not self.has_parsed_zones:
                        raise ValueError (f"Connections declared before any zones.")
                    elif line.startswith("connection:"):
                        self._parse_connection(line, n)
                    else:
                        raise ValueError(f"Unknown syntax: '{line.strip('\n')}'")

        except ValueError as e:
            console.print(
                f"[cyan]{self.filepath}[/]:[yellow]{n}[/]: [bold red]error: {e}[/]"
            )
            sys.exit(1)
        except FileNotFoundError as e:
            pass
        except PermissionError:
            pass
        except IsADirectoryError:
            pass

        if not self.has_start or not self.has_end:
            console.print(
                f"[bold red]error: Missing a start or end zone ![/]"
            )
            sys.exit(1)

    def _parse_drones(self, line: str, line_number: int):
        """Extracts the number of drones."""
        nb_drones = line.strip().replace(
            ' ', '').split('nb_drones:')[1].strip()
        if nb_drones is None or not nb_drones:
            raise ValueError(f"Required metadata nb_drones is missing.")
        try:
            self.nb_drones = int(nb_drones)
        except ValueError as e:
            raise ValueError(
                f"Invalid number of drones: '{nb_drones}'. Expected an integer.")

        if self.nb_drones < 0:
            raise ValueError(
                f"Invalid value for 'nb_drones': '{nb_drones}'. Expected a positive integer.")

    def _parse_zone(self, line: str, line_number: int):
        """Extracts the zone and its optional metadata."""
        is_start = False
        is_end = False
        zone_type = "normal"
        color = None
        max_drones = 1

        prefix = next((p for p in ("hub: ", "start_hub: ",
                      "end_hub: ") if line.strip().startswith(p)), None)
        if prefix is None:
            raise ValueError("Incomplete zone data. Expected: 'hub_type: <zone_name> x y ...'.")
            # raise ValueError(
            #     f"Malformed hub declaration. Expected ':' after zone type. e.g: 'start_hub:'.")

        match = re.search(r"^[^:]+:\s*(\S+)", line.strip())

        cor = re.search(r"(-?\d+)\s+(-?\d+)", line)
        if not cor:
            raise ValueError(f"Invalid coordinates.")
        x, y = cor.groups()

        metadata = dict()
        metadata_match = re.findall(r'\[(.*?)\]', line.strip())

        if len(metadata_match) > 1:
            raise ValueError(f"Invalid Metadata.")

        elif metadata_match != [''] and len(metadata_match) > 0:
            metadata = dict(re.findall(
                r'(\w+)\s*=\s*([^\s\]]+)', metadata_match[0]))

            for key, value in metadata.items():
                if '=' in value:
                    raise ValueError(
                        f"Invalid metadata option: {metadata_match}. Expected a single '=' separator.")
                if key not in ("zone", "color", "max_drones"):
                    raise ValueError(f"Invalid metadata option: {key}")

            if not metadata:
                raise ValueError(f"Expected a value for metadata option {metadata_match}.")

        color = metadata.get('color', None)
        zone_type = metadata.get('zone', "normal")
        max_drones = metadata.get('max_drones', 1)

        if match:
            hub_name = match.group(1)
            if '-' in hub_name:
                raise ValueError(
                    f"The zone name connot contains '-': '{hub_name}'.")
            if hub_name in self.zones:
                raise ValueError(
                    f"Duplicate zone name '{hub_name}' found."
                )
            # print(hub_name)
        else:
            raise ValueError(f"A hub name is required in line {line_number}.")

        if prefix.startswith("start_hub:"):
            is_start = True
            self.has_start = True
        elif prefix.startswith("end_hub:"):
            is_end = True
            self.has_end = True

        self.zones[hub_name] = Zone(hub_name, x, y, is_start, is_end, zone_type, color, max_drones)
        print(self.zones[hub_name])
        # print(line)

    def _parse_connection(self, line: str, line_number: int):
        """Extracts a connection and its optional metadata."""
        
        # print(line)
        pass
