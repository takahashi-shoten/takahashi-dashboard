import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import ledger, produce, qa, storyboard, visuals, voice, script  # noqa: E402

SCRIPT = {
    "title_options": ["MOCKタイトル"], "original_angle": "a", "hook": "h", "description": "d", "tags": ["t"], "fact_claims_to_verify": [],
    "ai_disclosure_needed": True,
    "sections": [{"heading": "a", "narration": "これは最初の文です。次の文も続きます。", "visual_prompt": "v", "seconds": 5},
                 {"heading": "b", "narration": "二つ目の場面です。短い文章です。", "visual_prompt": "v", "seconds": 5}]}


def test_orchestration_with_mocks_is_marked_mock_and_not_publishable(tmp_path, monkeypatch):
    con = ledger.connect(":memory:")
    pid = con.execute("INSERT INTO projects(genre,lang,platform,title,status,brief_json,created_at) VALUES('g','ja','youtube','t','brief','{}',?)",
                      (ledger.now(),)).lastrowid
    con.commit()
    monkeypatch.setattr(script, "write_script", lambda *a, **k: json.loads(json.dumps(SCRIPT)))

    def fake_storyboard(con_, client, project_id, d, lang, **k):
        beats = []
        for si, sec in enumerate(SCRIPT["sections"], 1):
            for bi, text in enumerate(storyboard.split_beats(sec["narration"], lang, 12), 1):
                beats.append({"section": si, "beat": bi, "chars": len(text), "narration": text, "shot": "environment", "cast_ids": [],
                              "visual_prompt": "an empty cafe interior", "replaced": False})
        sb = {"style_bible": {"look": "photo", "cast": [], "locations": []}, "beats": beats}
        (Path(d) / "storyboard.json").write_text(json.dumps(sb), encoding="utf-8")
        return sb
    monkeypatch.setattr(storyboard, "make_storyboard", fake_storyboard)
    rep = produce.produce(con, pid, "ja", client=None, voice_provider=voice.MockVoice(), image_provider=visuals.MockImage(),
                          reviewers=[qa.MockReviewer()], work_root=tmp_path)
    assert rep["is_mock"] is True and rep["ready_to_publish"] is False
    assert rep["qa"]["decision"] == "needs_human"
    assert set(rep["files"]) >= {"final.mp4", "preview.mp4", "thumbnail.png", "final.srt", "report.json".replace("report.json", "qa.json")}
    assert rep["final_seconds"] > 0 and (tmp_path / str(pid) / "report.json").exists()
    assert rep["stages"]["voice"]["status"] == "mock" and rep["stages"]["visuals"]["status"] == "mock"


def test_blocked_qa_stops_before_paying_for_assets(tmp_path, monkeypatch):
    con = ledger.connect(":memory:")
    pid = con.execute("INSERT INTO projects(genre,lang,platform,title,status,brief_json,created_at) VALUES('g','ja','youtube','t','brief','{}',?)",
                      (ledger.now(),)).lastrowid
    con.commit()
    bad = json.loads(json.dumps(SCRIPT)); bad["sections"][0]["narration"] = "必ず治る奇跡の方法です。"
    monkeypatch.setattr(script, "write_script", lambda *a, **k: bad)
    monkeypatch.setattr(storyboard, "make_storyboard", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not be called")))
    rep = produce.produce(con, pid, "ja", client=None, voice_provider=voice.MockVoice(), image_provider=visuals.MockImage(),
                          reviewers=[qa.MockReviewer()], work_root=tmp_path)
    assert rep["qa"]["decision"] == "blocked" and "no paid asset" in rep["stopped"]


def test_gemini_voice_writes_wav_and_retries_on_429(tmp_path, monkeypatch):
    import base64
    from types import SimpleNamespace as NS
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    pcm = b"\x00\x00" * 24000     # 1 s at 24 kHz
    good = {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "audio/L16;codec=pcm;rate=24000", "data": base64.b64encode(pcm).decode()}}]}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 25}}

    class S:
        def __init__(self):
            self.n = 0

        def post(self, url, json=None, headers=None, timeout=None):
            self.n += 1
            if self.n == 1:
                return NS(status_code=429, json=lambda: {"error": {"message": "slow down"}})
            return NS(status_code=200, json=lambda: good)
    s = S()
    v = voice.GeminiVoice(session=s, sleep=lambda x: None)
    sec = v.synthesize("テストです。", "ja", tmp_path / "a.wav")
    assert abs(sec - 1.0) < 0.01 and s.n == 2 and (tmp_path / "a.wav").exists() and v.usage[0]["output_tokens"] == 25
