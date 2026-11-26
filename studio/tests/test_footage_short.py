import shutil
import subprocess

import pytest

from studio import footage_short

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def _clip(path, w, h, secs):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0x884488:s={w}x{h}:r=30:d={secs}", "-pix_fmt", "yuv420p", str(path)], check=True)


def _probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,codec_name:format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout
    return out


def test_landscape_and_portrait_clips_become_1080x1920_with_cta(tmp_path):
    _clip(tmp_path / "a.mp4", 1920, 1080, 4)
    _clip(tmp_path / "b.mp4", 1080, 1920, 4)
    out = footage_short.build({"clips": [{"path": str(tmp_path / "a.mp4"), "start": 0, "end": 3}, {"path": str(tmp_path / "b.mp4"), "start": 0, "end": 3}],
                               "telops": [{"at": 0.2, "dur": 2, "text": "袴の帯を結びます"}], "cta": "ご予約はDMかお電話へ", "cta_seconds": 2, "out": str(tmp_path / "o.mp4")})
    info = _probe(out)
    assert "h264,1080,1920" in info
    assert abs(float(info.strip().splitlines()[-1]) - 8.0) < 0.5


def test_too_long_is_rejected(tmp_path):
    _clip(tmp_path / "a.mp4", 1080, 1920, 3)
    with pytest.raises(ValueError):
        footage_short.build({"clips": [{"path": str(tmp_path / "a.mp4"), "start": 0, "end": 3, "speed": 0.04}], "cta": "x", "out": str(tmp_path / "o.mp4")})
