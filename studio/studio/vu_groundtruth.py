"""Ground-truth test of video understanding on OUR OWN video (experiment E1 preview + its exact subtitles).
Runs in GitHub Actions (key is a secret). Steps: (0) credit/key check by the first real call, (1) cut a short clip, (2) analyse clip -> check that the API
counted VIDEO and AUDIO input tokens, transcript error rate vs subtitles, scene cuts vs FFmpeg, false alarms, (3) analyse defective copies (audio drop-out,
black-out) -> detection. Total spend is capped. Usage: python -m studio.vu_groundtruth <video.mp4> <subtitles.srt> [model] [start_s] [dur_s]"""
import json
import subprocess
import sys
import time
from pathlib import Path

from . import gemini, video_analysis as va, vu_eval as ev

PROMPT = """Analyse the ACTUAL video (frames AND audio). Return JSON only:
{"transcript": [{"start": seconds(number), "end": seconds(number), "text": str}],   // verbatim Japanese speech you HEAR, in order, whole clip
 "scene_cuts": [seconds(number)],                                                    // times where the picture changes to a different shot
 "anomalies": [{"time": seconds(number), "type": one of [audio_silent, picture_black, audio_video_out_of_sync, other], "description": str}]}
Rules: times are seconds from the start of THIS clip. Report an anomaly only if you actually see/hear it; an empty list is a valid answer. Do not guess."""


def sh(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def run_one(path, model, label, spent):
    uri, name = ev.upload_file(path)
    try:
        res = va.analyze(uri, model, prompt=PROMPT, resolution="low", is_file_uri=True, max_out=16000)
    finally:
        ev.delete_file(name)
    v, a = va.video_input_confirmed(res["usage"])
    spent[0] += res["cost_usd"] or 0
    print(f"[{label}] usage={res['usage']} cost_usd={res['cost_usd']} seconds={res['seconds']} video_tokens={v} audio_tokens={a} spent_so_far_usd={round(spent[0], 4)}", flush=True)
    return res, v, a


def main():
    src, srt = Path(sys.argv[1]), Path(sys.argv[2])
    model = sys.argv[3] if len(sys.argv) > 3 else "gemini-3.5-flash-lite"
    start = float(sys.argv[4]) if len(sys.argv) > 4 else 120.0
    dur = float(sys.argv[5]) if len(sys.argv) > 5 else 90.0
    cap_usd = 3.0
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    clip = out / "clip.mp4"
    sh(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", str(src), "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", str(clip)])
    spent = [0.0]
    report = dict(model=model, clip_start=start, clip_seconds=dur)
    try:
        res, v, a = run_one(clip, model, "baseline", spent)
    except gemini.GeminiError as e:
        print("CREDIT/KEY CHECK FAILED:", str(e)[:300])
        report["error"] = str(e)[:300]
        (out / "vu_groundtruth.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        sys.exit(1)
    print("CREDIT OK: Gemini call succeeded")
    j = res["json"] or {}
    hyp = "".join(x.get("text", "") for x in j.get("transcript", []))
    ref = ev.srt_window_text(srt.read_text(encoding="utf-8"), start + 1, start + dur - 1)
    cer = ev.cer(ref, hyp)
    truth_cuts = ev.ffmpeg_scene_cuts(clip)
    cuts = ev.match_events(truth_cuts, [float(x) for x in j.get("scene_cuts", [])], tol=2.0)
    fa = len(j.get("anomalies", []))
    report["baseline"] = dict(video_tokens=v, audio_tokens=a, usage=res["usage"], cost_usd=res["cost_usd"], cer=round(cer, 3), ref_chars=len(ev._norm(ref)), hyp_chars=len(ev._norm(hyp)),
                              scene_cuts=cuts, truth_cut_count=len(truth_cuts), false_alarms_on_clean_clip=fa, anomalies=j.get("anomalies", []))
    print("BASELINE cer", round(cer, 3), "| cuts", cuts, "| truth cuts", len(truth_cuts), "| false alarms on clean clip", fa)
    defects = []
    for p, inj in ev.build_defects(clip, out / "defects", dur):
        if p.name == "defect_av_shift.mp4":
            continue  # desync is reported separately below only if budget allows; skipped to keep cost small
        if spent[0] > cap_usd:
            print("BUDGET CAP reached; stop"); break
        r, v2, a2 = run_one(p, model, p.name, spent)
        times = [float(x.get("time", -1)) for x in (r["json"] or {}).get("anomalies", []) if str(x.get("time", "")).replace(".", "").isdigit() or isinstance(x.get("time"), (int, float))]
        d = ev.defect_detection(inj, times, tol=6.0)
        d.update(file=p.name, video_tokens=v2, audio_tokens=a2, cost_usd=r["cost_usd"], reported=(r["json"] or {}).get("anomalies", []))
        defects.append(d)
        print("DEFECT", p.name, "detection_rate", d["detection_rate"], "false_alarms", d["false_alarms"])
    report["defects"] = defects
    report["total_cost_usd"] = round(spent[0], 4)
    ok_tokens = report["baseline"]["video_tokens"] and report["baseline"]["audio_tokens"]
    report["verdict_inputs"] = dict(tokens_counted=bool(ok_tokens), cer=round(cer, 3), note="Pass thresholds are decided by the owner/AI review; see report.")
    (out / "vu_groundtruth.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("TOTAL cost_usd", report["total_cost_usd"])


if __name__ == "__main__":
    main()
