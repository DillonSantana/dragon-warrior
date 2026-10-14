import io
import json
import sys
import types
import urllib.error
from pathlib import Path

import numpy as np
import pytest

from rollout.__main__ import handle_turn
from rollout.brain import local_llm
from rollout.brain.local_llm import LocalLLM, OllamaError
from rollout.config import Config
from rollout.voice import tts
from rollout.voice.listen import join_chunks
from rollout.voice.stt import MIN_SAMPLES, Transcriber


def test_join_chunks_flattens_to_mono_float32():
    chunks = [np.ones((4, 1), dtype=np.float32), np.zeros((2, 1), dtype=np.float32)]
    audio = join_chunks(chunks)
    assert audio.shape == (6,)
    assert audio.dtype == np.float32


def test_join_chunks_handles_no_audio():
    assert join_chunks([]).size == 0


def test_transcriber_skips_very_short_audio():
    assert Transcriber("any").transcribe(np.zeros(MIN_SAMPLES - 1, dtype=np.float32)) == ""


def test_transcriber_uses_mlx_whisper(monkeypatch):
    calls = {}

    def fake_transcribe(audio, path_or_hf_repo, language):
        calls["model"] = path_or_hf_repo
        return {"text": "  what's the capital of Peru  "}

    monkeypatch.setitem(
        sys.modules, "mlx_whisper", types.SimpleNamespace(transcribe=fake_transcribe)
    )
    text = Transcriber("some/model").transcribe(np.zeros(MIN_SAMPLES, dtype=np.float32))
    assert text == "what's the capital of Peru"
    assert calls["model"] == "some/model"


def _fake_urlopen(reply, captured):
    def urlopen(request, timeout):
        captured.append(json.loads(request.data))
        return io.BytesIO(json.dumps({"message": {"content": reply}}).encode())

    return urlopen


def test_local_llm_sends_history_and_disables_thinking(monkeypatch):
    sent = []
    monkeypatch.setattr(local_llm.urllib.request, "urlopen", _fake_urlopen(" Lima. ", sent))
    llm = LocalLLM("qwen3:8b", "http://localhost:11434/")
    assert llm.ask("Capital of Peru?") == "Lima."
    llm.ask("And its population?")
    second = sent[1]
    assert second["model"] == "qwen3:8b"
    assert second["think"] is False
    assert [m["role"] for m in second["messages"]] == ["system", "user", "assistant", "user"]


def test_local_llm_keeps_history_bounded(monkeypatch):
    monkeypatch.setattr(local_llm.urllib.request, "urlopen", _fake_urlopen("ok", []))
    llm = LocalLLM("m", "http://x", history_turns=2)
    for i in range(5):
        llm.ask(f"q{i}")
    assert len(llm.history) == 4
    assert llm.history[0]["content"] == "q3"


