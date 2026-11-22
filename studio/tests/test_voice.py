import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import voice  # noqa: E402
from studio.errors import NotConnected  # noqa: E402


def project(tmp_path, narrations):
    secs = [dict(heading="h", narration=n, visual_prompt="v", seconds=5) for n in narrations]
    (tmp_path / "script.json").write_text(json.dumps(dict(sections=secs)), encoding="utf-8")
    return tmp_path


def test_mock_voice_length_scales_and_is_mock(tmp_path):
    v = voice.MockVoice()
    d1 = v.synthesize("あ" * 65, "ja", tmp_path / "a.wav")
    d2 = v.synthesize("あ" * 130, "ja", tmp_path / "b.wav")
    assert abs(d1 - 10) < 0.1 and abs(d2 - 20) < 0.1
    assert abs(v.synthesize("x" * 150, "en", tmp_path / "c.wav") - 10) < 0.1
    assert v.describe()["status"] == "mock"


def test_render_voice_writes_files_and_durations(tmp_path):
    p = project(tmp_path, ["こんにちは。" * 5, "second"])
    d = voice.render_voice(p, voice.MockVoice(), "ja")
    assert set(d) == {"01", "02"}
    assert (p / "voice/section_02.wav").exists()
    assert json.loads((p / "voice/durations.json").read_text()) == d


class Resp:
    def __init__(self, content=b"", js=None):
        self.content, self._js = content, js

    def raise_for_status(self):
        pass

    def json(self):
        return self._js


class FakeSession:
    def __init__(self, wav):
        self.wav, self.calls = wav, []

    def post(self, url, params=None, json=None, timeout=None):
        assert timeout
        self.calls.append((url, params))
        return Resp(js={"q": 1}) if url.endswith("/audio_query") else Resp(content=self.wav)


def test_voicevox_splits_and_concats(tmp_path):
    wav = tmp_path / "t.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.5", str(wav)], check=True)
    s = FakeSession(wav.read_bytes())
    vv = voice.VoicevoxVoice(base_url="http://x:1", speaker=7, session=s)
    dur = vv.synthesize("一つ目。二つ目！\n三つ目？", "ja", tmp_path / "o.wav")
    assert abs(dur - 1.5) < 0.1
    assert [c for c in s.calls if c[0].endswith("audio_query")][0][1] == {"text": "一つ目。", "speaker": 7}
    assert len(s.calls) == 6


def test_voicevox_unreachable_names_url(tmp_path):
    import requests

    class Down:
        def post(self, *a, **k):
            raise requests.ConnectionError("no")

    with pytest.raises(NotConnected, match="VOICEVOX_URL"):
        voice.VoicevoxVoice(session=Down()).synthesize("a。", "ja", tmp_path / "o.wav")


def test_english_stub():
    with pytest.raises(NotConnected, match="OPENAI_API_KEY"):
        voice.EnglishVoice().synthesize("hi", "en", Path("x.wav"))
    assert voice.EnglishVoice().describe()["status"] == "not_connected"
