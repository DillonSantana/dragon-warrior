import io
import json
import sys
import types
import urllib.error

import numpy as np
import pytest

from rollout.__main__ import handle_turn
from rollout.brain import local_llm
from rollout.brain.local_llm import LocalLLM, OllamaError
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
    tts.speak("Hello", voice="Daniel", rate=170)
    assert ran == [["say", "-r", "170", "-v", "Daniel", "Hello"]]


def test_speak_skips_empty_text(monkeypatch):
    ran = []
    monkeypatch.setattr(tts.subprocess, "run", lambda cmd, check: ran.append(cmd))
    tts.speak("  ** ")
    assert ran == []
