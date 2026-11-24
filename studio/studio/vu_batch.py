"""Quick one-pass marketing look at several videos of ONE channel, found by title keywords (YouTube Data API), analysed from real picture+sound (YouTube URL input).
Usage: python -m studio.vu_batch <channel_seed_video_id> <model> <keyword1|keyword2|...>   Spend capped; 503s are retried (never turned into success)."""
import json
import sys
import time
from pathlib import Path

from . import vu_diag as d
from .vu_marketing import RULES, yt

QUICK = RULES + ("課題: この動画を、次の項目で簡潔に（全体で2,500字程度）分析する。\n"
                 "1) 動画の長さ（最後の時刻）と、冒頭0〜10秒の発言（短く引用）。\n"
                 "2) 章立て（開始時刻・内容）。\n"
                 "3) 動画の中で提案される具体的な行動・習慣・考え方（時刻付き、短く引用）。\n"
                 "4) 4種類の価値（情報的／実用的／感情的／行動的）を、それぞれ観察された事実（時刻付き）と解釈を分けて2〜3行ずつ。\n"
                 "5) 話術・声（抑揚・間・テンポ）、信頼形成、キャラクター（登場時刻・役割）、コピーライティングの特徴。\n"
                 "6) 販売導線・行動の呼びかけ（時刻付き）。確認できなければ「確認できない」。\n"
                 "7) 視聴者の心理がどう動くか（段階ごと、根拠の時刻付き）。")


def gen_retry(model, uri, prompt, label, tries=4):
    for i in range(tries):
        r = d.gen(model, uri, None, prompt, label, resolution="MEDIA_RESOLUTION_LOW", max_out=12000)
        if r["http_status"] == 200 and r["text"]:
            return r
        if r["http_status"] not in (429, 500, 503, 504):
            return r
        print(f"RETRY {label} after HTTP {r['http_status']} ({i + 1}/{tries})", flush=True)
        time.sleep(20 * (i + 1))
    return r


def main():
    seed, model = sys.argv[1], sys.argv[2]
    kws = sys.argv[3].split("|")
    ch = yt("videos", part="snippet", id=seed)["items"][0]["snippet"]["channelId"]
    uploads = "UU" + ch[2:]
    vids, tok = [], None
    while True:
        r = yt("playlistItems", part="snippet", playlistId=uploads, maxResults=50, **({"pageToken": tok} if tok else {}))
        vids += [(i["snippet"]["resourceId"]["videoId"], i["snippet"]["title"]) for i in r.get("items", [])]
        tok = r.get("nextPageToken")
        if not tok:
            break
    print("CHANNEL uploads found:", len(vids), flush=True)
    base = d.OUT.parent / "marketing"
    for kw in kws:
        hits = [(v, t) for v, t in vids if kw in t]
        print(f"KEYWORD {kw!r} -> {hits}", flush=True)
        if len(hits) != 1:
            print("SKIP (not exactly one match; cannot be sure which video)", kw)
            continue
        vid, title = hits[0]
        if d.SPENT[0] > 1.5:
            print("BUDGET CAP"); break
        st = yt("videos", part="snippet,contentDetails,statistics", id=vid)["items"][0]
        out = base / vid
        out.mkdir(parents=True, exist_ok=True)
        meta = dict(video_id=vid, title=title, published=st["snippet"]["publishedAt"], duration=st["contentDetails"]["duration"], views=st["statistics"].get("viewCount"),
                    likes=st["statistics"].get("likeCount"), comments=st["statistics"].get("commentCount"), fetched_at=d.now())
        (out / "meta.json").write_text(json.dumps(dict(meta=meta), ensure_ascii=False, indent=1), encoding="utf-8")
        print("META", json.dumps(meta, ensure_ascii=False), flush=True)
        r = gen_retry(model, f"https://www.youtube.com/watch?v={vid}", QUICK, f"{model}|{vid}|quick")
        (out / "quick.md").write_text(r["text"] or f"(failed: HTTP {r['http_status']})", encoding="utf-8")
        print(f"QUICK {vid} http={r['http_status']} finish={r['finishReason']} usage={r['usage']} cost={r['cost_usd']} chars={len(r['text'])}", flush=True)
    (base / "batch_raw_log.json").write_text(json.dumps(d.LOG, ensure_ascii=False, indent=1), encoding="utf-8")
    print("TOTAL cost_usd", round(d.SPENT[0], 4))


if __name__ == "__main__":
    main()
