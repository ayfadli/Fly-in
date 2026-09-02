"""The map model (zones, connections, graph) and the parser that builds it."""

from dataclasses import dataclass
from enum import Enum

BIG = 10 ** 9


class ZoneType(Enum):
    """A zone's kind, which sets how many turns it costs to enter."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


@dataclass
class Zone:
    """One place a drone can stand on."""

    name: str
    x: int
    y: int
    kind: ZoneType
    color: str | None
    max_drones: int
    is_start: bool
    is_end: bool

    @property
    def enter_turns(self) -> int:
        """Turns to move in: 2 for a restricted zone, 1 otherwise."""
        return 2 if self.kind is ZoneType.RESTRICTED else 1

    @property
    def weight(self) -> int:
        """Router cost to enter; priority zones are made a little cheaper."""
        return {ZoneType.RESTRICTED: 20, ZoneType.PRIORITY: 9}.get(
            self.kind, 10)

    @property
    def capacity(self) -> int:
        """Drones that fit at once; the start and end zones are unlimited."""
        return BIG if self.is_start or self.is_end else self.max_drones


@dataclass
class Connection:
    """A two-way link between two zones."""

    a: str
    b: str
    capacity: int

    @property
    def name(self) -> str:
        """The link's label, e.g. ``start-waypoint1``."""
        return f"{self.a}-{self.b}"


class Graph:
    """Every zone plus the links between them."""

    def __init__(self) -> None:
        self.nb_drones = 0
        self.start = ""
        self.end = ""
        self.zones: dict[str, Zone] = {}
        self.links: dict[frozenset[str], Connection] = {}
        self.neighbours: dict[str, list[str]] = {}

    def add_zone(self, zone: Zone) -> None:
        """Store a zone and note it if it is the start or the end."""
        self.zones[zone.name] = zone
        self.neighbours[zone.name] = []
        if zone.is_start:
            self.start = zone.name
        if zone.is_end:
            self.end = zone.name

    def add_link(self, link: Connection) -> None:
        """Store a link and list it as a neighbour of both its zones."""
        self.links[frozenset((link.a, link.b))] = link
        self.neighbours[link.a].append(link.b)
        self.neighbours[link.b].append(link.a)

    def link(self, a: str, b: str) -> Connection:
        """The link joining zones `a` and `b`."""
        return self.links[frozenset((a, b))]


class ParseError(Exception):
    """A problem in the map file, reported with its line number."""


class MapParser:
    """Reads a map file into a `Graph`."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.graph = Graph()
        self._drones_done = False

    def parse(self) -> Graph:
        """Return the graph described by the file, or raise `ParseError`."""
        try:
            with open(self.path, encoding="utf-8") as handle:
                lines = handle.readlines()
        except OSError as err:
            raise ParseError(f"cannot read {self.path!r}: {err}")

        for number, raw in enumerate(lines, 1):
            line = raw.split("#")[0].strip()
            if not line:
                continue
            try:
                self._read(line)
            except ParseError as err:
                raise ParseError(f"line {number}: {err}")

        if not self.graph.start or not self.graph.end:
            raise ParseError("map needs one start_hub and one end_hub")
        return self.graph

    def _read(self, line: str) -> None:
        """Send one non-empty line to the matching reader."""
        if not self._drones_done:
            if not line.startswith("nb_drones:"):
                raise ParseError("first line must be 'nb_drones: <count>'")
            self.graph.nb_drones = self._int(
                line.split(":", 1)[1], "nb_drones")
            self._drones_done = True
        elif line.startswith(("start_hub:", "end_hub:", "hub:")):
            self._read_zone(line)
        elif line.startswith("connection:"):
            self._read_connection(line)
        else:
            raise ParseError(f"unexpected line: {line!r}")

    def _read_zone(self, line: str) -> None:
        """Parse a 'start_hub:/end_hub:/hub: <name> <x> <y> [opts]' line."""
        head, rest = line.split(":", 1)
        fields = rest.split("[", 1)[0].split()
        if len(fields) != 3:
            raise ParseError("expected '<name> <x> <y>' then optional '[...]'")
        name, sx, sy = fields
        if "-" in name or name in self.graph.zones:
            raise ParseError(f"bad or duplicate zone name {name!r}")
        try:
            x, y = int(sx), int(sy)
        except ValueError:
            raise ParseError("coordinates must be integers")

        meta = self._meta(line, ("zone", "color", "max_drones"))
        try:
            kind = ZoneType(meta.get("zone", "normal"))
        except ValueError:
            raise ParseError(f"unknown zone type {meta['zone']!r}")
        start, end = head == "start_hub", head == "end_hub"
        if (start and self.graph.start) or (end and self.graph.end):
            raise ParseError(f"{head} is already defined")

        # max_drones is ignored on the start/end zones (they are unlimited),
        # so any value there -- even an invalid one -- is not an error.
        if start or end:
            max_drones = 1
        else:
            max_drones = self._int(meta.get("max_drones", "1"), "max_drones")
        self.graph.add_zone(
            Zone(name, x, y, kind, meta.get("color"), max_drones, start, end))

    def _read_connection(self, line: str) -> None:
        """Parse a 'connection: <zone>-<zone> [opts]' line."""
        pair = line.split(":", 1)[1].split("[", 1)[0].strip().split("-")
        if len(pair) != 2 or not all(pair) or pair[0] == pair[1]:
            raise ParseError("connection must join two distinct zones")
        for name in pair:
            if name not in self.graph.zones:
                raise ParseError(f"unknown zone {name!r} in connection")
        if frozenset(pair) in self.graph.links:
            raise ParseError(f"duplicate connection {pair[0]}-{pair[1]}")

        meta = self._meta(line, ("max_link_capacity",))
        capacity = self._int(
            meta.get("max_link_capacity", "1"), "max_link_capacity")
        self.graph.add_link(Connection(pair[0], pair[1], capacity))

    @staticmethod
    def _meta(line: str, allowed: tuple[str, ...]) -> dict[str, str]:
        """Parse a trailing '[key=value ...]' block into a dict."""
        if "[" not in line:
            return {}
        if not line.endswith("]"):
            raise ParseError(f"metadata must end with ']': {line!r}")
        meta: dict[str, str] = {}
        for token in line[line.index("[") + 1:-1].split():
            key, sep, value = token.partition("=")
            if sep != "=" or not value or key not in allowed:
                raise ParseError(f"bad metadata option {token!r}")
            meta[key] = value
        return meta

    @staticmethod
    def _int(text: str, label: str) -> int:
        """Parse a strictly-positive integer, or raise `ParseError`."""
        text = text.strip()
        if not text.isdigit() or int(text) <= 0:
            raise ParseError(
                f"{label} must be a positive integer, got {text!r}")
        return int(text)
