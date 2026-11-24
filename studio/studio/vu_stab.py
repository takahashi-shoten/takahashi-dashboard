"""Repeatability / accuracy check on two clips of our own video (transcript-only prompt, defects with time-error scoring, clean-clip false alarms).
Usage: python -m studio.vu_stab <video.mp4> <subtitles.srt> [clip_starts comma-sep] [reps]"""
import json
import statistics
import sys
from pathlib import Path

from . import vu_diag as d, vu_eval as ev

P_TRANSCRIBE = "この動画（音声）の日本語の発言を、聞こえた通りに書き起こしてください。出力は書き起こし本文のみとし、前置き、見出し、説明、注記は一切書かないでください。"
LLM = "gemini-3.8-flash"
TRANSCRIBER = "gemini-3.5-transcribe"


def first_pair(text):
    ts = d.times_in(text)
    return (ts[0], ts[1]) if len(ts) >= 2 else None


def main():
    src, srt = Path(sys.argv[1]), Path(sys.argv[2])
    starts = [float(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "120,600").split(",")]
    reps = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    dur = 60.0
    d.OUT.mkdir(parents=True, exist_ok=True)
    srt_text = srt.read_text(encoding="utf-8")
    summary = []
    for st in starts:
        A, C = d.OUT / f"s{int(st)}_A.mp4", d.OUT / f"s{int(st)}_C.wav"
        d.sh(["ffmpeg", "-y", "-v", "error", "-ss", str(st), "-t", str(dur), "-i", str(src), "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", str(A)])
        d.sh(["ffmpeg", "-y", "-v", "error", "-i", str(A), "-vn", "-ac", "1", "-ar", "16000", str(C)])
        defs = {p.name: (p, inj[0]) for p, inj in ev.build_defects(A, d.OUT / f"defects_s{int(st)}", dur)}
        mute_p, mute_w = defs["defect_mute.mp4"]
        black_p, black_w = defs["defect_blackout.mp4"]
        ref = ev.srt_window_text(srt_text, st + 1, st + dur - 1)
        up = {k: d.upload(p, m) for k, p, m in [("A", A, "video/mp4"), ("C", C, "audio/wav"), ("MUTE", mute_p, "video/mp4"), ("BLACK", black_p, "video/mp4")]}
        row = dict(clip_start=st, ref_chars=len(ev._norm(ref)))
        cer_a, cer_c, cer_t = [], [], []
        mute_ok, black_ok, mute_err, black_err = [], [], [], []
        fa_s, fa_b = 0, 0
        for i in range(reps):
            if d.SPENT[0] > 3.0:
                print("BUDGET CAP"); break
            r = d.gen(LLM, up["A"][0], "video/mp4", P_TRANSCRIBE, f"{LLM}|s{int(st)}|A_tr|{i}")
            cer_a.append(ev.cer(ref, r["text"]))
            r = d.gen(LLM, up["C"][0], "audio/wav", P_TRANSCRIBE, f"{LLM}|s{int(st)}|C_tr|{i}")
            cer_c.append(ev.cer(ref, r["text"]))
            r = d.gen(TRANSCRIBER, up["C"][0], "audio/wav", P_TRANSCRIBE, f"{TRANSCRIBER}|s{int(st)}|C_tr|{i}")
            cer_t.append(ev.cer(ref, r["text"]) if r["text"] else 1.0)
            r = d.gen(LLM, up["MUTE"][0], "video/mp4", d.P_SILENT, f"{LLM}|s{int(st)}|MUTE|{i}")
            pr = first_pair(r["text"])
            mute_ok.append(bool(pr) and abs(pr[0] - mute_w["start"]) <= 2 and abs(pr[1] - mute_w["end"]) <= 2)
            mute_err.append(None if not pr else [round(pr[0] - mute_w["start"], 1), round(pr[1] - mute_w["end"], 1)])
            r = d.gen(LLM, up["BLACK"][0], "video/mp4", d.P_BLACK, f"{LLM}|s{int(st)}|BLACK|{i}")
            pr = first_pair(r["text"])
            black_ok.append(bool(pr) and abs(pr[0] - black_w["start"]) <= 2 and abs(pr[1] - black_w["end"]) <= 2)
            black_err.append(None if not pr else [round(pr[0] - black_w["start"], 1), round(pr[1] - black_w["end"], 1)])
            r = d.gen(LLM, up["A"][0], "video/mp4", d.P_SILENT, f"{LLM}|s{int(st)}|A_clean_silent|{i}")
            fa_s += bool(first_pair(r["text"]))
            r = d.gen(LLM, up["A"][0], "video/mp4", d.P_BLACK, f"{LLM}|s{int(st)}|A_clean_black|{i}")
            fa_b += bool(first_pair(r["text"]))
        f = lambda xs: dict(values=[round(x, 3) for x in xs], mean=round(statistics.mean(xs), 3) if xs else None, max=round(max(xs), 3) if xs else None)
        row.update(cer_llm_mp4=f(cer_a), cer_llm_wav=f(cer_c), cer_transcribe_wav=f(cer_t), mute_pass=mute_ok, mute_err=mute_err, black_pass=black_ok, black_err=black_err,
                   clean_false_alarms=dict(silent=fa_s, black=fa_b, trials=reps))
        summary.append(row)
        print("STAB", json.dumps(row, ensure_ascii=False), flush=True)
    (d.OUT / "vu_stab.json").write_text(json.dumps(dict(ran_at=d.now(), summary=summary, total_cost_usd=round(d.SPENT[0], 4), log=d.LOG), ensure_ascii=False, indent=1), encoding="utf-8")
    print("TOTAL cost_usd", round(d.SPENT[0], 4))


if __name__ == "__main__":
    main()