def test_local_llm_raises_when_ollama_is_down(monkeypatch):
    def down(request, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(local_llm.urllib.request, "urlopen", down)
    with pytest.raises(OllamaError):
        LocalLLM("m", "http://x").ask("hi")


def test_handle_turn_explains_when_ollama_is_down():
    class DownLLM:
        def ask(self, prompt):
            raise OllamaError("down")

    assert "Ollama" in handle_turn("hi", DownLLM())


def test_clean_for_speech_strips_markdown():
    assert tts.clean_for_speech("**Lima** is the\n `capital`") == "Lima is the capital"


def test_speak_calls_say_with_voice_and_rate(monkeypatch):
    ran = []
    monkeypatch.setattr(tts.subprocess, "run", lambda cmd, check: ran.append(cmd))
    tts.speak("Hello", Config(tts_style="plain", tts_voice="Daniel", tts_rate=170))
    assert ran == [["say", "-r", "170", "-v", "Daniel", "Hello"]]


def test_speak_skips_empty_text(monkeypatch):
    ran = []
    monkeypatch.setattr(tts.subprocess, "run", lambda cmd, check: ran.append(cmd))
    tts.speak("  ** ", Config())
    assert ran == []


def test_prime_effect_lowers_pitch_and_stays_in_range():
    sr = 22_050
    t = np.arange(sr) / sr
    audio = (0.5 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)
    out = tts.prime_effect(audio, sr)
    assert len(out) > len(audio)  # resampled slower, so lower pitched
    assert np.max(np.abs(out)) <= 0.91
    assert out.dtype == np.float32


def test_prime_effect_handles_silence():
    assert not np.any(tts.prime_effect(np.zeros(100, dtype=np.float32), 22_050))


def test_wav_round_trip(tmp_path):
    audio = np.linspace(-0.5, 0.5, 1000, dtype=np.float32)
    tts.write_wav(tmp_path / "a.wav", audio, 22_050)
    back, sr = tts.read_wav(tmp_path / "a.wav")
    assert sr == 22_050
    assert np.allclose(back, audio, atol=1e-3)


def test_speak_prime_renders_processes_and_plays(monkeypatch):
    ran = []

    def fake_run(cmd, check):
        ran.append(cmd)
        if cmd[0] == "say":
            out = Path(cmd[cmd.index("-o") + 1])
            tts.write_wav(out, np.full(2_000, 0.2, dtype=np.float32), 22_050)
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(tts.subprocess, "run", fake_run)
    tts.speak("Autobots", Config(tts_style="prime", tts_rate=164))
    say, play = ran
    assert say[:3] == ["say", "-r", "200"] and say[-1] == "Autobots"
    assert play[0] == "afplay"


def test_speak_custom_uses_clip(monkeypatch, tmp_path):
    calls = {}

    def fake_generate(**kwargs):
        calls.update(kwargs)

    module = types.SimpleNamespace(generate=fake_generate)
    monkeypatch.setitem(sys.modules, "f5_tts_mlx", types.SimpleNamespace(generate=module))
    monkeypatch.setitem(sys.modules, "f5_tts_mlx.generate", module)
    clip = tmp_path / "me.wav"
    tts.speak("Hello", Config(tts_style="custom", voice_clip=clip, voice_clip_text="this is me"))
    assert calls == {
        "generation_text": "Hello",
        "ref_audio_path": str(clip),
        "ref_audio_text": "this is me",
    }


def test_custom_without_clip_falls_back_to_prime(monkeypatch):
    ran = []
    monkeypatch.setattr(
        tts.subprocess,
        "run",
        lambda cmd, check: ran.append(cmd) or types.SimpleNamespace(returncode=1),
    )
    tts.speak("Hello", Config(tts_style="custom"))
    assert "-o" in ran[0]


ELEVEN = Config(tts_style="elevenlabs", elevenlabs_api_key="k", elevenlabs_voice_id="voice123")


def test_elevenlabs_fetches_and_plays_mp3(monkeypatch):
    sent, ran = [], []

    def urlopen(request, timeout):
        sent.append(request)
        return io.BytesIO(b"ID3fake-mp3")

    monkeypatch.setattr(tts.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(tts.subprocess, "run", lambda cmd, check: ran.append(cmd))
    tts.speak("Autobots, roll out", ELEVEN)
    request = sent[0]
    assert "/v1/text-to-speech/voice123" in request.full_url
    assert request.get_header("Xi-api-key") == "k"
    assert json.loads(request.data) == {
        "text": "Autobots, roll out",
        "model_id": "eleven_flash_v2_5",
    }
    assert ran[0][0] == "afplay" and ran[0][1].endswith(".mp3")


def test_elevenlabs_offline_falls_back_to_prime(monkeypatch):
    def offline(request, timeout):
        raise urllib.error.URLError("no internet")

    ran = []
    monkeypatch.setattr(tts.urllib.request, "urlopen", offline)
    monkeypatch.setattr(
        tts.subprocess,
        "run",
        lambda cmd, check: ran.append(cmd) or types.SimpleNamespace(returncode=1),
    )
    tts.speak("Hello", ELEVEN)
    assert ran[0][0] == "say" and "-o" in ran[0]


def test_elevenlabs_without_key_falls_back_to_prime(monkeypatch):
    ran = []
    monkeypatch.setattr(
        tts.subprocess,
        "run",
        lambda cmd, check: ran.append(cmd) or types.SimpleNamespace(returncode=1),
    )
    tts.speak("Hello", Config(tts_style="elevenlabs"))
    assert ran[0][0] == "say" and "-o" in ran[0]


def test_say_command_speaks_and_exits(monkeypatch):
    import rollout.__main__ as app_main

    spoken = []
    monkeypatch.setattr(app_main, "speak", lambda text, config: spoken.append(text))
    monkeypatch.setattr(app_main, "LocalLLM", None)  # must not start the assistant
    app_main.main(["--say", "Roll out."])
    assert spoken == ["Roll out."]


def test_elevenlabs_bad_key_explains_and_falls_back(monkeypatch, capsys):
    import io
    import urllib.error

    def refuse(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO())

    played = []
    monkeypatch.setattr(tts.urllib.request, "urlopen", refuse)
    monkeypatch.setattr(tts, "_speak_prime", lambda *a: played.append("prime"))
    tts.speak("Hello", ELEVEN)
    assert played == ["prime"]
    assert "Text to Speech access" in capsys.readouterr().out
