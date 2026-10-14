import numpy as np

import rollout.__main__ as app_main
from rollout.app.menubar import TITLES, title_for
from rollout.config import Config
from rollout.state import AssistantState


def test_title_follows_status():
    state = AssistantState(status="thinking")
    assert title_for(state) == TITLES["thinking"]
    state.paused.set()
    assert title_for(state) == TITLES["paused"]


class FakeMic:
    def __init__(self, utterances, state, pause_after=None):
        self.queue = list(utterances)
        self.state = state
        self.pause_after = pause_after
        self.flushes = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def flush(self):
        self.flushes += 1

    def utterances(self):
        while self.queue:
            yield self.queue.pop(0)
        self.state.stopped.set()
        yield np.zeros(1)

    def next_utterance(self, timeout_s=None):
        return None


class FakeSTT:
    def __init__(self, model):
        self.model = model

    def transcribe(self, audio):
        return "Hey Prime, what time is it?"


def test_paused_loop_ignores_wake_phrase(monkeypatch):
    state = AssistantState()
    state.paused.set()
    asked = []
    monkeypatch.setattr(app_main, "Microphone", lambda: FakeMic([np.ones(10)], state))
    monkeypatch.setattr(app_main, "Transcriber", FakeSTT)
    monkeypatch.setattr(app_main, "respond", lambda *a: asked.append(a))
    app_main.run_wake_word(Config(), llm=None, stt=FakeSTT("big"), state=state)
    assert asked == []
    assert state.status == "paused"


def test_listening_loop_answers_and_stops(monkeypatch):
    state = AssistantState()
    asked = []
    monkeypatch.setattr(app_main, "Microphone", lambda: FakeMic([np.ones(10)], state))
    monkeypatch.setattr(app_main, "Transcriber", FakeSTT)
    monkeypatch.setattr(app_main, "respond", lambda command, *a: asked.append(command))
    app_main.run_wake_word(Config(), llm=None, stt=FakeSTT("big"), state=state)
    assert asked == ["what time is it"]
    assert state.status == "listening"
