# CLAUDE.md

RollOut: a free, local, voice-activated assistant for macOS on Apple Silicon.

## Conventions

- Python 3.11+, managed with uv. Source in `src/rollout/`, tests in `tests/`.
- Run `uv run ruff check . && uv run ruff format --check . && uv run pytest` before every commit.
- Must stay free to run: no paid APIs or services as defaults (ElevenLabs is opt-in, with an offline fallback). Claude is optional and off unless `ROLLOUT_CLAUDE_ENABLED=1`.
- Never commit secrets or personal data: Google tokens, the D2L calendar feed link, `.env`, databases.
- Sending email or deleting anything always requires spoken confirmation.

## Who builds what

Claude builds everything; Dillon uses RollOut day to day and reviews pull requests.

## Voice

- Wake phrase: "Hey Prime", spotted by a small Whisper model on each utterance (`voice/wake.py`).
- A licensed voice through ElevenLabs (`tts_style=elevenlabs`) is fine; the API key lives only in the git-ignored `.env`.
- The custom voice style clones only a clip the user has the right to use. Don't source or clone a real person's voice without their consent, and never commit voice clips or cloned voice models.
