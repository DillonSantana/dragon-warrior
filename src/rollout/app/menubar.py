"""Menu bar app: shows RollOut's state and lets you pause or quit it.

The listening loop runs on a background thread; rumps owns the main thread, as macOS
requires for anything that draws UI.
"""

import os
import threading
import traceback
from collections.abc import Callable

from rollout.state import AssistantState

TITLES = {
    "starting": "Prime …",
    "listening": "Prime ●",
    "thinking": "Prime ⋯",
    "speaking": "Prime ♪",
    "paused": "Prime ‖",
    "error": "Prime ⚠",
}


def title_for(state: AssistantState) -> str:
    if state.paused.is_set():
        return TITLES["paused"]
    return TITLES.get(state.status, TITLES["starting"])


def run_menubar(loop: Callable[[AssistantState], None]) -> None:
    import rumps  # macOS only

    state = AssistantState()

    def worker() -> None:
        try:
            loop(state)
        except Exception:
            traceback.print_exc()
            state.status = "error"

    app = rumps.App("RollOut", title=TITLES["starting"], quit_button=None)
    pause_item = rumps.MenuItem("Pause listening")

    def toggle_pause(sender) -> None:
        if state.paused.is_set():
            state.paused.clear()
            sender.title = "Pause listening"
        else:
            state.paused.set()
            sender.title = "Resume listening"

    def quit_app(_) -> None:
        state.stopped.set()
        rumps.quit_application()
        os._exit(0)  # the listening thread may be blocked on the microphone

    pause_item.set_callback(toggle_pause)
    app.menu = [pause_item, None, rumps.MenuItem("Quit RollOut", callback=quit_app)]

    @rumps.timer(0.5)
    def refresh(_) -> None:
        app.title = title_for(state)

    threading.Thread(target=worker, daemon=True).start()
    app.run()
