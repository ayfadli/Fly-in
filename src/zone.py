from collections import defaultdict
from enum import Enum
from typing import Dict, Optional


class ZoneType(Enum):
    """The kind of a zone, driving its movement cost and accessibility."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def move_cost(self) -> int:
        """Turns required to move into a zone of this type."""
        return _MOVE_COST[self]


_MOVE_COST: Dict[ZoneType, int] = {
    ZoneType.NORMAL: 1,
    ZoneType.PRIORITY: 1,
    ZoneType.RESTRICTED: 2,
    ZoneType.BLOCKED: -1,
}


class Zone:
    """A node of the routing graph, tracking its own occupancy over time."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: ZoneType = ZoneType.NORMAL,
        color: Optional[str] = None,
        max_drones: int = 1,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.max_drones = max_drones
        self.is_start = is_start
        self.is_end = is_end
        self._reservations: Dict[int, int] = defaultdict(int)

    @property
    def has_unlimited_capacity(self) -> bool:
        """The start and end zones never enforce an occupancy limit."""
        return self.is_start or self.is_end

    def occupancy_at(self, turn: int) -> int:
        """How many drones are reserved to occupy this zone at `turn`."""
        return self._reservations[turn]

    def has_room_at(self, turn: int) -> bool:
        """Whether one more drone could occupy this zone at `turn`."""
        return (
            self.has_unlimited_capacity
            or self.occupancy_at(turn) < self.max_drones
        )

    def reserve(self, turn: int, delta: int = 1) -> None:
        """Add (or, with a negative delta, remove) a drone reservation."""
        self._reservations[turn] += delta

    def __repr__(self) -> str:
        return f"Zone({self.name!r}, type={self.zone_type.value})"
