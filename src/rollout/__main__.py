"""Entry point: `uv run rollout` or `python -m rollout`.

Phase 1 is push-to-talk in the terminal: press Enter, speak, press Enter again.
"""

from rollout import __version__
from rollout.brain.local_llm import LocalLLM, OllamaError
from rollout.config import Config
from rollout.voice.listen import record_until_enter
from rollout.voice.stt import Transcriber
from rollout.voice.tts import speak


def handle_turn(transcript: str, llm: LocalLLM) -> str:
    """Turn one transcript into the reply RollOut should speak."""
    try:
        return llm.ask(transcript)
    except OllamaError:
        return "I can't reach my local model. Make sure the Ollama app is running."


def main() -> None:
    config = Config.from_env()
    llm = LocalLLM(config.ollama_model, config.ollama_url)
    stt = Transcriber(config.whisper_model)
    print(f"RollOut {__version__} ready, using {config.ollama_model}. Ctrl+C to quit.")
    try:
        while True:
            input("\nPress Enter and speak...")
            print("Listening. Press Enter when you're done.")
            transcript = stt.transcribe(record_until_enter())
            if not transcript:
                print("(didn't catch that)")
                continue
            print(f"You: {transcript}")
            reply = handle_turn(transcript, llm)
            print(f"RollOut: {reply}")
            speak(
                reply,
                config.tts_voice,
                config.tts_rate,
                config.tts_style,
                config.voice_clip,
                config.voice_clip_text,
            )
    except (KeyboardInterrupt, EOFError):
        print("\nRollOut out.")


if __name__ == "__main__":
    main()
