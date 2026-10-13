# CLAUDE.md

Jarvis (dragon-warrior): a free, local, voice-activated assistant for macOS on Apple Silicon.

## Conventions

- Python 3.11+, managed with uv. Source in `src/dragon_warrior/`, tests in `tests/`.
- Run `uv run ruff check . && uv run ruff format --check . && uv run pytest` before every commit.
- Must stay free to run: no paid APIs or services as defaults. Claude is optional and off unless `JARVIS_CLAUDE_ENABLED=1`.
- Never commit secrets or personal data: Google tokens, the D2L calendar feed link, `.env`, databases.
- Sending email or deleting anything always requires spoken confirmation.

## Who builds what

Dillon is building these parts himself to learn them. Claude reviews, explains and gives hints, but does not write the implementation unless Dillon asks:

- Audio pipeline (`voice/wake.py`, `voice/listen.py`, `voice/stt.py`)
- Agent loop (`brain/agent.py`)
- Google Calendar and Gmail MCP server (`servers/google`)
- D2L iCal connector (`servers/school`)
- Offline sync and outbox (`store/sync.py`, `store/outbox.py`)
- Tests and CI for the above

Claude may write scaffolding, glue code, the menu bar app, text to speech and the tasks server.
