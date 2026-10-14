import numpy as np

from rollout.__main__ import command_after_wake
from rollout.voice.wake import FRAME_SAMPLES, Microphone, SpeechSegmenter, match_wake

PHRASES = ("hey prime", "hi prime")


def frames(level: float, seconds: float, seed: int = 0) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    count = int(seconds * 16_000 / FRAME_SAMPLES)
    return [(rng.standard_normal(FRAME_SAMPLES) * level).astype(np.float32) for _ in range(count)]


def run(segmenter: SpeechSegmenter, chunks: list[np.ndarray]) -> list[np.ndarray]:
    return [u for u in (segmenter.feed(c) for c in chunks) if u is not None]


def test_segmenter_finds_one_utterance_between_silences():
    seg = SpeechSegmenter()
    out = run(seg, frames(0.002, 1.0) + frames(0.2, 1.0, seed=1) + frames(0.002, 1.0, seed=2))
    assert len(out) == 1
    # one second of speech plus pre-roll and trailing silence
    assert 1.0 < len(out[0]) / 16_000 < 2.2


def test_segmenter_ignores_steady_background_noise():
    assert run(SpeechSegmenter(), frames(0.005, 3.0)) == []


def test_segmenter_drops_short_clicks():
    seg = SpeechSegmenter()
    assert run(seg, frames(0.002, 1.0) + frames(0.3, 0.06) + frames(0.002, 1.5)) == []


def test_segmenter_caps_long_utterances():
    seg = SpeechSegmenter(max_s=2.0)
    out = run(seg, frames(0.2, 5.0))
    assert len(out) == 2


def test_match_wake_returns_the_command():
    assert match_wake("Hey Prime, what's on my calendar?", PHRASES) == "what's on my calendar"


def test_match_wake_with_phrase_only():
    assert match_wake("Hey, Prime.", PHRASES) == ""


def test_match_wake_allows_a_filler_word_first():
    assert match_wake("Okay hi prime set a timer", PHRASES) == "set a timer"


def test_match_wake_ignores_other_speech():
    assert match_wake("I watched Prime Video last night", PHRASES) is None
    assert match_wake("so then my friend said hey prime", PHRASES) is None


def test_command_after_wake_falls_back_to_full_transcript():
    assert command_after_wake("Hey Prime, add milk to my list.", PHRASES) == "add milk to my list"
    assert command_after_wake("Add milk to my list.", PHRASES) == "Add milk to my list."


def test_next_utterance_times_out_when_nobody_talks():
    mic = Microphone()
    for chunk in frames(0.002, 1.0):
        mic.frames.put(chunk)
    assert mic.next_utterance(timeout_s=0.5) is None


def test_flush_discards_queued_audio():
    mic = Microphone()
    for chunk in frames(0.2, 0.5):
        mic.frames.put(chunk)
    mic.flush()
    assert mic.frames.empty()
    assert mic.segmenter.frames == []
