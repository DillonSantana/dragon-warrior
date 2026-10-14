import numpy as np

import rollout.__main__ as app_main
from rollout.config import Config
from rollout.state import AssistantState
from rollout.voice.wake import is_exit

EXITS = Config().exit_phrases


def test_exit_phrase_variants():
    assert is_exit("Roll out.", EXITS)
    assert is_exit("Rollout!", EXITS)
    assert is_exit("Okay, roll out", EXITS)
    assert is_exit("Role out", EXITS)


def test_questions_mentioning_roll_out_are_not_exits():
    assert not is_exit("When does the new phone roll out in stores?", EXITS)
    assert not is_exit("What's on my calendar today?", EXITS)


class ScriptedMic:
    def __init__(self, follow_ups):
        self.follow_ups = list(follow_ups)

    def flush(self):
        pass

    def next_utterance(self, timeout_s=None):
        return self.follow_ups.pop(0) if self.follow_ups else None


class EchoSTT:
    """Each fake utterance is a string; 'transcribing' it returns the string."""

    def transcribe(self, audio):
        return audio


def run(command, follow_ups, monkeypatch, config=None):
    asked, spoken = [], []
    monkeypatch.setattr(
        app_main, "respond", lambda text, llm, cfg, state, theme=None: asked.append((text, theme))
    )
    monkeypatch.setattr(app_main, "speak", lambda text, cfg: spoken.append(text))
    state = AssistantState()
    app_main.converse(
        command, ScriptedMic(follow_ups), None, EchoSTT(), config or Config(), state, "theme"
    )
    return asked, spoken, state


def test_follow_ups_without_wake_phrase_until_roll_out(monkeypatch):
    asked, spoken, _ = run("what's today?", ["and tomorrow?", "Roll out."], monkeypatch)
    assert [text for text, _ in asked] == ["what's today?", "and tomorrow?"]
    assert spoken == [app_main.SIGN_OFF]


def test_theme_plays_only_on_first_answer(monkeypatch):
    asked, _, _ = run("one", ["two"], monkeypatch)
    assert [theme for _, theme in asked] == ["theme", None]


def test_silence_ends_the_conversation(monkeypatch):
    asked, spoken, state = run("hello", [], monkeypatch)
    assert len(asked) == 1 and spoken == []
    assert state.status == "awake"  # the caller sets it back to listening


def test_hey_prime_roll_out_just_signs_off(monkeypatch):
    asked, spoken, _ = run("roll out", [], monkeypatch)
    assert asked == [] and spoken == [app_main.SIGN_OFF]


def test_conversation_mode_can_be_turned_off(monkeypatch):
    asked, _, _ = run("one", ["two"], monkeypatch, Config(conversation=False))
    assert len(asked) == 1


def test_conversation_settings_from_environment(monkeypatch):
    monkeypatch.setenv("ROLLOUT_EXIT_PHRASES", "that's all, goodbye")
    monkeypatch.setenv("ROLLOUT_CONVERSATION", "0")
    config = Config.from_env()
    assert config.exit_phrases == ("that's all", "goodbye")
    assert config.conversation is False


def test_wake_loop_returns_to_listening_after_conversation(monkeypatch):
    state = AssistantState()

    class Mic(ScriptedMic):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def utterances(self):
            yield np.ones(10)

    class STT:
        def __init__(self, model=None):
            pass

        def transcribe(self, audio):
            return "Hey Prime, roll out"

    spoken = []
    monkeypatch.setattr(app_main, "Microphone", lambda: Mic([]))
    monkeypatch.setattr(app_main, "Transcriber", STT)
    monkeypatch.setattr(app_main, "speak", lambda text, cfg: spoken.append(text))
    app_main.run_wake_word(Config(), llm=None, stt=STT(), state=state)
    assert spoken == [app_main.SIGN_OFF]
    assert state.status == "listening"
