"""Hands-free listening: split the microphone stream into utterances and spot "Hey Prime".

Instead of a trained wake word model, every utterance is transcribed by a small, fast
Whisper model and checked for the wake phrase. Any phrase works with no training.
"""

import queue
import re
from collections import deque
from collections.abc import Iterable, Iterator

import numpy as np

from rollout.voice.listen import SAMPLE_RATE

FRAME_SAMPLES = 480  # 30 ms at 16 kHz


class SpeechSegmenter:
    """Energy-based voice activity detection with an adaptive noise floor.

    Feed fixed-size frames; `feed` returns a whole utterance once the speaker stops.
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        frame_samples: int = FRAME_SAMPLES,
        start_ratio: float = 3.0,
        min_level: float = 0.01,
        silence_s: float = 0.8,
        preroll_s: float = 0.3,
        min_speech_s: float = 0.25,
        max_s: float = 15.0,
    ):
        frame_s = frame_samples / sample_rate
        self.start_ratio = start_ratio
        self.min_level = min_level
        self.silence_frames = int(silence_s / frame_s)
        self.min_speech_frames = int(min_speech_s / frame_s)
        self.max_frames = int(max_s / frame_s)
        self.preroll: deque[np.ndarray] = deque(maxlen=int(preroll_s / frame_s))
        self.noise = min_level / start_ratio
        self.reset()

    def reset(self) -> None:
        self.frames: list[np.ndarray] = []
        self.speech_frames = 0
        self.quiet_frames = 0
        self.preroll.clear()

    @property
    def threshold(self) -> float:
        return max(self.min_level, self.noise * self.start_ratio)

    def feed(self, frame: np.ndarray) -> np.ndarray | None:
        level = float(np.sqrt(np.mean(frame**2))) if frame.size else 0.0
        if not self.frames:
            if level > self.threshold:
                self.frames = [*self.preroll, frame]
                self.speech_frames = 1
                self.quiet_frames = 0
            else:
                self.noise = 0.95 * self.noise + 0.05 * level
                self.preroll.append(frame)
            return None

        self.frames.append(frame)
        if level > self.threshold * 0.7:
            self.speech_frames += 1
            self.quiet_frames = 0
        else:
            self.quiet_frames += 1
        if self.quiet_frames >= self.silence_frames or len(self.frames) >= self.max_frames:
            done, enough = self.frames, self.speech_frames >= self.min_speech_frames
            self.reset()
            return np.concatenate(done) if enough else None
        return None


def _normalize(text: str) -> list[str]:
    return re.sub(r"[^a-z' ]+", " ", text.lower()).split()


def match_wake(text: str, phrases: Iterable[str]) -> str | None:
    """Return what was said after the wake phrase, or None if no phrase was heard.

    The phrase must start within the first few words, so "I asked hey prime yesterday"
    late in a sentence doesn't count.
    """
    words = _normalize(text)
    for phrase in phrases:
        target = _normalize(phrase)
        for start in range(min(3, len(words))):
            if words[start : start + len(target)] == target:
                return " ".join(words[start + len(target) :])
    return None


class Microphone:
    """An always-on microphone stream that yields utterances."""

    def __init__(self, segmenter: SpeechSegmenter | None = None):
        self.segmenter = segmenter or SpeechSegmenter()
        self.frames: queue.Queue[np.ndarray] = queue.Queue()
        self.stream = None

    def __enter__(self) -> "Microphone":
        import sounddevice as sd

        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=FRAME_SAMPLES,
            callback=lambda indata, frames, time, status: self.frames.put(indata[:, 0].copy()),
        )
        self.stream.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stream.stop()
        self.stream.close()

    def flush(self) -> None:
        """Drop audio captured while RollOut was busy or talking, so it doesn't hear itself."""
        while not self.frames.empty():
            self.frames.get_nowait()
        self.segmenter.reset()

    def utterances(self) -> Iterator[np.ndarray]:
        while True:
            utterance = self.next_utterance()
            if utterance is not None:
                yield utterance

    def next_utterance(self, timeout_s: float | None = None) -> np.ndarray | None:
        """Wait for one utterance; give up after `timeout_s` seconds of nobody starting to talk."""
        waited = 0
        frame_s = FRAME_SAMPLES / SAMPLE_RATE
        while True:
            utterance = self.segmenter.feed(self.frames.get())
            if utterance is not None:
                return utterance
            waited += 1
            if timeout_s is not None and not self.segmenter.frames and waited * frame_s > timeout_s:
                return None
