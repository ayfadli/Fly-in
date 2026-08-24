from collections import defaultdict
from typing import Dict, Optional


class Connection:
    """A bidirectional link between two zones with its own capacity."""

    def __init__(
        self,
        zone_a: str,
        zone_b: str,
        max_link_capacity: int = 1,
        name: Optional[str] = None,
    ) -> None:
        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_link_capacity = max_link_capacity
        self.name = name or f"{zone_a}-{zone_b}"
        self._reservations: Dict[int, int] = defaultdict(int)

    def other(self, zone_name: str) -> str:
        """The zone name on the far side of the connection from `zone_name`."""
        return self.zone_b if zone_name == self.zone_a else self.zone_a

    def links(self, zone_a: str, zone_b: str) -> bool:
        """Whether this connection joins exactly `zone_a` and `zone_b`."""
        return {zone_a, zone_b} == {self.zone_a, self.zone_b}

    def occupancy_at(self, turn: int) -> int:
        """How many drones are reserved to traverse this link at `turn`."""
        return self._reservations[turn]

    def has_room_at(self, turn: int) -> bool:
        """Whether one more drone could traverse this link at `turn`."""
        return self.occupancy_at(turn) < self.max_link_capacity

    def reserve(self, turn: int, delta: int = 1) -> None:
        """Add (or, with a negative delta, remove) a drone reservation."""
        self._reservations[turn] += delta

    def __repr__(self) -> str:
        return f"Connection({self.name!r}, capacity={self.max_link_capacity})"
