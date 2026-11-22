"""Thumbnail visual-style comparison: hits vs. baseline videos of a genre.

Read-only analysis of data already collected. Thumbnails are fetched from the public
i.ytimg.com CDN (no YouTube API quota) and classified with Claude Haiku. Only the
resulting categorical features are stored.

NOTE (API terms): thumbnail image bytes are kept in memory only. They are NEVER written
to disk and never persisted anywhere (DB, report, logs). Do not add caching of the bytes.
"""
import base64
import json
import math
import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from . import config
from .util import days_since, iso, utcnow

MODEL = "claude-haiku-5-5"
# USD per 1M tokens (input, output). Anthropic list price, prompts up to 100K tokens, cached 2026-11
PRICE = {"claude-haiku-5-5": (0.10, 0.50)}

THUMB_URL = "https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
FETCH_TIMEOUT = 15
MIN_GROUP = 20          # below this a group is "insufficient data"
BASELINE_SOURCE = {}    # genre -> description of where the baseline group came from (shown in the report)
MIN_BASE_COUNT = 3      # baseline count needed for a value's lift
BASELINE_MIN_AGE_DAYS = 14
MAX_WORKERS = 4

ENUMS = {
    "medium": ["photo", "illustration_2d", "render_3d", "anime", "screenshot", "collage", "stock_look", "other"],
    "ai_look": ["likely", "unlikely", "unclear"],
    "mood": ["dark_moody", "bright_light", "neutral"],
    "palette": ["warm", "cool", "neutral", "high_contrast", "monochrome"],
    "subject": ["face_closeup", "two_people", "group", "object", "landscape_scene", "text_only",
                "map_or_diagram", "other"],
    "text_overlay": ["none", "small", "large"],
    "emotion": ["none", "neutral", "surprised", "serious", "happy", "sad"],
}
SCHEMA = {
    "type": "object",
    "properties": {**{k: {"type": "string", "enum": v} for k, v in ENUMS.items()},
                   "face_present": {"type": "boolean"}},
    "required": [*ENUMS, "face_present"],
    "additionalProperties": False,
}
ATTRS = [*ENUMS, "face_present"]
LABELS = {"medium": "表現媒体", "ai_look": "AIっぽさ", "mood": "雰囲気", "palette": "配色", "subject": "被写体",
          "face_present": "顔の有無", "text_overlay": "文字オーバーレイ", "emotion": "表情"}
PROMPT = ("Classify this YouTube thumbnail strictly by what is visible. Judge ai_look only from visual "
          "cues (likely / unlikely / unclear). Return JSON matching the schema.")

DDL = """CREATE TABLE IF NOT EXISTS thumb_features(
  video_id TEXT PRIMARY KEY, genre TEXT, grp TEXT, model TEXT, features_json TEXT, classified_at TEXT)"""


class MissingApiKey(RuntimeError):
    pass


# ---------------------------------------------------------------- selection
def select_groups(con, genre, limit=40, now=None, seed=0):
    """Return (hits, baseline) lists of video_id. Hits: top by views/day; baseline: seeded random sample."""
    now = now or utcnow()
    since = iso(now - timedelta(days=config.WINDOW_DAYS))
    rows = con.execute("""SELECT DISTINCT v.video_id, v.published_at, v.view_count FROM v_latest v
        JOIN discoveries d ON d.video_id=v.video_id JOIN topics t ON t.topic_id=d.topic_id
        WHERE t.genre=? AND COALESCE(v.category_id,'')!=? AND v.published_at>=? AND v.view_count>=?
          AND v.unavailable_at IS NULL""",
                       (genre, config.MUSIC_CATEGORY_ID, since, config.MIN_VIEWS)).fetchall()
    ranked = sorted(rows, key=lambda r: (-r["view_count"] / days_since(r["published_at"], now), r["video_id"]))
    hits = [r["video_id"] for r in ranked[:limit]]
    cut = iso(now - timedelta(days=BASELINE_MIN_AGE_DAYS))
    base = sorted({r[0] for r in con.execute("""SELECT v.video_id FROM v_latest v
        JOIN date_samples s ON s.video_id=v.video_id JOIN topics t ON t.topic_id=s.topic_id
        WHERE t.genre=? AND COALESCE(v.category_id,'')!=? AND v.published_at<=?
          AND v.unavailable_at IS NULL""", (genre, config.MUSIC_CATEGORY_ID, cut))} - set(hits))
    random.Random(f"{seed}:{genre}").shuffle(base)
    BASELINE_SOURCE[genre] = "新着順の標本(date_samples)"
    if len(base) < MIN_GROUP:
        # Fallback when the genre has too few date-sampled videos: non-hit uploads of the channels that produced this genre's hits
        # (same channels, same period). It controls for the channel, but is NOT a random sample of the genre: stated in the report.
        extra = sorted({r[0] for r in con.execute("""SELECT v2.video_id FROM v_latest v2
            WHERE v2.channel_id IN (SELECT DISTINCT v.channel_id FROM v_latest v JOIN discoveries d ON d.video_id=v.video_id
                                    JOIN topics t ON t.topic_id=d.topic_id WHERE t.genre=? AND v.view_count>=?)
              AND COALESCE(v2.category_id,'')!=? AND v2.published_at>=? AND v2.published_at<=? AND v2.view_count<?
              AND v2.unavailable_at IS NULL""", (genre, config.MIN_VIEWS, config.MUSIC_CATEGORY_ID, since, cut, config.MIN_VIEWS))}
            - set(hits) - set(base))
        random.Random(f"{seed}:{genre}:fb").shuffle(extra)
        base = base + extra
        if extra:
            BASELINE_SOURCE[genre] = "同じチャンネルの、ヒットに届かなかった投稿(ランダム標本ではありません)"
    return hits, base[:limit]


