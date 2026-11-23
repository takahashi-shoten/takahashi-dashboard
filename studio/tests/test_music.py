import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import music  # noqa: E402


def ff(*a):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)


def mean_db(path, start, dur, pre=""):
    af = (pre + "," if pre else "") + "volumedetect"
    r = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(start), "-t", str(dur), "-i", str(path), "-vn", "-af", af,
                        "-f", "null", "-"], capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "mean_volume" in line:
            return float(line.split("mean_volume:")[1].split("dB")[0])
    raise AssertionError(r.stderr)


def streams(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(path)],
                         capture_output=True, text=True).stdout
    return [s["codec_type"] for s in json.loads(out)["streams"]]


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    d = tmp_path_factory.mktemp("v")
    v = d / "final.mp4"
    # 6 s: speech-like 3000 Hz bursts at 1.5-3.5 s only
    ff("-f", "lavfi", "-i", "color=c=black:s=160x90:r=10:d=6", "-f", "lavfi", "-i", "sine=f=3000:r=44100:d=6",
       "-af", "volume='if(between(t,1.5,3.5),0.5,0)':eval=frame", "-c:v", "libx264", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-t", "6", str(v))
    return v


def test_procedural_bed_format_and_duration(tmp_path):
    for kind in ("calm", "warm", "tense"):
        p = music.ProceduralBed(kind).render(5, tmp_path / f"{kind}.wav")
        assert abs(music.probe_duration(p) - 5) < 0.05
        info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate,channels", "-of", "csv=p=0", str(p)],
                              capture_output=True, text=True).stdout.strip()
        assert info == "44100,2"
    assert music.ProceduralBed().describe()["status"] == "done"


def test_procedural_deterministic(tmp_path):
    a = music.ProceduralBed("calm").render(2, tmp_path / "a.wav")
    b = music.ProceduralBed("calm").render(2, tmp_path / "b.wav")
    assert a.read_bytes() == b.read_bytes()


def test_mix_duration_streams_and_ducking(tmp_path, video):
    bed = music.ProceduralBed("warm").render(6, tmp_path / "bed.wav")
    ducked = music.mix_bgm(video, bed, tmp_path / "d.mp4")
    plain = music.mix_bgm(video, bed, tmp_path / "p.mp4", duck=False)
    for o in (ducked, plain):
        assert abs(music.probe_duration(o) - music.probe_duration(video)) < 0.05
        assert streams(o).count("audio") == 1 and streams(o).count("video") == 1
    # Bed partials are all <= 330 Hz; the "speech" is a 3000 Hz sine. Below 400 Hz only the bed is measured.
    low = "lowpass=f=400,lowpass=f=400,lowpass=f=400"
    def drop(path):  # level during speech minus level in a speech-free gap (same windows, so fades/loudnorm cancel in the comparison)
        return mean_db(path, 2.0, 1.4, low) - mean_db(path, 4.0, 0.8, low)
    assert drop(ducked) < drop(plain) - 6          # bed is pushed down while speech plays and recovers in the gap


def _audio_b64(tmp_path, fmt):
    f = tmp_path / ("t." + fmt)
    args = ["-f", "lavfi", "-i", "sine=f=330:d=3:r=24000"]
    args += ["-f", "s16le", "-ac", "1"] if fmt == "pcm" else []
    ff(*args, str(f))
    return base64.b64encode(f.read_bytes()).decode()


class Resp:
    def __init__(self, code, body):
        self.status_code, self._b = code, body

    def json(self):
        return self._b


class Session:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append((url, json))
        return self.replies.pop(0)


def reply(mime, data):
    return Resp(200, {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": mime, "data": data}}]}}],
                      "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 99}})


def test_lyria_pcm(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    s = Session([reply("audio/L16;codec=pcm;rate=24000", _audio_b64(tmp_path, "pcm"))])
    m = music.LyriaMusic(session=s)
    out = m.render(8, tmp_path / "o.wav", prompt="x")  # 3 s clip extended to 8 s
    assert abs(music.probe_duration(out) - 8) < 0.1
    assert m.last_usage["output_tokens"] == 99
    assert s.calls[0][1]["generationConfig"] == {"responseModalities": ["AUDIO"]}
    assert m.describe()["status"] == "done"


def test_lyria_mp3_and_400_retry(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    s = Session([Resp(400, {"error": {"message": "bad param"}}), reply("audio/mpeg", _audio_b64(tmp_path, "mp3"))])
    m = music.LyriaMusic("lyria-3.5", session=s)
    out = m.render(2, tmp_path / "o.wav", prompt="x")
    assert abs(music.probe_duration(out) - 2) < 0.1
    assert len(s.calls) == 2 and "generationConfig" not in s.calls[1][1]
    assert m.last_mime == "audio/mpeg"


def test_lyria_not_connected(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert music.LyriaMusic().describe()["status"] == "not_connected"


def test_add_bgm_fallback_without_key(monkeypatch, tmp_path, video):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (tmp_path / "final.mp4").write_bytes(video.read_bytes())
    r = music.add_bgm(tmp_path, None, None, kind="tense")
    assert r["file"] == "final_bgm.mp4" and r["provider"].startswith("procedural:tense")
    assert abs(r["seconds"] - 6) < 0.1
    assert (tmp_path / "final.mp4").read_bytes() == video.read_bytes()


def test_bgm_prompt():
    p = music.bgm_prompt("history documentary", "en", "calm")
    assert "INSTRUMENTAL" in p and "not imitating any existing song or artist" in p and "strings" in p
    assert "piano" in music.bgm_prompt("calm advice", "ja", "warm")
