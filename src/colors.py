from src.zone import Zone, ZoneType

RESET = "\033[0m"
DIM = "\033[2m"

NAMED_COLORS = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "purple": "\033[35m",
    "violet": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "gray": "\033[90m",
    "grey": "\033[90m",
    "black": "\033[90m",
    "orange": "\033[33m",
    "gold": "\033[33m",
    "brown": "\033[33m",
    "crimson": "\033[31m",
    "maroon": "\033[31m",
    "darkred": "\033[31m",
    "rainbow": "\033[95m",
}

TYPE_COLORS = {
    ZoneType.NORMAL: "\033[37m",
    ZoneType.PRIORITY: "\033[32m",
    ZoneType.RESTRICTED: "\033[31m",
    ZoneType.BLOCKED: "\033[90m",
}


def zone_color(zone: Zone) -> str:
    """ANSI color code for a zone, from its declared color or its type."""
    if zone.color:
        return NAMED_COLORS.get(
            zone.color.lower(), TYPE_COLORS[zone.zone_type])
    return TYPE_COLORS[zone.zone_type]


def colorize(text: str, code: str) -> str:
    """Wrap text in the given ANSI color code, resetting after it."""
    return f"{code}{text}{RESET}"
