"""Theme music: plays a song from a set point in the Spotify app when RollOut wakes up.

Spotify is controlled with AppleScript, so it needs only the Spotify desktop app, with no
account keys. RollOut never interrupts music you're already playing, and it pauses the
theme before it talks so the music doesn't drown out the answer.
"""

import re
import subprocess
import threading
import time
from collections.abc import Callable

FADE_STEPS = 8

Runner = Callable[[str], str]


def track_uri(link: str) -> str | None:
    """spotify:track:ID from a share link (open.spotify.com/track/ID?si=...) or a URI."""
    match = re.search(r"(?:track[/:])([A-Za-z0-9]{22})", link)
    return f"spotify:track:{match.group(1)}" if match else None


def parse_start(text: str) -> float:
    """Seconds from "83", "1:23" or "1:23.5"."""
    seconds = 0.0
    for part in text.strip().split(":"):
        seconds = seconds * 60 + float(part)
    return seconds


def osascript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, timeout=10, check=False
    )
    return result.stdout.strip()


class Theme:
    def __init__(self, link: str, start_s: float = 0.0, run: Runner = osascript):
        self.uri = track_uri(link)
        self.start_s = start_s
        self.run = run
        self.playing = False  # only ever pause music RollOut started
        self.volume: str | None = None
        self.lock = threading.Lock()

    def play(self, launch: bool = False) -> bool:
        """Start the theme. Skips it if Spotify is closed (unless launch) or already playing."""
        if not self.uri:
            return False
        with self.lock:
            if not launch and self.run('application "Spotify" is running') != "true":
                return False
            if self.run('tell application "Spotify" to player state as string') == "playing":
                return False
            self.volume = self.run('tell application "Spotify" to sound volume as string')
            self.run(
                f'tell application "Spotify"\n'
                f'  play track "{self.uri}"\n'
                f"  delay 0.3\n"
                f"  set player position to {self.start_s}\n"
                f"end tell"
            )
            self.playing = True
            return True

    def stop(self, fade_s: float = 1.0) -> None:
        """Fade the theme out and pause it, then put Spotify's volume back."""
        with self.lock:
            if not self.playing:
                return
            self.playing = False
            volume = int(self.volume) if self.volume and self.volume.isdigit() else 100
            for step in range(FADE_STEPS - 1, -1, -1):
                level = volume * step // FADE_STEPS
                self.run(f'tell application "Spotify" to set sound volume to {level}')
                time.sleep(fade_s / FADE_STEPS)
            self.run('tell application "Spotify" to pause')
            self.run(f'tell application "Spotify" to set sound volume to {volume}')

    def play_for(self, seconds: float, launch: bool = False) -> None:
        """Play in the background, then fade out after a while (used when RollOut opens)."""

        def run() -> None:
            if self.play(launch=launch):
                time.sleep(seconds)
                self.stop()

        threading.Thread(target=run, daemon=True).start()
