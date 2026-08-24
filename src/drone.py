from typing import List, Optional, Tuple

# An event is (turn, kind, name): kind is "zone" or "conn", name is the
# zone name or connection name reached/entered by that turn.
Event = Tuple[int, str, str]


class Drone:
    """A single drone, identified by id and following a planned timeline."""

    def __init__(self, drone_id: int) -> None:
        self.id = drone_id
        self.timeline: List[Event] = []

    def set_timeline(self, timeline: List[Event]) -> None:
        """Assign the sequence of (turn, kind, name) events this drone flies."""
        self.timeline = timeline

    @property
    def arrival_turn(self) -> int:
        """The turn at which this drone reaches the end zone."""
        return self.timeline[-1][0] if self.timeline else 0

    def event_at(self, turn: int) -> Optional[Event]:
        """The event scheduled for exactly `turn`, if any."""
        for event in self.timeline:
            if event[0] == turn:
                return event
        return None

    def location_before(self, turn: int) -> Optional[Event]:
        """The most recent event at or before `turn` (where the drone is)."""
        best: Optional[Event] = None
        for event in self.timeline:
            if event[0] > turn:
                break
            best = event
        return best

    def __repr__(self) -> str:
        return f"Drone(D{self.id})"
