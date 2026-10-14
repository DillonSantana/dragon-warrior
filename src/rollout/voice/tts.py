"""Text to speech in one of four styles.

- plain: the built-in `say` voice as is.
- prime: `say` rendered to a file, pitched down and given a short echo, then played with `afplay`.
- custom: F5-TTS on Apple Silicon (f5-tts-mlx), matching a reference clip you have the right
  to use. Clips live in the git-ignored `voices/` folder and never go in the repo.
- elevenlabs: a voice from your ElevenLabs account, such as a licensed character voice. Needs
  internet and uses ElevenLabs credits; falls back to prime when it can't be reached.
"""

import json
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from rollout.config import Config

_MARKDOWN = re.compile(r"[*_`#>]+")

PRIME_PITCH = 0.82  # playback speed factor; below 1 lowers pitch
PRIME_ECHOES = ((0.045, 0.35), (0.090, 0.18))  # (delay seconds, gain)
SAY_SAMPLE_RATE = 22_050


def clean_for_speech(text: str) -> str:
    """Drop markdown symbols and collapse whitespace so speech reads naturally."""
    return " ".join(_MARKDOWN.sub("", text).split())


ELEVENLABS_URL = (
    "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
)


def speak(text: str, config: "Config") -> None:
    text = clean_for_speech(text)
    if not text:
        return
    style, voice, rate = config.tts_style, config.tts_voice, config.tts_rate
    if style == "elevenlabs" and _speak_elevenlabs(text, config):
        return
    if style == "custom" and config.voice_clip and config.voice_clip_text:
        _speak_custom(text, config.voice_clip, config.voice_clip_text)
    elif style in ("prime", "custom", "elevenlabs"):  # fallback when the others can't run
        _speak_prime(text, voice, rate)
    else:
        subprocess.run([*_say_cmd(voice, rate), text], check=False)


def _speak_elevenlabs(text: str, config: "Config") -> bool:
    """Speak through ElevenLabs. Returns False if it isn't set up or can't be reached."""
    if not (config.elevenlabs_api_key and config.elevenlabs_voice_id):
        return False
    request = urllib.request.Request(
        ELEVENLABS_URL.format(voice_id=config.elevenlabs_voice_id),
        data=json.dumps({"text": text, "model_id": config.elevenlabs_model}).encode(),
        headers={"xi-api-key": config.elevenlabs_api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            audio = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"(ElevenLabs unavailable, using the Prime voice: {exc})")
        return False
    with tempfile.TemporaryDirectory() as tmp:
        mp3 = Path(tmp) / "reply.mp3"
        mp3.write_bytes(audio)
        subprocess.run(["afplay", str(mp3)], check=False)
    return True


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
