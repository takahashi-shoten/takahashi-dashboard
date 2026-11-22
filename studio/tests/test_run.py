import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import run  # noqa: E402


def test_demo_builds_a_mock_video_and_never_claims_publishable(tmp_path):
    rep = run.demo(work_root=tmp_path)
    assert rep["is_mock"] is True and rep["ready_to_publish"] is False
    assert rep["qa_decision"] == "needs_human"      # mock-only QA can never pass
    assert rep["stages"]["voice"]["status"] == "mock" and rep["stages"]["visuals"]["status"] == "mock"
    out = Path(rep["outputs"]["final.mp4"])
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "stream=width,height,codec_type", "-of", "json", str(out)]))
    assert any(s.get("width") == 1920 and s.get("height") == 1080 for s in probe["streams"])
    assert any(s["codec_type"] == "audio" for s in probe["streams"])
    assert Path(rep["outputs"]["thumbnail.png"]).exists() and Path(rep["outputs"]["shorts.mp4"]).exists()
