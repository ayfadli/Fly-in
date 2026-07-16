from dataclasses import dataclass
from typing import Optional

@dataclass
class Zone:
    name: str
    x: int
    y: int
    is_start: bool = False
    is_end: bool = False
    zone_type: str = "normal" # normal, restricted, priority, blocked
    color: Optional[str] = None
    max_drones: int = 1

@dataclass
class Connection:
    zone1: str
    zone2: str
    max_link_capacity: int = 1
