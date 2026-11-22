import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import voice_live_test as t  # noqa: E402

SPEAKERS = [
    {"name": "A", "styles": [{"name": "normal", "id": 0}, {"name": "sweet", "id": 1}]},
    {"name": "B", "styles": [{"name": "normal", "id": 3}]},
]


def test_speaker_name_found_and_missing():
    assert t.speaker_name(SPEAKERS, 1) == ("A", "sweet")
    assert t.speaker_name(SPEAKERS, 3) == ("B", "normal")
    assert t.speaker_name(SPEAKERS, 99) == (None, None)
    assert t.speaker_name([], 0) == (None, None)


def test_chars_per_sec():
    assert t.chars_per_sec("あ" * 65, 10.0) == 6.5
    assert t.chars_per_sec("abc", 0) == 0.0


def test_sample_length_about_150():
    assert 130 <= len(t.SAMPLE) <= 170


def test_probe_audio(tmp_path):
    p = tmp_path / "a.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", "0.2", str(p)], check=True)
    assert t.probe_audio(p) == (24000, 1)


def test_main_fails_when_unreachable(monkeypatch, capsys):
    monkeypatch.setenv("VOICEVOX_URL", "http://127.0.0.1:9")
    assert t.main() == 1
    assert "FAIL" in capsys.readouterr().err
