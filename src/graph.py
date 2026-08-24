from collections import defaultdict
from typing import Dict, Iterator, List, Optional

from src.connection import Connection
from src.zone import Zone


class Graph:
    """The full network of zones and connections a drone can travel."""

    def __init__(self) -> None:
        self.zones: Dict[str, Zone] = {}
        self.connections: List[Connection] = []
        self.nb_drones: int = 0
        self.start: Optional[Zone] = None
        self.end: Optional[Zone] = None
        self._adjacency: Dict[str, Dict[str, Connection]] = defaultdict(dict)
        self._by_name: Dict[str, Connection] = {}

    def add_zone(self, zone: Zone) -> None:
        """Register a zone, remembering it as start/end when applicable."""
        self.zones[zone.name] = zone
        if zone.is_start:
            self.start = zone
        if zone.is_end:
            self.end = zone

    def add_connection(self, connection: Connection) -> None:
        """Register a bidirectional connection between two known zones."""
        self.connections.append(connection)
        self._adjacency[connection.zone_a][connection.zone_b] = connection
        self._adjacency[connection.zone_b][connection.zone_a] = connection
        self._by_name[connection.name] = connection

    def neighbors(self, zone_name: str) -> Iterator[Zone]:
        """Iterate over the zones directly reachable from `zone_name`."""
        for neighbor_name in self._adjacency[zone_name]:
            yield self.zones[neighbor_name]

    def connection_between(
        self, zone_a: str, zone_b: str
    ) -> Optional[Connection]:
        """The connection linking two zone names, if one exists."""
        return self._adjacency.get(zone_a, {}).get(zone_b)

    def connection_named(self, name: str) -> Connection:
        """The connection registered under `name`."""
        return self._by_name[name]
