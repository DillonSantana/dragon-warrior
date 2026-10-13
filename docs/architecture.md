# Architecture

Jarvis is a pipeline that runs on the Mac:

1. **Wake word** (`voice/wake.py`): openWakeWord listens for "Hey Jarvis".
2. **End of speech** (`voice/listen.py`): Silero VAD records until you stop talking.
3. **Speech to text** (`voice/stt.py`): mlx-whisper transcribes on device.
4. **Router** (`brain/router.py`): sends the request to the local model, or to Claude only when enabled.
5. **Agent loop** (`brain/agent.py`): the model calls MCP tool servers until it has an answer.
6. **Text to speech** (`voice/tts.py`): `say` or Piper speaks the answer.

## Tool servers (`servers/`)

| Server | Data source | Notes |
| --- | --- | --- |
| tasks | SQLite | tasks and remembered preferences |
| google | Google Calendar and Gmail APIs | OAuth tokens in the macOS Keychain; email is sent only after confirmation |
| school | D2L calendar iCal feed | the feed link is private and stays out of the repo |

## Offline

A sync worker (`store/sync.py`) copies calendar and assignment data into SQLite so reads work offline. Changes made offline go to an outbox (`store/outbox.py`) with an id per action, so each is sent exactly once after reconnecting.