# ---------------------------------------------------------------- fetch / classify
def fetch_thumbnail(session, video_id):
    """Bytes of the thumbnail or None. In memory only; never written anywhere."""
    try:
        r = session.get(THUMB_URL.format(video_id=video_id), timeout=FETCH_TIMEOUT)
        if r.status_code != 200 or not r.content:
            return None
        return r.content
    except Exception:  # noqa: BLE001
        return None


def classify_image(client, image_bytes):
    """Returns (features|None, (tokens_in, tokens_out), note)."""
    resp = client.messages.create(
        model=MODEL, max_tokens=600,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.b64encode(image_bytes).decode()}},
            {"type": "text", "text": PROMPT}]}])
    usage = (getattr(resp.usage, "input_tokens", 0) or 0, getattr(resp.usage, "output_tokens", 0) or 0)
    if resp.stop_reason == "refusal":
        return None, usage, "refusal"
    text = next(b.text for b in resp.content if b.type == "text")
    data = json.loads(text)
    if not all(k in data for k in ATTRS):
        raise ValueError("incomplete features")
    return data, usage, None


def cost_usd(tin, tout, model=MODEL):
    pi, po = PRICE[model]
    return tin / 1e6 * pi + tout / 1e6 * po


def _work(session, client, vid):
    img = fetch_thumbnail(session, vid)
    if img is None:
        return vid, "fetch_failed", None, (0, 0)
    try:
        feats, usage, note = classify_image(client, img)
    except Exception:  # noqa: BLE001
        return vid, "classify_failed", None, (0, 0)
    return vid, ("refusal" if note else "ok"), feats, usage


def classify_pending(con, session, client, pending, genre, max_images, stats):
    """pending: list of (video_id, grp). Writes thumb_features rows; respects the hard cap."""
    room = max(0, max_images - stats["classified_calls"])
    todo = pending[:room]
    stats["skipped_by_cap"] += len(pending) - len(todo)
    grp_of = dict(todo)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        results = list(ex.map(lambda v: _work(session, client, v), [v for v, _ in todo]))
    for vid, status, feats, (tin, tout) in results:
        stats["tokens_in"] += tin
        stats["tokens_out"] += tout
        if status == "fetch_failed":
            stats["fetch_failed"] += 1
            continue
        if status == "classify_failed":
            stats["classify_failed"] += 1
            continue
        stats["classified_calls"] += 1
        payload = feats if status == "ok" else {"unclassified": "refusal"}
        if status == "refusal":
            stats["refusals"] += 1
        con.execute("INSERT OR IGNORE INTO thumb_features VALUES(?,?,?,?,?,?)",
                    (vid, genre, grp_of[vid], MODEL, json.dumps(payload), iso(utcnow())))
    con.commit()


# ---------------------------------------------------------------- stats
def load_features(con, ids):
    out = {}
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        q = ",".join("?" * len(chunk))
        for r in con.execute(f"SELECT video_id, features_json FROM thumb_features WHERE video_id IN ({q})", chunk):
            f = json.loads(r["features_json"])
            if "unclassified" not in f:
                out[r["video_id"]] = f
    return out


def _val(f, attr):
    return str(f[attr]).lower() if isinstance(f[attr], bool) else f[attr]


def attribute_table(hit_feats, base_feats, attr):
    nh, nb = len(hit_feats), len(base_feats)
    vals = sorted({_val(f, attr) for f in [*hit_feats, *base_feats]})
    rows = []
    for v in vals:
        ch = sum(1 for f in hit_feats if _val(f, attr) == v)
        cb = sum(1 for f in base_feats if _val(f, attr) == v)
        sh, sb = (ch / nh if nh else 0), (cb / nb if nb else 0)
        lift = sh / sb if (nh >= MIN_GROUP and nb >= MIN_GROUP and cb >= MIN_BASE_COUNT) else None
        rows.append(dict(value=v, hit_n=ch, hit_share=sh, base_n=cb, base_share=sb, lift=lift))
    rows.sort(key=lambda r: (r["lift"] is None, -(r["lift"] or 0), r["value"]))
    return rows


