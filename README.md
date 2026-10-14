# RollOut

RollOut is a voice-activated daily assistant that runs entirely on a Mac. Say "Hey Prime" to ask about your schedule, tasks, email and school assignments. Everything runs locally and costs nothing to use: speech recognition, the language model and your data all stay on the machine.

> Status: Phase 2 done (hands-free "Hey Prime" in the menu bar). See the [roadmap](#roadmap).

## How it works

```
"Hey Prime" -> end of speech -> speech to text
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

Say "Hey Prime" and your question in one breath ("Hey Prime, what's the capital of Peru?"), or say "Hey Prime", wait for the chime, then ask. After it answers, keep talking without saying "Hey Prime" again: RollOut listens for follow-ups until you say "Roll out" or stay quiet for 10 seconds, then waits for "Hey Prime". Set `ROLLOUT_CONVERSATION=0` for one question per "Hey Prime", `ROLLOUT_CONVERSATION_TIMEOUT` to change the quiet time, or `ROLLOUT_EXIT_PHRASES` (comma-separated) for other exit phrases. To press Enter to talk instead, set `ROLLOUT_LISTEN_MODE=push`. The first run downloads the Whisper models (about 1.8 GB). macOS will ask for microphone access for your terminal app.

Settings are environment variables, for example `ROLLOUT_OLLAMA_MODEL=qwen3:4b` on a Mac with 8 GB of memory, or `ROLLOUT_TTS_VOICE=Daniel` for a different `say` voice.

Run the checks:

```sh
uv run ruff check .
uv run pytest
```

## Run it in the background

To have RollOut start every time you log in and wait in the menu bar for "Hey Prime":

```sh
./scripts/install_login_item.sh
```

A "Prime" item appears in the menu bar: ● listening, ⋯ thinking, ♪ speaking, ‖ paused. Its menu can pause listening or quit. If it crashes, macOS restarts it. Logs go to `~/Library/Logs/rollout.log`. To remove it, run `./scripts/install_login_item.sh --remove`.

When you say "Hey Prime", a glowing crest fades in near the bottom of your screen, like Siri. It shows what you asked and RollOut's answer, spins while RollOut thinks, pulses while it talks, and fades away when it's done. It never takes clicks or focus. To use your own picture instead of the built-in crest, save a square PNG with a transparent background as `insignia.png` in the `roll-out` folder (git keeps it out of the repo), or point `ROLLOUT_OVERLAY_IMAGE` in `.env` at one elsewhere. `ROLLOUT_OVERLAY_POSITION` can be `bottom`, `center` or `top-right`, and `ROLLOUT_OVERLAY=0` turns it off. Restart RollOut from its menu after changing `.env`.

Run `uv run rollout` from Terminal once first so macOS asks for microphone access and the models download. Keep the Ollama app set to open at login too.

## Voice

`ROLLOUT_TTS_STYLE` picks how RollOut sounds:

| Style | Sound | Setup |
| --- | --- | --- |
| `prime` (default) | a deeper, pitched-down voice with a short echo | none; try `ROLLOUT_TTS_VOICE=Alex` or another voice from `say -v '?'` |
| `plain` | the macOS `say` voice as is | none |
| `elevenlabs` | a voice from your ElevenLabs account, such as a licensed character voice | copy `.env.example` to `.env`, then fill in `ELEVENLABS_API_KEY` and `ROLLOUT_ELEVENLABS_VOICE_ID`. Needs internet and uses your ElevenLabs credits; when offline it falls back to `prime` |
| `custom` | matches a voice from a reference clip | put a 5 to 10 second mono 24 kHz WAV in `voices/`, then set `ROLLOUT_VOICE_CLIP` to its path and `ROLLOUT_VOICE_CLIP_TEXT` to exactly what it says |

Only use clips of a voice you have the right to use, such as your own. The `voices/` folder is git-ignored so clips never reach the public repo. Custom voice generation runs on device with [F5-TTS for MLX](https://github.com/lucasnewman/f5-tts-mlx) and takes a few seconds per reply.

To hear the current voice without talking to RollOut, run `uv run rollout --say "Roll out."`. If ElevenLabs can't be used, it prints why and speaks in the `prime` voice instead.

To convert a recording: `ffmpeg -i input.m4a -ac 1 -ar 24000 -sample_fmt s16 -t 10 voices/me.wav`

## Theme music

RollOut can play a song from the Spotify desktop app, starting at a point you choose. In Spotify, right-click the song, choose Share, then Copy Song Link, and add it to `.env`:

```sh
ROLLOUT_THEME_TRACK=https://open.spotify.com/track/...
ROLLOUT_THEME_START=1:23
```

By default it plays for 20 seconds when RollOut starts, and again while RollOut works out each answer, fading out before it speaks. Set `ROLLOUT_THEME_ON` to `wake` or `open` to keep only one of those. It never interrupts music you're already playing, and it won't open Spotify just for a "Hey Prime". The first time, macOS asks whether RollOut may control Spotify; choose OK. To test it, run `uv run rollout --theme` (it plays for `ROLLOUT_THEME_OPEN_SECONDS`, 20 by default); if the song doesn't play, it prints why.

## Roadmap

- [x] Phase 0: project setup and CI
- [x] Phase 1: push-to-talk voice loop
- [x] Phase 2: wake word, menu bar, start at login
- [ ] Phase 3: agent loop, tasks and memory
- [ ] Phase 4: Google Calendar and Gmail
- [ ] Phase 5: D2L assignments
- [ ] Phase 6: offline sync and outbox
- [ ] Phase 7: briefings, routines and reminders

## License

MIT
