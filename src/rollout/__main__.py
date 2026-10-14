"""Entry point: `uv run rollout` or `python -m rollout`.

By default RollOut listens hands-free for "Hey Prime". Set ROLLOUT_LISTEN_MODE=push to
press Enter to talk instead.
"""

import subprocess

from rollout import __version__
from rollout.brain.local_llm import LocalLLM, OllamaError
from rollout.config import Config
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


def respond(transcript: str, llm: LocalLLM, config: Config) -> None:
    print(f"You: {transcript}")
    reply = handle_turn(transcript, llm)
    print(f"RollOut: {reply}")
    speak(reply, config)


def command_after_wake(full_transcript: str, phrases) -> str:
    """The command part of "Hey Prime, <command>" as heard by the accurate model."""
    rest = match_wake(full_transcript, phrases)
    return full_transcript if rest is None else rest


def run_push_to_talk(config: Config, llm: LocalLLM, stt: Transcriber) -> None:
    while True:
        input("\nPress Enter and speak...")
        print("Listening. Press Enter when you're done.")
        transcript = stt.transcribe(record_until_enter())
        if transcript:
            respond(transcript, llm, config)
        else:
            print("(didn't catch that)")


def run_wake_word(config: Config, llm: LocalLLM, stt: Transcriber) -> None:
    wake_stt = Transcriber(config.wake_model)
    with Microphone() as mic:
        print('Say "Hey Prime" followed by your question.')
        for audio in mic.utterances():
            rest = match_wake(wake_stt.transcribe(audio), config.wake_phrases)
            if rest is None:
                continue
            if rest:
                command = command_after_wake(stt.transcribe(audio), config.wake_phrases)
            else:
                # Just "Hey Prime": chime, then listen for the question
                subprocess.run(["afplay", CHIME], check=False)
                mic.flush()
                follow_up = mic.next_utterance(timeout_s=FOLLOW_UP_TIMEOUT_S)
                command = stt.transcribe(follow_up) if follow_up is not None else ""
            if command.strip():
                respond(command, llm, config)
            mic.flush()


def main() -> None:
    config = Config.from_env()
    llm = LocalLLM(config.ollama_model, config.ollama_url)
    stt = Transcriber(config.whisper_model)
    print(f"RollOut {__version__} ready, using {config.ollama_model}. Ctrl+C to quit.")
    try:
        if config.listen_mode == "push":
            run_push_to_talk(config, llm, stt)
        else:
            run_wake_word(config, llm, stt)
    except (KeyboardInterrupt, EOFError):
        print("\nRollOut out.")


if __name__ == "__main__":
    main()
