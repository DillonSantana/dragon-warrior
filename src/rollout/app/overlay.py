"""On-screen emblem that appears when RollOut hears "Hey Prime", like Siri.

This module holds the parts that don't need macOS: when the emblem shows, how it glows,
where it sits and its shape. `overlay_mac.py` draws it with AppKit.
"""

import math

# Statuses that bring the emblem on screen
VISIBLE = frozenset({"awake", "thinking", "speaking"})
FADE_S = 0.25
CAPTION_LIMIT = 140
SIZE = (360, 300)  # width, height in points
MARGIN = 80

# An original "Prime" crest, drawn in a unit square with y pointing up. Each half runs from
# the top of the center line down the right side to the bottom of the center line.
SHIELD_HALF = [
    (0.50, 0.98),
    (0.80, 0.90),
    (0.95, 0.70),
    (0.90, 0.40),
    (0.72, 0.14),
    (0.50, 0.02),
]
CREST_HALF = [(0.50, 0.92), (0.56, 0.72), (0.50, 0.62)]
FACEPLATE_HALF = [(0.50, 0.42), (0.57, 0.39), (0.62, 0.30), (0.56, 0.18), (0.50, 0.14)]
RIGHT_EYE = [(0.57, 0.58), (0.85, 0.67), (0.81, 0.53), (0.59, 0.50)]

SHIELD_COLOR = (0.82, 0.09, 0.12)
DETAIL_COLOR = (0.07, 0.10, 0.22)
GLOW_COLOR = (0.30, 0.65, 1.00)


def mirror(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return [(1.0 - x, y) for x, y in points]


def symmetric(half: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Close a right half into a full outline by mirroring it across the center line."""
    return half + mirror(half[-2:0:-1])


def emblem_shapes() -> list[tuple[tuple[float, float, float], list[tuple[float, float]]]]:
    """(color, polygon) pairs, painted in order."""
    return [
        (SHIELD_COLOR, symmetric(SHIELD_HALF)),
        (DETAIL_COLOR, symmetric(CREST_HALF)),
        (DETAIL_COLOR, symmetric(FACEPLATE_HALF)),
        (DETAIL_COLOR, RIGHT_EYE),
        (DETAIL_COLOR, mirror(RIGHT_EYE)),
    ]


def target_alpha(status: str, paused: bool) -> float:
    return 1.0 if status in VISIBLE and not paused else 0.0


def step_alpha(current: float, target: float, dt: float, fade_s: float = FADE_S) -> float:
    """Move the window's opacity toward its target, so it fades in and out."""
    step = dt / fade_s
    if current < target:
        return min(target, current + step)
    return max(target, current - step)


def glow(status: str, t: float) -> float:
    """Glow strength from 0 to 1: a slow breath while listening, a quick pulse while talking."""
    if status == "speaking":
        return 0.55 + 0.45 * abs(math.sin(t * 7.0))
    if status == "thinking":
        return 0.7
    return 0.6 + 0.4 * (0.5 + 0.5 * math.sin(t * 2.5))


def spinner_angle(t: float) -> float:
    """Where the ring's arc points while thinking, in degrees."""
    return (-t * 300.0) % 360.0


def caption_for(text: str, limit: int = CAPTION_LIMIT) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def window_origin(
    screen: tuple[float, float, float, float], position: str, size: tuple[int, int] = SIZE
) -> tuple[float, float]:
    """Bottom-left corner for the window inside the screen's visible frame (x, y, w, h)."""
    x, y, w, h = screen
    width, height = size
    if position == "center":
        return x + (w - width) / 2, y + (h - height) / 2
    if position == "top-right":
        return x + w - width - 20, y + h - height - 20
    return x + (w - width) / 2, y + MARGIN  # bottom, above the Dock
