import numpy as np

import rollout.__main__ as app_main
from rollout.app import overlay
from rollout.config import Config
from rollout.state import AssistantState


def test_emblem_shows_only_while_awake_thinking_or_speaking():
    assert overlay.target_alpha("awake", paused=False) == 1.0
    assert overlay.target_alpha("speaking", paused=False) == 1.0
    assert overlay.target_alpha("listening", paused=False) == 0.0
    assert overlay.target_alpha("speaking", paused=True) == 0.0


def test_alpha_fades_and_stops_at_target():
    assert overlay.step_alpha(0.0, 1.0, dt=0.1, fade_s=0.25) == 0.4
    assert overlay.step_alpha(0.9, 1.0, dt=0.1, fade_s=0.25) == 1.0
    assert overlay.step_alpha(0.1, 0.0, dt=0.1, fade_s=0.25) == 0.0


def test_glow_stays_in_range():
    for status in ("awake", "thinking", "speaking"):
        for i in range(100):
            assert 0.0 <= overlay.glow(status, i * 0.037) <= 1.0


def test_emblem_is_symmetric_and_inside_unit_square():
    for _, points in overlay.emblem_shapes():
        assert all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in points)
    shield = overlay.symmetric(overlay.SHIELD_HALF)
    assert sorted((round(1 - x, 6), y) for x, y in shield) == sorted(
        (round(x, 6), y) for x, y in shield
    )


def test_caption_is_trimmed():
    assert overlay.caption_for("  hi\nthere ") == "hi there"
    long = overlay.caption_for("word " * 100, limit=20)
    assert len(long) <= 20 and long.endswith("…")


def test_window_positions_stay_on_screen():
    screen = (0, 25, 1440, 875)
    for position in ("bottom", "center", "top-right"):
        x, y = overlay.window_origin(screen, position)
        assert 0 <= x <= 1440 - overlay.SIZE[0]
        assert 25 <= y <= 900 - overlay.SIZE[1]


def test_overlay_settings_from_environment(monkeypatch):
    monkeypatch.setenv("ROLLOUT_OVERLAY", "0")
    monkeypatch.setenv("ROLLOUT_OVERLAY_IMAGE", "~/Pictures/crest.png")
    config = Config.from_env()
    assert config.overlay is False
    assert config.overlay_image.name == "crest.png"
    assert "~" not in str(config.overlay_image)


def test_wake_phrase_wakes_the_emblem(monkeypatch):
    state = AssistantState()
    seen = []

    class Mic:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def flush(self):
            pass

        def utterances(self):
            yield np.ones(10)

        def next_utterance(self, timeout_s=None):
            return None

    class STT:
        def __init__(self, model):
            pass

        def transcribe(self, audio):
            return "Hey Prime, what's on today?"

    def respond(command, llm, config, state):
        seen.append((state.status, state.caption, command))

    monkeypatch.setattr(app_main, "Microphone", Mic)
    monkeypatch.setattr(app_main, "Transcriber", STT)
    monkeypatch.setattr(app_main, "respond", respond)
    app_main.run_wake_word(Config(), llm=None, stt=STT("big"), state=state)
    assert [(status, caption) for status, caption, _ in seen] == [("awake", "Listening…")]
    assert state.status == "listening"


def test_insignia_in_project_folder_is_picked_up(monkeypatch, tmp_path):
    import rollout.config as config_module

    monkeypatch.delenv("ROLLOUT_OVERLAY_IMAGE", raising=False)
    insignia = tmp_path / "insignia.png"
    monkeypatch.setattr(config_module, "DEFAULT_OVERLAY_IMAGE", insignia)
    assert Config.from_env().overlay_image is None
    insignia.write_bytes(b"png")
    assert Config.from_env().overlay_image == insignia
