from pathlib import Path

from dragon_warrior import __version__
from dragon_warrior.__main__ import main
from dragon_warrior.config import Config


def test_version_is_set():
    assert __version__ == "0.1.0"


def test_config_defaults_are_free_and_local():
    config = Config()
    assert config.claude_enabled is False
    assert config.ollama_url.startswith("http://localhost")


def test_config_reads_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.setenv("JARVIS_CLAUDE_ENABLED", "1")
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    config = Config.from_env()
    assert config.ollama_model == "qwen3:4b"
    assert config.claude_enabled is True
    assert config.data_dir == Path(tmp_path)


def test_main_runs(capsys):
    main()
    assert "Jarvis" in capsys.readouterr().out
