"""Entry point: `uv run rollout` or `python -m rollout`.

By default RollOut listens hands-free for "Hey Prime" in the terminal. `rollout --menubar`
runs it as a menu bar app instead (what the login item starts). Set ROLLOUT_LISTEN_MODE=push
to press Enter to talk.
"""

import argparse
import subprocess
import time

from rollout import __version__
from rollout.app.theme import Theme
from rollout.brain.local_llm import LocalLLM, OllamaError
from rollout.config import Config
from rollout.state import AssistantState
from rollout.voice.listen import record_until_enter
from rollout.voice.stt import Transcriber
from rollout.voice.tts import speak
from rollout.voice.wake import Microphone, match_wake

FOLLOW_UP_TIMEOUT_S = 8
CHIME = "/System/Library/Sounds/Tink.aiff"


def handle_turn(transcript: str, llm: LocalLLM) -> str:
    """Turn one transcript into the reply RollOut should speak."""
    try:
        return llm.ask(transcript)
    except OllamaError:
        return "I can't reach my local model. Make sure the Ollama app is running."


def respond(
    transcript: str,
    llm: LocalLLM,
    config: Config,
    state: AssistantState,
    theme: Theme | None = None,
) -> None:
    print(f"You: {transcript}", flush=True)
    state.caption = transcript
    state.status = "thinking"
    if theme and config.theme_on in ("wake", "both"):
        theme.play()
    reply = handle_turn(transcript, llm)
    print(f"RollOut: {reply}", flush=True)
    if theme:
        theme.stop()
    state.caption = reply
    state.status = "speaking"
    speak(reply, config)


def command_after_wake(full_transcript: str, phrases) -> str:
    """The command part of "Hey Prime, <command>" as heard by the accurate model."""
    rest = match_wake(full_transcript, phrases)
    return full_transcript if rest is None else rest


def run_push_to_talk(config: Config, llm: LocalLLM, stt: Transcriber) -> None:
    state = AssistantState()
    while True:
        input("\nPress Enter and speak...")
        print("Listening. Press Enter when you're done.")
        transcript = stt.transcribe(record_until_enter())
        if transcript:
            respond(transcript, llm, config, state)
        else:
            print("(didn't catch that)")


def run_wake_word(
    config: Config, llm: LocalLLM, stt: Transcriber, state: AssistantState | None = None
) -> None:
    state = state or AssistantState()
    wake_stt = Transcriber(config.wake_model)
    theme = Theme(config.theme_track, config.theme_start) if config.theme_track else None
    if theme and config.theme_on in ("open", "both"):
        theme.play_for(config.theme_open_seconds, launch=True)
    with Microphone() as mic:
        print('Say "Hey Prime" followed by your question.', flush=True)
        state.status = "listening"
        for audio in mic.utterances():
            if state.stopped.is_set():
                return
            if state.paused.is_set():
                state.status = "paused"
                mic.flush()
                continue
            state.status = "listening"
            rest = match_wake(wake_stt.transcribe(audio), config.wake_phrases)
            if rest is None:
                continue
            state.caption = "Listening…"
            state.status = "awake"
            if rest:
                command = command_after_wake(stt.transcribe(audio), config.wake_phrases)
            else:
                # Just "Hey Prime": chime, then listen for the question
                subprocess.run(["afplay", CHIME], check=False)
                mic.flush()
                follow_up = mic.next_utterance(timeout_s=FOLLOW_UP_TIMEOUT_S)
                command = stt.transcribe(follow_up) if follow_up is not None else ""
            if command.strip():
                respond(command, llm, config, state, theme)
            state.status = "listening"
            mic.flush()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="rollout", description="RollOut voice assistant")
    parser.add_argument("--menubar", action="store_true", help="run as a menu bar app")
    parser.add_argument("--say", metavar="TEXT", help="speak TEXT in RollOut's voice and exit")
    parser.add_argument("--theme", action="store_true", help="play the theme song, then exit")
    args = parser.parse_args(argv)

    config = Config.from_env()
    if args.say:
        speak(args.say, config)
        return
    if args.theme:
        if not config.theme_track:
            print("No theme set. Add ROLLOUT_THEME_TRACK to .env.")
            return
        theme = Theme(config.theme_track, config.theme_start)
        if theme.play(launch=True):
            time.sleep(config.theme_open_seconds)
            theme.stop()
        return
    llm = LocalLLM(config.ollama_model, config.ollama_url)
    stt = Transcriber(config.whisper_model)
    print(f"RollOut {__version__} ready, using {config.ollama_model}. Ctrl+C to quit.", flush=True)
    if args.menubar:
        from rollout.app.menubar import run_menubar

        run_menubar(lambda state: run_wake_word(config, llm, stt, state), config)
        return
    try:
        if config.listen_mode == "push":
            run_push_to_talk(config, llm, stt)
        else:
            run_wake_word(config, llm, stt)
    except (KeyboardInterrupt, EOFError):
        print("\nRollOut out.")


if __name__ == "__main__":
    main()
