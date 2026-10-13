"""Entry point: `uv run jarvis` or `python -m dragon_warrior`."""

from dragon_warrior import __version__
from dragon_warrior.config import Config


def main() -> None:
    config = Config.from_env()
    print(f"Jarvis {__version__} starting with model {config.ollama_model}")
    print("Nothing to run yet: the voice loop arrives in Phase 1.")


if __name__ == "__main__":
    main()
