"""Text to speech with the built-in macOS `say` command."""

import re
import subprocess

_MARKDOWN = re.compile(r"[*_`#>]+")


def clean_for_speech(text: str) -> str:
    """Drop markdown symbols and collapse whitespace so `say` reads naturally."""
    return " ".join(_MARKDOWN.sub("", text).split())


def speak(text: str, voice: str | None = None, rate: int = 185) -> None:
    text = clean_for_speech(text)
    if not text:
        return
    cmd = ["say", "-r", str(rate)]
    if voice:
        cmd += ["-v", voice]
    subprocess.run([*cmd, text], check=False)
