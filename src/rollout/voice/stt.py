"""Speech to text with Whisper running on Apple Silicon through mlx-whisper."""

import numpy as np

MIN_SAMPLES = 8_000  # half a second at 16 kHz; anything shorter is a stray key press


class Transcriber:
    def __init__(self, model: str):
        self.model = model

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size < MIN_SAMPLES:
            return ""
        import mlx_whisper  # macOS only; loaded on first use and cached by mlx-whisper

        result = mlx_whisper.transcribe(audio, path_or_hf_repo=self.model, language="en")
        return result["text"].strip()
