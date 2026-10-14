from rollout.app import theme as theme_module
from rollout.app.theme import Theme, parse_start, track_uri
from rollout.config import Config

TRACK = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC?si=abc123"


def test_track_uri_from_link_or_uri():
    assert track_uri(TRACK) == "spotify:track:4uLU6hMCjMI75M1A2tKUQC"
    uri = "spotify:track:4uLU6hMCjMI75M1A2tKUQC"
    assert track_uri(uri) == uri
    assert track_uri("not a song") is None


def test_parse_start():
    assert parse_start("83") == 83
    assert parse_start("1:23") == 83
    assert parse_start("1:23.5") == 83.5


class FakeSpotify:
    """Answers like Spotify, which only takes a jump once the new song has loaded."""

    def __init__(self, running="true", state="paused", load_after=0):
        self.answers = {"is running": running, "player state": state, "sound volume as": "70"}
        self.scripts = []
        self.track = "spotify:track:old"
        self.position = "0"
        self.load_after = load_after  # how many "current track" checks before it loads

    def __call__(self, script):
        self.scripts.append(script)
        if "play track" in script:
            self.pending = script.split('"')[3]
            return ""
        if "id of current track" in script:
            if self.load_after == 0:
                self.track = getattr(self, "pending", self.track)
            else:
                self.load_after -= 1
            return self.track
        if "set player position to" in script:
            if self.track == getattr(self, "pending", None):
                self.position = script.rsplit(" ", 1)[1].replace(".", ",")
            return ""
        if "to player position" in script:
            return self.position
        for key, answer in self.answers.items():
            if key in script:
                return answer
        return ""


def test_plays_track_from_start_point_and_restores_volume(monkeypatch):
    monkeypatch.setattr(theme_module.time, "sleep", lambda s: None)
    spotify = FakeSpotify()
    theme = Theme(TRACK, 83, run=spotify)
    assert theme.play()
    assert any('play track "spotify:track:4uLU6hMCjMI75M1A2tKUQC"' in s for s in spotify.scripts)
    assert spotify.position.startswith("83")
    theme.stop()
    assert spotify.scripts[-2].endswith("to pause")
    assert spotify.scripts[-1].endswith("set sound volume to 70")


def test_never_interrupts_music_already_playing():
    spotify = FakeSpotify(state="playing")
    theme = Theme(TRACK, 0, run=spotify)
    assert not theme.play()
    theme.stop()
    assert not any("pause" in s for s in spotify.scripts)


def test_does_not_open_spotify_on_wake():
    spotify = FakeSpotify(running="false")
    assert not Theme(TRACK, run=spotify).play()
    assert not any("launch" in s for s in spotify.scripts)


def test_opens_spotify_when_rollout_starts():
    spotify = FakeSpotify(running="false")
    assert Theme(TRACK, run=spotify).play(launch=True)
    assert 'tell application "Spotify" to launch' in spotify.scripts


def test_osascript_explains_missing_permission(monkeypatch, capsys):
    import subprocess

    def refuse(*args, **kwargs):
        return subprocess.CompletedProcess(
            args, 1, "", "execution error: Not authorized to send Apple events to Spotify. (-1743)"
        )

    monkeypatch.setattr(theme_module.subprocess, "run", refuse)
    assert theme_module.osascript('tell application "Spotify" to pause') == ""
    assert "Privacy & Security > Automation" in capsys.readouterr().out


def test_osascript_survives_a_hung_spotify(monkeypatch):
    import subprocess

    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired("osascript", 10)

    monkeypatch.setattr(theme_module.subprocess, "run", hang)
    assert theme_module.osascript("anything") == ""


def test_theme_command_without_song(monkeypatch, capsys):
    import rollout.__main__ as app_main

    monkeypatch.delenv("ROLLOUT_THEME_TRACK", raising=False)
    monkeypatch.setattr(app_main.Config, "from_env", classmethod(lambda cls: Config()))
    app_main.main(["--theme"])
    assert "ROLLOUT_THEME_TRACK" in capsys.readouterr().out


def test_theme_settings_from_environment(monkeypatch):
    monkeypatch.setenv("ROLLOUT_THEME_TRACK", TRACK)
    monkeypatch.setenv("ROLLOUT_THEME_START", "2:05")
    monkeypatch.setenv("ROLLOUT_THEME_ON", "wake")
    config = Config.from_env()
    assert config.theme_track == TRACK
    assert config.theme_start == 125
    assert config.theme_on == "wake"
    assert Config().theme_track is None


def test_theme_pauses_before_rollout_speaks(monkeypatch):
    import rollout.__main__ as app_main

    events = []

    class FakeTheme:
        def play(self):
            events.append("play")

        def stop(self):
            events.append("stop")

    class FakeLLM:
        def ask(self, prompt):
            events.append("think")
            return "Roll out."

    monkeypatch.setattr(app_main, "speak", lambda text, config: events.append("speak"))
    state = app_main.AssistantState()
    app_main.respond("hello", FakeLLM(), Config(), state, FakeTheme())
    assert events == ["play", "think", "stop", "speak"]


def test_waits_for_song_to_load_before_jumping(monkeypatch):
    monkeypatch.setattr(theme_module.time, "sleep", lambda s: None)
    spotify = FakeSpotify(load_after=3)
    assert Theme(TRACK, 48, run=spotify).play()
    assert spotify.position.startswith("48")
