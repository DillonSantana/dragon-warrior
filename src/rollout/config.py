"""Settings for RollOut, read from environment variables with sensible defaults."""

import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_data_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "rollout"


@dataclass(frozen=True)
class Config:
    # openWakeWord's pretrained model until a custom RollOut wake word is trained (Phase 2)
    wake_word: str = "hey_jarvis"
    ollama_model: str = "qwen3:8b"
    ollama_url: str = "http://localhost:11434"
    claude_enabled: bool = False
    data_dir: Path = field(default_factory=_default_data_dir)

    @classmethod
    def from_env(cls) -> "Config":
        defaults = cls()
        return cls(
            wake_word=os.environ.get("ROLLOUT_WAKE_WORD", defaults.wake_word),
            ollama_model=os.environ.get("ROLLOUT_OLLAMA_MODEL", defaults.ollama_model),
            ollama_url=os.environ.get("ROLLOUT_OLLAMA_URL", defaults.ollama_url),
            claude_enabled=os.environ.get("ROLLOUT_CLAUDE_ENABLED", "0") == "1",
            data_dir=Path(os.environ.get("ROLLOUT_DATA_DIR", defaults.data_dir)),
        )
