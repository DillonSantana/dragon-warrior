# Architecture

RollOut is a pipeline that runs on the Mac:

1. **Listening** (`voice/wake.py`): the mic stays on, and an energy-based voice detector with an adaptive noise floor cuts the stream into utterances when you pause.
2. **Wake phrase** (`voice/wake.py`): a small Whisper model (`whisper-base.en`) transcribes each utterance and checks it for "Hey Prime". Any phrase works without training. If the phrase comes with a question, the accurate model re-transcribes it; if not, RollOut chimes and waits for the question. Push-to-talk (`voice/listen.py`) is still available with `ROLLOUT_LISTEN_MODE=push`.
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

## Running in the background

`scripts/install_login_item.sh` installs a launchd agent (`~/Library/LaunchAgents/com.rollout.assistant.plist`) that runs `rollout --menubar` at login and restarts it after a crash. The menu bar app (`app/menubar.py`, rumps) owns the main thread and shows the state from `state.py`; the listening loop runs on a background thread and checks the pause and quit flags between utterances.