def genre_result(con, genre, hits, base):
    hf = load_features(con, hits)
    bf = load_features(con, base)
    res = dict(genre=genre, hit_n=len(hf), base_n=len(bf), hits_selected=len(hits), base_selected=len(base),
               tables={})
    # Too few selected videos => that group is insufficient (and nothing was classified);
    # otherwise judge by how many thumbnails were actually classified.
    short = [g for g, n in (("hit", len(hits)), ("baseline", len(base))) if n < MIN_GROUP]
    res["insufficient"] = short or [g for g, n in (("hit", len(hf)), ("baseline", len(bf))) if n < MIN_GROUP]
    if not res["insufficient"]:
        for a in ATTRS:
            res["tables"][a] = attribute_table(list(hf.values()), list(bf.values()), a)
    return res


# ---------------------------------------------------------------- report
CAVEATS = [
    "相関であって因果ではありません。サムネイルの様式が再生数を生んだとは言えません。",
    "見ているのはサムネイルのみで、動画本編の映像ではありません。",
    "サンプルが小さい(各群数十本)ため、差は偶然の可能性があります。",
    "生存者バイアス: ヒット群は再生数で選んでおり、同じ様式で伸びなかった動画は見えていません。",
    "模倣はしない: 他者のサムネイルをコピーせず、あくまで参考傾向として使ってください。",
    "画像は保存していません(メモリ上で分類し破棄、保存するのは分類結果のみ)。",
    "モデルの学習には使っていません。",
]


def _pct(x):
    return f"{x * 100:.0f}%"


def render_report(results, stats):
    L = ["# サムネイル視覚スタイル分析", "",
         f"生成: {iso(utcnow())} / モデル: `{MODEL}`", "",
         f"- 分類 {stats['classified_calls']} 枚 / 取得失敗 {stats['fetch_failed']} / 分類失敗 {stats['classify_failed']}"
         f" / 拒否 {stats['refusals']} / 上限超過で未処理 {stats['skipped_by_cap']}",
         f"- トークン 入力 {stats['tokens_in']:,} / 出力 {stats['tokens_out']:,}"
         f" / 実測コスト ${cost_usd(stats['tokens_in'], stats['tokens_out']):.4f}", ""]
    L += ["## 注意事項(必ずお読みください)", ""] + [f"- {c}" for c in CAVEATS] + [""]
    for r in results:
        L += [f"## ジャンル: {r['genre']}", "",
              f"ヒット群 n={r['hit_n']}(選定 {r['hits_selected']}) / ベースライン群 n={r['base_n']}(選定 {r['base_selected']})",
              f"比較の対象(ベースライン): {BASELINE_SOURCE.get(r['genre'], '不明')}", ""]
        if r["insufficient"]:
            names = {"hit": "ヒット群", "baseline": "ベースライン群"}
            L += [f"**データ不足**: {'・'.join(names[g] for g in r['insufficient'])}が {MIN_GROUP} 本未満のため、リフトは計算していません。", ""]
            continue
        cands = []
        for a in ATTRS:
            L += [f"### {LABELS[a]} (`{a}`)", "", "| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |",
                  "|---|---|---|---|---|---|"]
            for t in r["tables"][a]:
                lift = f"{t['lift']:.2f}" if t["lift"] is not None else "-"
                L.append(f"| {t['value']} | {t['hit_n']} | {_pct(t['hit_share'])} | {t['base_n']} | {_pct(t['base_share'])} | {lift} |")
                if t["lift"] is not None and t["lift"] > 0:
                    cands.append((abs(math.log(t["lift"])), a, t))
            L.append("")
        cands.sort(key=lambda c: -c[0])
        L += ["### 要約: 差の大きい上位3点", ""]
        if not cands:
            L.append("- 計算可能なリフトがありません。")
        for _, a, t in cands[:3]:
            d = "多い" if t["lift"] >= 1 else "少ない"
            L.append(f"- {LABELS[a]}が「{t['value']}」の動画は、ヒット群({_pct(t['hit_share'])})の方がベースライン群"
                     f"({_pct(t['base_share'])})より{d}(リフト {t['lift']:.2f})。")
        L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- orchestration
def run(con, genres, limit=40, max_images=200, session=None, client=None, report_dir=None, now=None, seed=0):
    if client is None:
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            raise MissingApiKey("ANTHROPIC_API_KEY is not set; visual-style needs it to classify thumbnails")
        import anthropic
        client = anthropic.Anthropic()
    if session is None:
        import requests
        session = requests.Session()
    con.execute(DDL)
    stats = dict(classified_calls=0, fetch_failed=0, classify_failed=0, refusals=0, skipped_by_cap=0,
                 tokens_in=0, tokens_out=0)
    results = []
    for g in genres:
        hits, base = select_groups(con, g, limit, now, seed)
        if len(hits) >= MIN_GROUP and len(base) >= MIN_GROUP:
            have = {r[0] for r in con.execute("SELECT video_id FROM thumb_features")}
            pending = [(v, grp) for grp, ids in (("hit", hits), ("baseline", base)) for v in ids if v not in have]
            classify_pending(con, session, client, pending, g, max_images, stats)
        results.append(genre_result(con, g, hits, base))
    stats["cost_usd"] = cost_usd(stats["tokens_in"], stats["tokens_out"])
    md = render_report(results, stats)
    d = report_dir or config.REPORT_DIR
    d.mkdir(parents=True, exist_ok=True)
    (d / "visual_style.md").write_text(md, encoding="utf-8")
    return results, stats
