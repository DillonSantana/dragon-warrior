"""Entry point: `uv run rollout` or `python -m rollout`."""

from rollout import __version__
from rollout.config import Config


def main() -> None:
    config = Config.from_env()
    print(f"RollOut {__version__} starting with model {config.ollama_model}")
    print("Nothing to run yet: the voice loop arrives in Phase 1.")


if __name__ == "__main__":
    main()
