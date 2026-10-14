"""Text to speech: plain macOS `say`, a deeper "prime" style, or a custom cloned voice.

- plain: the built-in `say` voice as is.
- prime: `say` rendered to a file, pitched down and given a short echo, then played with `afplay`.
- custom: F5-TTS on Apple Silicon (f5-tts-mlx), matching a reference clip you have the right
  to use. Clips live in the git-ignored `voices/` folder and never go in the repo.
"""

import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

_MARKDOWN = re.compile(r"[*_`#>]+")

PRIME_PITCH = 0.82  # playback speed factor; below 1 lowers pitch
PRIME_ECHOES = ((0.045, 0.35), (0.090, 0.18))  # (delay seconds, gain)
SAY_SAMPLE_RATE = 22_050


def clean_for_speech(text: str) -> str:
    """Drop markdown symbols and collapse whitespace so speech reads naturally."""
    return " ".join(_MARKDOWN.sub("", text).split())


def speak(
    text: str,
    voice: str | None = None,
    rate: int = 185,
    style: str = "plain",
    clip: Path | None = None,
    clip_text: str | None = None,
) -> None:
    text = clean_for_speech(text)
    if not text:
        return
    if style == "custom" and clip and clip_text:
        _speak_custom(text, clip, clip_text)
    elif style in ("prime", "custom"):  # custom without a clip falls back to prime
        _speak_prime(text, voice, rate)
    else:
        subprocess.run([*_say_cmd(voice, rate), text], check=False)


def _say_cmd(voice: str | None, rate: int) -> list[str]:
    cmd = ["say", "-r", str(rate)]
    if voice:
        cmd += ["-v", voice]
    return cmd


def prime_effect(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Lower the pitch by resampling, add a short echo, and normalize."""
    n_out = int(len(audio) / PRIME_PITCH)
    lowered = np.interp(np.linspace(0, len(audio) - 1, n_out), np.arange(len(audio)), audio)
    out = np.copy(lowered)
    for delay, gain in PRIME_ECHOES:
        shift = int(delay * sample_rate)
        out[shift:] += gain * lowered[: len(lowered) - shift]
    peak = np.max(np.abs(out)) if out.size else 0
    return (out / peak * 0.9 if peak else out).astype(np.float32)


def _speak_prime(text: str, voice: str | None, rate: int) -> None:
    # Speak faster up front so the pitch-down doesn't make speech drag
    say_rate = int(rate / PRIME_PITCH)
    with tempfile.TemporaryDirectory() as tmp:
        raw, processed = Path(tmp) / "raw.wav", Path(tmp) / "prime.wav"
        cmd = [*_say_cmd(voice, say_rate), "-o", str(raw), f"--data-format=LEI16@{SAY_SAMPLE_RATE}"]
        if subprocess.run([*cmd, text], check=False).returncode != 0 or not raw.exists():
            return
        audio, sample_rate = read_wav(raw)
        write_wav(processed, prime_effect(audio, sample_rate), sample_rate)
        subprocess.run(["afplay", str(processed)], check=False)


def _speak_custom(text: str, clip: Path, clip_text: str) -> None:
    from f5_tts_mlx.generate import generate  # macOS only; plays the audio when it's ready

    generate(generation_text=text, ref_audio_path=str(clip), ref_audio_text=clip_text)


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as f:
        frames = f.readframes(f.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768
        if f.getnchannels() > 1:
            audio = audio.reshape(-1, f.getnchannels()).mean(axis=1)
        return audio, f.getframerate()


def write_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
