# RollOut

RollOut is a voice-activated daily assistant that runs entirely on a Mac. Say "Hey Prime" to ask about your schedule, tasks, email and school assignments. Everything runs locally and costs nothing to use: speech recognition, the language model and your data all stay on the machine.

> Status: Phase 1 (push-to-talk voice loop). See the [roadmap](#roadmap).

## How it works

```
wake word -> end of speech -> speech to text
    -> router -> local model (Ollama) -> MCP tool servers -> answer -> text to speech
```

| Part | Tool |
| --- | --- |
| Wake word | openWakeWord |
| End of speech | Silero VAD |
| Speech to text | mlx-whisper |
| Brain | Qwen3 via Ollama (Claude optional, off by default) |
| Integrations | MCP servers: tasks, Google Calendar and Gmail, D2L assignments |
| Storage | SQLite cache and offline outbox |
| Menu bar | rumps |

More detail in [docs/architecture.md](docs/architecture.md).

## Getting started

Requires macOS on Apple Silicon, [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com).

```sh
git clone https://github.com/DillonSantana/roll-out
cd roll-out
uv sync
ollama pull qwen3:8b
uv run rollout
```

For now RollOut is push-to-talk in the terminal: press Enter, speak, then press Enter again. The first run downloads the Whisper model (about 1.6 GB). macOS will ask for microphone access for your terminal app.

Settings are environment variables, for example `ROLLOUT_OLLAMA_MODEL=qwen3:4b` on a Mac with 8 GB of memory, or `ROLLOUT_TTS_VOICE=Daniel` for a different `say` voice.

Run the checks:

```sh
uv run ruff check .
uv run pytest
```

## Roadmap

- [x] Phase 0: project setup and CI
- [x] Phase 1: push-to-talk voice loop
- [ ] Phase 2: wake word, menu bar, start at login
- [ ] Phase 3: agent loop, tasks and memory
- [ ] Phase 4: Google Calendar and Gmail
- [ ] Phase 5: D2L assignments
- [ ] Phase 6: offline sync and outbox
- [ ] Phase 7: briefings, routines and reminders

## License

MIT
