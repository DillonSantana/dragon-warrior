"""State shared between the listening loop and the menu bar."""

import threading
from dataclasses import dataclass, field


@dataclass
class AssistantState:
    # starting, listening, awake (heard "Hey Prime"), thinking, speaking, paused, error
    status: str = "starting"
    caption: str = ""  # what the on-screen emblem shows under it
    paused: threading.Event = field(default_factory=threading.Event)
    stopped: threading.Event = field(default_factory=threading.Event)
