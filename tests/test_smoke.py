from pathlib import Path

from rollout import __version__
from rollout.__main__ import main
from rollout.config import Config


def test_version_is_set():
    assert __version__ == "0.1.0"


def test_config_defaults_are_free_and_local():
    config = Config()
    assert config.claude_enabled is False
    assert config.tts_style == "prime"
    assert config.listen_mode == "wake"
    assert "hey prime" in config.wake_phrases
    assert config.ollama_url.startswith("http://localhost")


def test_wake_phrases_from_environment(monkeypatch):
    monkeypatch.setenv("ROLLOUT_WAKE_PHRASES", "Hey Prime, optimus ,")
    assert Config.from_env().wake_phrases == ("Hey Prime", "optimus")


def test_config_reads_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("ROLLOUT_OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.setenv("ROLLOUT_CLAUDE_ENABLED", "1")
    monkeypatch.setenv("ROLLOUT_DATA_DIR", str(tmp_path))
    config = Config.from_env()
    assert config.ollama_model == "qwen3:4b"
    assert config.claude_enabled is True
    assert config.data_dir == Path(tmp_path)


def test_main_exits_cleanly_on_ctrl_c(monkeypatch, capsys):
    def interrupt(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setenv("ROLLOUT_LISTEN_MODE", "push")
    monkeypatch.setattr("builtins.input", interrupt)
    main()
    assert "RollOut" in capsys.readouterr().out
