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
LAUNCH_WAIT_S = 15
SEEK_WAIT_S = 4
NOT_ALLOWED = "-1743"  # macOS refused to let RollOut control Spotify

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


def _seconds(text: str) -> float:
    try:
        return float(text.replace(",", "."))  # some regions write 48,5
    except ValueError:
        return 0.0


def osascript(script: str) -> str:
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=10, check=False
        )
    except subprocess.TimeoutExpired:
        print("(Theme: Spotify didn't respond in time)", flush=True)
        return ""
    if result.returncode != 0:
        error = result.stderr.strip()
        hint = ""
        if NOT_ALLOWED in error:
            hint = (
                " Allow it in System Settings > Privacy & Security > Automation: turn on Spotify"
                " under Terminal (or under uv / python if RollOut runs at login)."
            )
        print(f"(Theme: Spotify said: {error}.{hint})", flush=True)
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
            print("(Theme: ROLLOUT_THEME_TRACK isn't a Spotify song link)", flush=True)
            return False
        with self.lock:
            if self.run('application "Spotify" is running') != "true":
                if not launch:
                    return False
                if not self._launch():
                    print("(Theme: couldn't open Spotify)", flush=True)
                    return False
            if self.run('tell application "Spotify" to player state as string') == "playing":
                print("(Theme: skipped because Spotify is already playing)", flush=True)
                return False
            self.volume = self.run('tell application "Spotify" to sound volume as string')
            self.run(f'tell application "Spotify" to play track "{self.uri}"')
            self._seek()
            self.playing = True
            print(f"(Theme: playing from {self.start_s:g} seconds)", flush=True)
            return True

    def _seek(self) -> None:
        """Jump to the start point once Spotify has loaded the song; it ignores earlier jumps."""
        if self.start_s <= 0:
            return
        deadline = time.monotonic() + SEEK_WAIT_S
        while time.monotonic() < deadline:
            if self.run('tell application "Spotify" to id of current track') == self.uri:
                self.run(f'tell application "Spotify" to set player position to {self.start_s}')
                if _seconds(self.run('tell application "Spotify" to player position')) >= (
                    self.start_s - 1
                ):
                    return
            time.sleep(0.25)
        print("(Theme: Spotify didn't jump to the start point in time)", flush=True)

    def _launch(self) -> bool:
        """Open Spotify in the background and wait until it can take commands."""
        self.run('tell application "Spotify" to launch')
        deadline = time.monotonic() + LAUNCH_WAIT_S
        while time.monotonic() < deadline:
            if self.run('tell application "Spotify" to player state as string'):
                return True
            time.sleep(0.5)
        return False

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
