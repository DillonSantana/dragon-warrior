"""Settings for RollOut, read from environment variables with sensible defaults."""

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines from a git-ignored .env file without overriding real env vars."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


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
    # plain, prime (deeper with an echo), custom (cloned from voice_clip) or elevenlabs
    tts_style: str = "prime"
    # Custom voice: a 5 to 10 second mono 24 kHz WAV you have the right to use, and its transcript
    voice_clip: Path | None = None
    voice_clip_text: str | None = None
    # ElevenLabs voice, e.g. a licensed character voice on your account. Keep the key in .env.
    elevenlabs_api_key: str | None = field(default=None, repr=False)
    elevenlabs_voice_id: str | None = None
    elevenlabs_model: str = "eleven_flash_v2_5"
    # Emblem that appears on screen when you say "Hey Prime" (menu bar app only).
    # overlay_image swaps in your own picture, ideally a square PNG with a transparent background.
    overlay: bool = True
    overlay_position: str = "bottom"  # bottom, center or top-right
    overlay_image: Path | None = None
    claude_enabled: bool = False
    data_dir: Path = field(default_factory=_default_data_dir)

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv(Path.cwd() / ".env")
        load_dotenv(PROJECT_ROOT / ".env")
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
            elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY") or None,
            elevenlabs_voice_id=os.environ.get("ROLLOUT_ELEVENLABS_VOICE_ID") or None,
            elevenlabs_model=os.environ.get("ROLLOUT_ELEVENLABS_MODEL", defaults.elevenlabs_model),
            overlay=os.environ.get("ROLLOUT_OVERLAY", "1") != "0",
            overlay_position=os.environ.get("ROLLOUT_OVERLAY_POSITION", defaults.overlay_position),
            overlay_image=Path(img).expanduser()
            if (img := os.environ.get("ROLLOUT_OVERLAY_IMAGE"))
            else None,
            claude_enabled=os.environ.get("ROLLOUT_CLAUDE_ENABLED", "0") == "1",
            data_dir=Path(os.environ.get("ROLLOUT_DATA_DIR", defaults.data_dir)),
        )
