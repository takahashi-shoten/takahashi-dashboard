"""End-to-end orchestration: script -> voice -> visuals -> edit -> QA, with honest per-stage status.

A run that used any mock provider is reported as `mock` and can never be published: `qa.run_qa` never
returns "pass" without two real reviewers, and `ready_to_publish` additionally requires every stage to be real.
"""
import json
from pathlib import Path

from . import edit, ledger, pipeline, qa, script as script_mod, visuals, voice
from .errors import NotConnected

WORK = Path(__file__).resolve().parent.parent / "work"

SAMPLE_SCRIPT = {
    "title_options": ["MOCK: サンプル動画"], "original_angle": "pipeline smoke test", "hook": "これは動作確認用のサンプルです。",
    "sections": [
        {"heading": "導入", "narration": "これは動作確認用のサンプルです。実際の企画ではありません。", "visual_prompt": "abstract blue gradient, simple shapes", "seconds": 8},
        {"heading": "本編", "narration": "音声は無音、映像は仮の画像で作られています。", "visual_prompt": "abstract green gradient, simple shapes", "seconds": 8}],
    "description": "pipeline smoke test (mock)", "tags": ["mock"], "fact_claims_to_verify": [], "ai_disclosure_needed": True,
}


def project_dir(project_id) -> Path:
    d = WORK / str(project_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def build_video(con, project_id, lang, voice_provider, image_provider, reviewers, client=None, work_root=None):
    """Runs every stage. Returns a report dict; each stage is also stored in the ledger."""
    d = (Path(work_root) / str(project_id)) if work_root else project_dir(project_id)
    d.mkdir(parents=True, exist_ok=True)
    report = {"project_id": project_id, "stages": {}}

    def stage(name, status, note=""):
        report["stages"][name] = {"status": status, "note": note}
        ledger.add_step(con, project_id, name, "done" if status == "real" else status, None, note)

    sp = d / "script.json"
    if not sp.exists():
        if client is None:
            raise NotConnected("no script.json and no Claude client: set ANTHROPIC_API_KEY")
        data = script_mod.write_script(con, client, project_id)
        if data is None:
            raise RuntimeError("script generation refused by the model")
        sp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    stage("script", "real" if client is not None else "mock", "script.json present")

    vd, im = voice_provider.describe(), image_provider.describe()
    voice.render_voice(d, voice_provider, lang)
    stage("voice", "real" if vd["status"] == "done" else "mock", vd.get("note", ""))
    visuals.render_visuals(d, image_provider)
    stage("visuals", "real" if im["status"] == "done" else "mock", im.get("note", ""))

    title = json.loads(sp.read_text(encoding="utf-8"))["title_options"][0]
    edit.assemble(d)
    edit.make_shorts(d)
    edit.make_thumbnail(d, title)
    stage("edit", "real", "ffmpeg assembly (deterministic)")

    result = qa.run_qa(d, lang, reviewers)
    real_reviewers = sum(1 for r in result["reviews"] if r.get("reviewer") not in (None, "mock"))
    stage("qa", "real" if real_reviewers >= 2 else "mock", f"decision={result['decision']}")
    report["qa_decision"] = result["decision"]
    report["is_mock"] = any(s["status"] == "mock" for s in report["stages"].values())
    report["ready_to_publish"] = (not report["is_mock"]) and result["decision"] == "pass" and pipeline.is_publish_approved(con, project_id)
    report["outputs"] = {n: str(d / n) for n in ("final.mp4", "shorts.mp4", "thumbnail.png", "final.srt", "qa.json") if (d / n).exists()}
    return report


def demo(work_root=None):
    """Smoke test with mock providers and a built-in sample script. Output is clearly mock."""
    con = ledger.connect(":memory:")
    pid = con.execute("INSERT INTO projects(genre,lang,platform,title,status,brief_json,created_at) VALUES('demo','ja','youtube','MOCK','brief','{}',?)",
                      (ledger.now(),)).lastrowid
    con.commit()
    root = Path(work_root) if work_root else WORK
    (root / str(pid)).mkdir(parents=True, exist_ok=True)
    (root / str(pid) / "script.json").write_text(json.dumps(SAMPLE_SCRIPT, ensure_ascii=False), encoding="utf-8")
    return build_video(con, pid, "ja", voice.MockVoice(), visuals.MockImage(), [qa.MockReviewer()], work_root=root)
