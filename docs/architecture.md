# Architecture

RollOut is a pipeline that runs on the Mac:

1. **Wake word** (`voice/wake.py`): openWakeWord listens for "Hey Prime" (a custom model, trained in Phase 2).
2. **Recording** (`voice/listen.py`): Phase 1 records until you press Enter; Phase 2 adds Silero VAD to stop when you stop talking.
3. **Speech to text** (`voice/stt.py`): mlx-whisper transcribes on device.
4. **Router** (`brain/router.py`): sends the request to the local model, or to Claude only when enabled.
5. **Local model** (`brain/local_llm.py`): Qwen3 in Ollama answers, keeping the last few turns as context. Phase 3 adds the agent loop (`brain/agent.py`) so it can call MCP tool servers.
6. **Text to speech** (`voice/tts.py`): `say` or Piper speaks the answer.

## Tool servers (`servers/`)

| Server | Data source | Notes |
| --- | --- | --- |
| tasks | SQLite | tasks and remembered preferences |
| google | Google Calendar and Gmail APIs | OAuth tokens in the macOS Keychain; email is sent only after confirmation |
| school | D2L calendar iCal feed | the feed link is private and stays out of the repo |

## Offline

A sync worker (`store/sync.py`) copies calendar and assignment data into SQLite so reads work offline. Changes made offline go to an outbox (`store/outbox.py`) with an id per action, so each is sent exactly once after reconnecting.
