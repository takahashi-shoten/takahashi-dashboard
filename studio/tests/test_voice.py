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
    d1 = v.synthesize("あ" * 55, "ja", tmp_path / "a.wav")      # 5.5 chars/s (measured with real VOICEVOX)
    d2 = v.synthesize("あ" * 110, "ja", tmp_path / "b.wav")
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


def test_fit_to_total_speeds_up_within_limit_and_refuses_beyond(tmp_path):
    import subprocess
    vd = tmp_path / "voice"; vd.mkdir()
    for k in ("01", "02"):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=35", "-ar", "24000", "-ac", "1", str(vd / f"section_{k}.wav")], check=True)
    d = {"01": 35.0, "02": 35.0}                       # 70 s + 0.4 > 59: needs ~x1.19
    out = voice.fit_to_total(tmp_path, d, 59.0)
    assert sum(out.values()) + 0.4 <= 59.0 + 0.1 and out["01"] < 35.0
    d2 = {"01": 100.0, "02": 100.0}
    try:
        voice.fit_to_total(tmp_path, d2, 59.0)
        assert False, "must refuse a x3 speed-up"
    except ValueError:
        pass
    assert voice.GeminiVoice.STYLE_SHORT["en"] != voice.GeminiVoice.STYLE["en"]


def test_gemini_voice_daily_limit_falls_back_and_caches(tmp_path, monkeypatch):
    from studio import gemini, voice
    monkeypatch.setenv("STUDIO_TTS_CACHE", str(tmp_path / "cache"))
    calls = []

    def fake_tts(model, text, v, style, session):
        calls.append(model)
        if model == "gemini-3.8-flash-tts":
            raise gemini.GeminiError("HTTP 429: Quota exceeded for metric: generate_requests_per_model_per_day, limit: 100")
        return b"\x00\x00" * 24000, 24000, {"output_tokens": 1}

    monkeypatch.setattr(gemini, "tts", fake_tts)
    gv = voice.GeminiVoice(sleep=lambda s: None)
    d = gv.synthesize("こんにちは", "ja", tmp_path / "a.wav")
    assert abs(d - 1.0) < 0.01
    assert calls == ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"]
    gv.synthesize("こんにちは", "ja", tmp_path / "b.wav")           # same text again: the fallback model's result is served from cache
    assert calls == ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"]   # primary is retried first (still over quota), the paid fallback audio is not re-requested
    assert gv.models_used[-1] == "gemini-3.8-flash-lite-tts (cache)"
