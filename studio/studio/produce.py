"""One real production run: brief -> script -> QA (+ one revision) -> storyboard -> voice -> beat images -> edit -> report.

`produce_short` is the vertical Shorts variant (short.mp4, <= 59 s).
Writes `report.json` (stage status, measured costs, durations, outputs). Anything produced with a mock provider is marked as such, and
`ready_to_publish` is only True if every stage is real, QA passed with two independent vendors AND the owner approved (ledger approvals).
Nothing is ever published by this module.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import brief, edit, ledger, pipeline, qa, script, storyboard, visuals, voice
from .run import project_dir

IMAGE_USD_PER_M_TOKENS = {"gemini-3.1-flash-image": 60.0, "gemini-3.1-flash-lite-image": 30.0}   # Google list price per 1M image output tokens (flash image); other models: unknown -> not priced


def _duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], text=True)
    return float(out.strip())


def _needs_fix(res):
    return any(r["verdict"] == "revise" for r in res["reviews"]) or bool(res["unverified_claims"])


def _record_qa(con, project_id, rep, res, stage):
    for r in res["reviews"]:
        u = r.get("usage")
        if u:
            m = r.get("model")
            if m in ledger.PRICES:
                ledger.record_cost(con, project_id, "qa", "anthropic", m, u["input_tokens"], u["output_tokens"])
            else:
                ledger.record_usage(con, project_id, "qa", r["reviewer"], m or "?", u["input_tokens"], u["output_tokens"])
    rep["qa"] = {"decision": res["decision"], "reasons": res["reasons"], "reviewers": [r["reviewer"] for r in res["reviews"]],
                 "issues": [i for r in res["reviews"] for i in r["issues"]][:12], "unverified": res["unverified_claims"][:12]}
    real_reviewers = {r["reviewer"].split("_")[0] for r in res["reviews"] if r["reviewer"] != "mock"}
    stage("qa", "real" if len(real_reviewers) >= 2 else "mock", f"decision={res['decision']}")


def image_cost(provider):
    """(output tokens, USD estimate or None) over every model the provider used; unknown-model tokens make the USD None."""
    parts = getattr(provider, "parts", None) or [(getattr(provider, "model", ""), getattr(provider, "usage", []))]
    tok, usd = 0, 0.0
    for model, usage in parts:
        t = sum(int(u.get("output_tokens", 0)) for u in usage)
        tok += t
        price = IMAGE_USD_PER_M_TOKENS.get(model)
        if price is None:
            if t:
                return tok, None
        else:
            usd += t * price / 1e6
    return tok, usd


def produce(con, project_id, lang, client, voice_provider, image_provider, reviewers, target_seconds=480, work_root=None, revise_once=True):
    d = (Path(work_root) / str(project_id)) if work_root else project_dir(project_id)
    d.mkdir(parents=True, exist_ok=True)
    rate = getattr(voice_provider, "chars_per_sec", {}).get(lang) if hasattr(voice_provider, "chars_per_sec") else None
    rep = {"project_id": project_id, "lang": lang, "stages": {}, "files": {}}

    def stage(name, status, note=""):
        rep["stages"][name] = {"status": status, "note": note}
        ledger.add_step(con, project_id, name, "done" if status == "real" else status, None, note)

    data = script.write_script(con, client, project_id, target_seconds, chars_per_sec=rate)
    if data is None:
        raise RuntimeError("script generation was refused by the model")
    (d / "script.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    stage("script", "real", f"narration_chars={script.narration_chars(data)}")

    titles = None
    res = qa.run_qa(d, lang, reviewers, reference_titles=titles)
    if revise_once and res["decision"] != "blocked" and _needs_fix(res):
        issues = [i for r in res["reviews"] for i in r["issues"]]
        data = script.revise_with_feedback(con, client, project_id, data, issues, res["unverified_claims"], lang, chars_per_sec=rate)
        (d / "script.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        res = qa.run_qa(d, lang, reviewers, reference_titles=titles)
        stage("script_revision", "real", "revised after QA feedback")
    _record_qa(con, project_id, rep, res, stage)
    if res["decision"] == "blocked":
        rep["stopped"] = "QA blocked the script; no paid asset was generated"
        (d / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        return rep

    sb = storyboard.make_storyboard(con, client, project_id, d, lang)
    stage("storyboard", "real", f"beats={len(sb['beats'])}")
    vd = voice_provider.describe()
    durations = voice.render_voice(d, voice_provider, lang)
    stage("voice", "real" if vd["status"] == "done" else "mock", vd.get("note", ""))
    for u in getattr(voice_provider, "usage", []):
        ledger.record_usage(con, project_id, "voice", "gemini", getattr(voice_provider, "model", "tts"), u["input_tokens"], u["output_tokens"])
    imd = image_provider.describe()
    paths = storyboard.render_beats(d, image_provider)
    stage("visuals", "real" if imd["status"] == "done" else "mock", f"{len(paths)} images; {imd.get('note', '')}")
    model = getattr(image_provider, "model", "")
    tok, usd = image_cost(image_provider)                                                    # thread-safe per-image usage
    ledger.record_usage(con, project_id, "images", "gemini", model or "?", 0, tok, usd)

    edit.assemble(d)
    edit.make_shorts(d)
    edit.make_thumbnail(d, data["title_options"][0], data.get("thumbnail_text"))
    edit.make_preview(d)
    stage("edit", "real", "ffmpeg assembly")

    rep["title_options"] = data["title_options"]
    rep["ai_disclosure_needed"] = data["ai_disclosure_needed"]
    rep["voice_credit"] = "VOICEVOX:..." if isinstance(voice_provider, voice.VoicevoxVoice) else f"Gemini TTS voice={getattr(voice_provider, 'voice', '?')} (synthetic voice)"
    rep["narration_seconds"] = round(sum(durations.values()), 1)
    rep["final_seconds"] = round(_duration(d / "final.mp4"), 1)
    rep["costs"] = [dict(r) for r in con.execute("SELECT stage, provider, model, input_tokens, output_tokens, usd FROM costs WHERE project_id=?", (project_id,))]
    rep["measured_usd_claude"] = round(sum(r["usd"] or 0 for r in rep["costs"] if r["provider"] == "anthropic"), 4)
    rep["image_output_tokens"] = tok
    rep["image_usd_estimate"] = None if usd is None else round(usd, 4)
    rep["is_mock"] = any(s["status"] == "mock" for s in rep["stages"].values())
    rep["ready_to_publish"] = (not rep["is_mock"]) and res["decision"] == "pass" and pipeline.is_publish_approved(con, project_id)
    rep["files"] = {n: str(d / n) for n in ("final.mp4", "preview.mp4", "shorts.mp4", "thumbnail.png", "final.srt", "script.json", "storyboard.json", "qa.json")
                    if (d / n).exists()}
    (d / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return rep


def produce_short(con, project_id, lang, client, voice_provider, image_provider, reviewers, target_seconds=50, work_root=None, revise_once=True):
    """Like `produce` but makes a vertical YouTube Short (short.mp4, 1080x1920, <= 59 s): one idea, 6-9 beats, one image per beat."""
    d = (Path(work_root) / str(project_id)) if work_root else project_dir(project_id)
    d.mkdir(parents=True, exist_ok=True)
    rate = getattr(voice_provider, "short_chars_per_sec", getattr(voice_provider, "chars_per_sec", {})).get(lang) if hasattr(voice_provider, "chars_per_sec") else None
    rep = {"project_id": project_id, "lang": lang, "format": "short", "stages": {}, "files": {}}

    def stage(name, status, note=""):
        rep["stages"][name] = {"status": status, "note": note}
        ledger.add_step(con, project_id, name, "done" if status == "real" else status, None, note)

    data = script.write_short(con, client, project_id, target_seconds, chars_per_sec=rate)
    if data is None:
        raise RuntimeError("script generation was refused by the model")
    (d / "script.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    stage("script", "real", f"short narration_chars={script.narration_chars(data)} beats={len(data['sections'])}")

    res = qa.run_qa(d, lang, reviewers, short=True)
    if revise_once and res["decision"] != "blocked" and _needs_fix(res):
        issues = [i for r in res["reviews"] for i in r["issues"]]
        data = script.revise_with_feedback(con, client, project_id, data, issues, res["unverified_claims"], lang, chars_per_sec=rate, short=True)
        (d / "script.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        res = qa.run_qa(d, lang, reviewers, short=True)
        stage("script_revision", "real", "revised after QA feedback")
    _record_qa(con, project_id, rep, res, stage)
    if res["decision"] == "blocked":
        rep["stopped"] = "QA blocked the script; no paid asset was generated"
        (d / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        return rep

    sb = storyboard.make_storyboard(con, client, project_id, d, lang, beats_per_section=1, vertical=True)
    stage("storyboard", "real", f"beats={len(sb['beats'])} (one image per narration beat)")
    vd = voice_provider.describe()
    durations = voice.render_voice(d, voice_provider, lang)
    durations = voice.fit_to_total(d, durations, 57.5)      # safety net: up to x1.3 speed-up, else ValueError (shorten the script)
    stage("voice", "real" if vd["status"] == "done" else "mock", vd.get("note", ""))
    for u in getattr(voice_provider, "usage", []):
        ledger.record_usage(con, project_id, "voice", "gemini", getattr(voice_provider, "model", "tts"), u["input_tokens"], u["output_tokens"])
    imd = image_provider.describe()
    paths = storyboard.render_beats(d, image_provider, size=edit.SHORT_SIZE)
    stage("visuals", "real" if imd["status"] == "done" else "mock", f"{len(paths)} vertical images; {imd.get('note', '')}")
    model = getattr(image_provider, "model", "")
    tok, usd = image_cost(image_provider)
    ledger.record_usage(con, project_id, "images", "gemini", model or "?", 0, tok, usd)

    edit.assemble_short(d)
    stage("edit", "real", "ffmpeg vertical assembly with burned-in captions")

    rep["title_options"] = data["title_options"]
    rep["ai_disclosure_needed"] = data["ai_disclosure_needed"]
    rep["voice_credit"] = "VOICEVOX:..." if isinstance(voice_provider, voice.VoicevoxVoice) else f"Gemini TTS voice={getattr(voice_provider, 'voice', '?')} (synthetic voice)"
    rep["narration_seconds"] = round(sum(durations.values()), 1)
    rep["final_seconds"] = round(_duration(d / "short.mp4"), 1)
    rep["costs"] = [dict(r) for r in con.execute("SELECT stage, provider, model, input_tokens, output_tokens, usd FROM costs WHERE project_id=?", (project_id,))]
    rep["measured_usd_claude"] = round(sum(r["usd"] or 0 for r in rep["costs"] if r["provider"] == "anthropic"), 4)
    rep["image_output_tokens"] = tok
    rep["image_usd_estimate"] = None if usd is None else round(usd, 4)
    rep["is_mock"] = any(s["status"] == "mock" for s in rep["stages"].values())
    rep["ready_to_publish"] = (not rep["is_mock"]) and res["decision"] == "pass" and pipeline.is_publish_approved(con, project_id)
    rep["files"] = {n: str(d / n) for n in ("short.mp4", "short.ass", "script.json", "storyboard.json", "qa.json") if (d / n).exists()}
    (d / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return rep


def main(argv=None):
    import anthropic
    ap = argparse.ArgumentParser(prog="studio.produce")
    ap.add_argument("--ytr-db", required=True)
    ap.add_argument("--genre", required=True)
    ap.add_argument("--lang", default="ja")
    ap.add_argument("--voice", default="Iapetus")
    ap.add_argument("--format", choices=["long", "short"], default="long", help="long: 16:9 video; short: vertical 9:16 Short (45-60 s)")
    ap.add_argument("--target-seconds", type=int, default=None, help="default 480 (long) / 50 (short)")
    ap.add_argument("--topic", default="", help="optional topic/angle hint passed to the script writer")
    ap.add_argument("--audience", default="40-60代の日本人男性")
    ap.add_argument("--style", default="photo", choices=["photo", "manga", "illustration"], help="visual style of the generated images")
    a = ap.parse_args(argv)
    os.environ["STUDIO_VISUAL_STYLE"] = a.style
    con = ledger.connect(":memory:")
    b = brief.make_brief(a.ytr_db, a.genre, a.lang, audience=a.audience)
    if a.topic:
        b["topic"] = a.topic
    pid = brief.create_project(con, b)
    client = anthropic.Anthropic()
    run = produce_short if a.format == "short" else produce
    vstyle = voice.GeminiVoice.STYLE_SHORT.get(a.lang) if a.format == "short" else None     # brisk pace for Shorts
    rep = run(con, pid, a.lang, client, voice.GeminiVoice(voice=a.voice, style=vstyle), (visuals.HybridImage(style=a.style, max_share=1.0 if a.format == "short" else 0.3) if os.environ.get("STUDIO_IMAGE_MODE", "hybrid") == "hybrid" else visuals.GeminiImage(style=a.style)),
              [qa.WebClaudeReviewer(client), qa.GeminiReviewer()], a.target_seconds or (50 if a.format == "short" else 480))
    short = {k: rep.get(k) for k in ("project_id", "title_options", "narration_seconds", "final_seconds", "measured_usd_claude",
                                    "image_output_tokens", "image_usd_estimate", "is_mock", "ready_to_publish", "voice_credit", "stopped")}
    print(json.dumps(short, ensure_ascii=False, indent=1))
    print("stages:", {k: v["status"] for k, v in rep["stages"].items()})
    print("qa:", json.dumps(rep.get("qa"), ensure_ascii=False)[:1500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
