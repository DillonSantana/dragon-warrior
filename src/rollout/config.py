"""Settings for RollOut, read from environment variables with sensible defaults."""

import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_data_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "rollout"


@dataclass(frozen=True)
class Config:
    # "wake" listens hands-free for a wake phrase; "push" is press Enter to talk
    listen_mode: str = "wake"
    # Whisper often hears "Hey Prime" as one of these
    wake_phrases: tuple[str, ...] = ("hey prime", "hi prime", "hay prime", "a prime", "hey primes")
    # Small, fast model that checks every utterance for the wake phrase
    wake_model: str = "mlx-community/whisper-base.en-mlx"
    ollama_model: str = "qwen3:8b"
    ollama_url: str = "http://localhost:11434"
    whisper_model: str = "mlx-community/whisper-large-v3-turbo"
    # macOS `say` voice; None uses the system default. List voices with `say -v '?'`.
    tts_voice: str | None = None
    tts_rate: int = 185
    # plain, prime (deeper with an echo) or custom (cloned from voice_clip)
    tts_style: str = "prime"
    # Custom voice: a 5 to 10 second mono 24 kHz WAV you have the right to use, and its transcript
    voice_clip: Path | None = None
    voice_clip_text: str | None = None
    claude_enabled: bool = False
    data_dir: Path = field(default_factory=_default_data_dir)

    @classmethod
    def from_env(cls) -> "Config":
        defaults = cls()
        return cls(
            listen_mode=os.environ.get("ROLLOUT_LISTEN_MODE", defaults.listen_mode),
            wake_phrases=tuple(
                p.strip() for p in os.environ["ROLLOUT_WAKE_PHRASES"].split(",") if p.strip()
            )
            if os.environ.get("ROLLOUT_WAKE_PHRASES")
            else defaults.wake_phrases,
            wake_model=os.environ.get("ROLLOUT_WAKE_MODEL", defaults.wake_model),
            ollama_model=os.environ.get("ROLLOUT_OLLAMA_MODEL", defaults.ollama_model),
            ollama_url=os.environ.get("ROLLOUT_OLLAMA_URL", defaults.ollama_url),
            whisper_model=os.environ.get("ROLLOUT_WHISPER_MODEL", defaults.whisper_model),
            tts_voice=os.environ.get("ROLLOUT_TTS_VOICE") or defaults.tts_voice,
            tts_rate=int(os.environ.get("ROLLOUT_TTS_RATE", defaults.tts_rate)),
            tts_style=os.environ.get("ROLLOUT_TTS_STYLE", defaults.tts_style),
            voice_clip=Path(clip) if (clip := os.environ.get("ROLLOUT_VOICE_CLIP")) else None,
            voice_clip_text=os.environ.get("ROLLOUT_VOICE_CLIP_TEXT") or None,
            claude_enabled=os.environ.get("ROLLOUT_CLAUDE_ENABLED", "0") == "1",
            data_dir=Path(os.environ.get("ROLLOUT_DATA_DIR", defaults.data_dir)),
        )
