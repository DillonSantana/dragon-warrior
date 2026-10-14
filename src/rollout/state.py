"""State shared between the listening loop and the menu bar."""

import threading
from dataclasses import dataclass, field


@dataclass
class AssistantState:
    status: str = "starting"  # starting, listening, thinking, speaking, paused, error
    paused: threading.Event = field(default_factory=threading.Event)
    stopped: threading.Event = field(default_factory=threading.Event)
