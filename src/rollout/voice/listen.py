"""Record from the default microphone until the user presses Enter."""

from collections.abc import Callable

import numpy as np

SAMPLE_RATE = 16_000  # Whisper expects 16 kHz mono float32


def join_chunks(chunks: list[np.ndarray]) -> np.ndarray:
    """Flatten recorded chunks into one mono float32 array."""
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    audio = np.concatenate(chunks)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio.astype(np.float32, copy=False)


def record_until_enter(wait: Callable[[], object] = input) -> np.ndarray:
    """Record while `wait` blocks (by default, until Enter), then return the audio."""
    import sounddevice as sd  # imported here so tests and CI don't need PortAudio

    chunks: list[np.ndarray] = []

    def on_audio(indata, frames, time, status):
        chunks.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=on_audio):
        wait()
    return join_chunks(chunks)
