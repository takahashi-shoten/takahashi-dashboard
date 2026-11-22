"""Title anatomy: what hit videos of a genre are about and how they are titled, vs. baseline videos.

Read-only analysis of data already collected (titles, durations, views, channel stats). The only
network access is the Anthropic API: titles are classified in batches with Claude Haiku and only the
categorical features are stored. Groups come from visual_style.select_groups (same hit/baseline rules).
"""
import json
import os
import re
from statistics import median

from . import config, visual_style
from .util import days_since, iso, utcnow

MODEL = visual_style.MODEL
PRICE = visual_style.PRICE
MIN_GROUP = visual_style.MIN_GROUP
MIN_BASE_COUNT = visual_style.MIN_BASE_COUNT
MIN_CLUSTER = 3
BATCH_SIZE = 25
YOUNG_CHANNEL_DAYS = 365

ENUMS = {
    "hook_type": ["question", "how_to", "numbered_list", "warning_urgent", "news_timely", "personal_story",
                  "comparison", "mystery_reveal", "definition_explainer", "other"],
    "emotion": ["curiosity", "fear", "hope", "anger", "nostalgia", "awe", "comfort", "none"],
    "specificity": ["high", "medium", "low"],
    "time_sensitivity": ["evergreen", "timely"],
    "clickbait_level": ["low", "medium", "high"],
}
ITEM_PROPS = {
    "index": {"type": "integer"},
    **{k: {"type": "string", "enum": v} for k, v in ENUMS.items()},
    "audience_pain_or_desire": {"type": "string"},
    "topic_cluster": {"type": "string"},
    "real_person_story": {"type": "boolean"},
}
ITEM_SCHEMA = {"type": "object", "properties": ITEM_PROPS, "required": list(ITEM_PROPS),
               "additionalProperties": False}
SCHEMA = {"type": "object",
          "properties": {"items": {"type": "array", "items": ITEM_SCHEMA}},
          "required": ["items"], "additionalProperties": False}
FEATURE_KEYS = [k for k in ITEM_PROPS if k != "index"]
# Attributes shown in lift tables ("has_digit"/"has_bracket" are derived from the title text itself).
ATTRS = ["hook_type", "emotion", "specificity", "time_sensitivity", "clickbait_level", "real_person_story",
         "has_digit", "has_bracket"]
LABELS = {"hook_type": "フック型", "emotion": "感情", "specificity": "具体性", "time_sensitivity": "時事性",
          "clickbait_level": "釣り度", "real_person_story": "実在の人物の物語", "has_digit": "数字を含む",
          "has_bracket": "括弧【】「」を含む"}
PROMPT = ("You classify YouTube video titles. Below is a numbered list of titles (one per line, format "
          "'index: title'). Return JSON {\"items\": [...]} with exactly one item per title, each carrying the "
          "same index you were given. Judge only from the title text. audience_pain_or_desire: the viewer problem "
          "or desire the title promises to solve or satisfy, in the title's language, at most 12 words. "
          "topic_cluster: a short English label of at most 4 words that groups similar videos (reuse the same "
          "label for similar topics). real_person_story: true only if the title promises a real named person's or "
          "participant's story or documentary.\n\n")

DDL = """CREATE TABLE IF NOT EXISTS title_features(
  video_id TEXT PRIMARY KEY, genre TEXT, grp TEXT, model TEXT, features_json TEXT, classified_at TEXT)"""

BRACKETS = re.compile("[【】「」]")
DIGIT = re.compile(r"[0-9０-９]")


class MissingApiKey(RuntimeError):
    pass


def cost_usd(tin, tout, model=MODEL):
    pi, po = PRICE[model]
    return tin / 1e6 * pi + tout / 1e6 * po


# ---------------------------------------------------------------- data
def load_info(con, ids):
    """video_id -> dict(title, duration_s, format_class, view_count, published_at, channel_id, channel stats)."""
    has_cm = con.execute("SELECT 1 FROM sqlite_master WHERE name='channel_metrics'").fetchone() is not None
    if has_cm:
        join, cols = ("LEFT JOIN channel_metrics m ON m.channel_id=v.channel_id",
                      "m.subscribers, m.channel_age_days, m.uploads_90d")
    else:
        join, cols = "", "NULL AS subscribers, NULL AS channel_age_days, NULL AS uploads_90d"
    out = {}
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        q = ",".join("?" * len(chunk))
        for r in con.execute(f"""SELECT v.video_id, v.title, v.duration_s, v.format_class, v.view_count, v.published_at,
              v.channel_id, {cols} FROM v_latest v {join} WHERE v.video_id IN ({q})""", chunk):
            out[r["video_id"]] = dict(r)
    return out


def load_features(con, ids):
    out = {}
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        q = ",".join("?" * len(chunk))
        for r in con.execute(f"SELECT video_id, features_json FROM title_features WHERE video_id IN ({q})", chunk):
            f = json.loads(r["features_json"])
            if "unclassified" not in f:
                out[r["video_id"]] = f
    return out


# ---------------------------------------------------------------- classify
def classify_batch(client, titles):
    """titles: list of (index, title). Returns ({index: features}, (tin, tout), note)."""
    text = PROMPT + "\n".join(f"{i}: {t}" for i, t in titles)
    resp = client.messages.create(
        model=MODEL, max_tokens=8000,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": text}])
    usage = (getattr(resp.usage, "input_tokens", 0) or 0, getattr(resp.usage, "output_tokens", 0) or 0)
    if resp.stop_reason == "refusal":
        return {}, usage, "refusal"
    data = json.loads(next(b.text for b in resp.content if b.type == "text"))
    sent = {i for i, _ in titles}
    got = {}
    for it in data["items"]:
        if it.get("index") in sent and all(k in it for k in FEATURE_KEYS) and it["index"] not in got:
            got[it["index"]] = {k: it[k] for k in FEATURE_KEYS}
    return got, usage, None


def classify_pending(con, client, pending, genre, titles, max_calls, stats):
    """pending: list of (video_id, grp). Batches of BATCH_SIZE; one API call per batch; hard cap on calls."""
    for s in range(0, len(pending), BATCH_SIZE):
        batch = pending[s:s + BATCH_SIZE]
        if stats["api_calls"] >= max_calls:
            stats["skipped_by_cap"] += len(pending) - s
            break
        stats["api_calls"] += 1
        try:
            got, (tin, tout), note = classify_batch(client, [(i, titles[v]) for i, (v, _) in enumerate(batch)])
        except Exception:  # noqa: BLE001
            stats["classify_failed"] += len(batch)
            continue
        stats["tokens_in"] += tin
        stats["tokens_out"] += tout
        for i, (vid, grp) in enumerate(batch):
            if note == "refusal":
                payload = {"unclassified": "refusal"}
                stats["refusals"] += 1
            elif i in got:
                payload = got[i]
                stats["classified"] += 1
            else:
                stats["classify_failed"] += 1      # missing from the reply: retried on the next run
                continue
            con.execute("INSERT OR IGNORE INTO title_features VALUES(?,?,?,?,?,?)",
                        (vid, genre, grp, MODEL, json.dumps(payload, ensure_ascii=False), iso(utcnow())))
        con.commit()


# ---------------------------------------------------------------- stats
def _val(f, attr):
    v = f[attr]
    return str(v).lower() if isinstance(v, bool) else v


def with_derived(feats, info):
    out = {}
    for vid, f in feats.items():
        title = (info.get(vid) or {}).get("title") or ""
        out[vid] = {**f, "has_digit": bool(DIGIT.search(title)), "has_bracket": bool(BRACKETS.search(title))}
    return out


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


def _med(xs):
    xs = [x for x in xs if x is not None]
    return median(xs) if xs else None


def numeric_facts(ids, info, now):
    rows = [info[v] for v in ids if v in info]
    longs = [r["duration_s"] / 60 for r in rows if r["format_class"] == "long" and r["duration_s"]]
    n = len(rows)
    ages = [r["channel_age_days"] for r in rows if r["channel_age_days"] is not None]
    return dict(
        n=n, long_n=len(longs), median_long_min=_med(longs),
        median_title_len=_med([len(r["title"] or "") for r in rows]),
        digit_share=sum(1 for r in rows if DIGIT.search(r["title"] or "")) / n if n else None,
        bracket_share=sum(1 for r in rows if BRACKETS.search(r["title"] or "")) / n if n else None,
        median_vpd=_med([r["view_count"] / days_since(r["published_at"], now) for r in rows]),
        median_subs=_med([r["subscribers"] for r in rows]),
        young_share=sum(1 for a in ages if a < YOUNG_CHANNEL_DAYS) / len(ages) if ages else None,
        median_uploads_90d=_med([r["uploads_90d"] * 90 / config.WINDOW_DAYS for r in rows
                                 if r["uploads_90d"] is not None]))


def cluster_table(hit_feats, info):
    """Topic clusters among hit videos (>= MIN_CLUSTER hits), with example titles."""
    groups = {}
    for vid, f in hit_feats.items():
        key = " ".join(str(f["topic_cluster"]).lower().split())
        if key and vid in info:
            groups.setdefault(key, []).append(vid)
    rows = []
    for key, vids in groups.items():
        if len(vids) < MIN_CLUSTER:
            continue
        vids = sorted(vids, key=lambda v: (-info[v]["view_count"], v))
        rows.append(dict(cluster=key, n=len(vids), median_views=_med([info[v]["view_count"] for v in vids]),
                         examples=[info[v]["title"] for v in vids[:2]]))
    return rows


def genre_result(con, genre, hits, base, now=None):
    now = now or utcnow()
    hf = load_features(con, hits)
    bf = load_features(con, base)
    info = load_info(con, list(hf) + list(bf))
    hfd, bfd = with_derived(hf, info), with_derived(bf, info)
    res = dict(genre=genre, hit_n=len(hf), base_n=len(bf), hits_selected=len(hits), base_selected=len(base),
               tables={}, clusters=[], facts=None)
    short = [g for g, n in (("hit", len(hits)), ("baseline", len(base))) if n < MIN_GROUP]
    res["insufficient"] = short or [g for g, n in (("hit", len(hf)), ("baseline", len(bf))) if n < MIN_GROUP]
    if res["insufficient"]:
        return res
    for a in ATTRS:
        res["tables"][a] = attribute_table(list(hfd.values()), list(bfd.values()), a)
    res["facts"] = dict(hit=numeric_facts(list(hf), info, now), base=numeric_facts(list(bf), info, now))
    res["clusters"] = cluster_table(hf, info)
    return res


# ---------------------------------------------------------------- report
CAVEATS = [
    "相関であって因果ではありません。タイトルの型や話題が再生数を生んだとは言えません。",
    "生存者バイアス: ヒット群は再生数で選んでおり、同じ型で伸びなかった動画は見えていません。",
    "視聴維持率などの視聴者行動データはありません。クリックされても最後まで見られたかは不明です。",
    "サンプルが小さい(各群数十本)ため、差は偶然の可能性があります。",
    "見ているのはタイトル・長さ・チャンネル指標のみで、動画の中身やサムネイルは見ていません。",
    "分類は小型モデルによる自動判定で、人手での検証はしていません。誤分類を含みます。",
    "模倣はしない: 他者のタイトルをコピーせず、あくまで参考傾向として使ってください。",
]


def _pct(x):
    return "-" if x is None else f"{x * 100:.0f}%"


def _fmt(x, fmt):
    if x is None:
        return "-"
    return _pct(x) if fmt == "pct" else fmt.format(x)


def _fact_rows(f):
    h, b = f["hit"], f["base"]
    spec = [("長尺の長さ中央値(分)", "median_long_min", "{:.1f}"), ("タイトル文字数の中央値", "median_title_len", "{:.0f}"),
            ("数字を含むタイトルの割合", "digit_share", "pct"), ("括弧【】「」を含む割合", "bracket_share", "pct"),
            ("再生数/日の中央値", "median_vpd", "{:,.0f}"), ("チャンネル登録者数の中央値", "median_subs", "{:,.0f}"),
            ("1年未満のチャンネルの割合", "young_share", "pct"), ("90日あたり投稿数の中央値", "median_uploads_90d", "{:.1f}")]
    return [f"| {label} | {_fmt(h[k], fmt)} | {_fmt(b[k], fmt)} |" for label, k, fmt in spec]


def playbook(r):
    L = ["### プレイブック案(仮説)", "",
         "以下は相関から機械的に作った**仮説**です。因果は確認していません。", ""]
    h = r["facts"]["hit"]
    if h["median_long_min"] is not None and h["long_n"] >= MIN_CLUSTER:
        m = h["median_long_min"]
        L.append(f"- 目標の長さ(長尺): ヒット群の中央値 {m:.1f} 分の±25% = {m * 0.75:.1f}〜{m * 1.25:.1f} 分")
    else:
        L.append("- 目標の長さ: 長尺のヒット動画が少なく、範囲を出せません。")
    cands = [(a, t) for a in ATTRS for t in r["tables"][a] if t["lift"] is not None and t["lift"] > 1]
    cands.sort(key=lambda c: (-c[1]["lift"], c[0], c[1]["value"]))
    L.append("- リフトの高いタイトルの型 上位3点:")
    for a, t in cands[:3]:
        L.append(f"  - {LABELS[a]}=「{t['value']}」: ヒット {_pct(t['hit_share'])} / ベース {_pct(t['base_share'])}(リフト {t['lift']:.2f})")
    if not cands:
        L.append("  - 計算可能な1超のリフトがありません。")
    best = sorted(r["clusters"], key=lambda c: (-c["median_views"], -c["n"], c["cluster"]))[:5]
    L.append("- 有望な話題クラスタ 上位5件(ヒット群の再生数中央値順):")
    for c in best:
        L.append(f"  - {c['cluster']}(ヒット {c['n']} 本 / 再生数中央値 {c['median_views']:,.0f})")
    if not best:
        L.append(f"  - {MIN_CLUSTER} 本以上のクラスタがありません。")
    L += ["", "注意: 生存者バイアス・視聴維持率データなし・小サンプル・タイトルのみ・小型モデルの未検証分類、という限界があります。", ""]
    return L


def render_report(results, stats):
    L = ["# タイトル解剖(何の話題が、どんなタイトルで伸びたか)", "",
         f"生成: {iso(utcnow())} / モデル: `{MODEL}`", "",
         f"- 分類 {stats['classified']} 本 / APIコール {stats['api_calls']} / 分類失敗 {stats['classify_failed']}"
         f" / 拒否 {stats['refusals']} / 上限超過で未処理 {stats['skipped_by_cap']}",
         f"- トークン 入力 {stats['tokens_in']:,} / 出力 {stats['tokens_out']:,}"
         f" / 実測コスト ${cost_usd(stats['tokens_in'], stats['tokens_out']):.4f}", ""]
    L += ["## 注意事項(必ずお読みください)", ""] + [f"- {c}" for c in CAVEATS] + [""]
    for r in results:
        L += [f"## ジャンル: {r['genre']}", "",
              f"ヒット群 n={r['hit_n']}(選定 {r['hits_selected']}) / ベースライン群 n={r['base_n']}(選定 {r['base_selected']})",
              f"比較の対象(ベースライン): {visual_style.BASELINE_SOURCE.get(r['genre'], '不明')}", ""]
        if r["insufficient"]:
            names = {"hit": "ヒット群", "baseline": "ベースライン群"}
            L += [f"**データ不足**: {'・'.join(names[g] for g in r['insufficient'])}が {MIN_GROUP} 本未満のため、リフトは計算していません。", ""]
            continue
        for a in ATTRS:
            L += [f"#### {LABELS[a]} (`{a}`)", "", "| 値 | ヒット n | ヒット割合 | ベース n | ベース割合 | リフト |",
                  "|---|---|---|---|---|---|"]
            for t in r["tables"][a]:
                lift = f"{t['lift']:.2f}" if t["lift"] is not None else "-"
                L.append(f"| {t['value']} | {t['hit_n']} | {_pct(t['hit_share'])} | {t['base_n']} | {_pct(t['base_share'])} | {lift} |")
            L.append("")
        L += ["### 数値の事実(ヒット vs ベースライン)", "", "| 指標 | ヒット | ベース |", "|---|---|---|", *_fact_rows(r["facts"]), ""]
        L += [f"### 話題クラスタ(ヒット {MIN_CLUSTER} 本以上)", ""]
        if not r["clusters"]:
            L += ["該当するクラスタはありません。", ""]
        else:
            for title, key in (("ヒット本数の多い順", lambda c: (-c["n"], -c["median_views"], c["cluster"])),
                               ("ヒット群の再生数中央値の高い順", lambda c: (-c["median_views"], -c["n"], c["cluster"]))):
                L += [f"**{title}**", "", "| クラスタ | ヒット本数 | 再生数中央値 | 例1 | 例2 |", "|---|---|---|---|---|"]
                for c in sorted(r["clusters"], key=key)[:10]:
                    ex = [e.replace("|", "/") for e in c["examples"]] + ["", ""]
                    L.append(f"| {c['cluster']} | {c['n']} | {c['median_views']:,.0f} | {ex[0]} | {ex[1]} |")
                L.append("")
        L += playbook(r)
    return "\n".join(L)


# ---------------------------------------------------------------- orchestration
def run(con, genres, limit=60, max_calls=40, client=None, report_dir=None, now=None, seed=0):
    if client is None:
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            raise MissingApiKey("ANTHROPIC_API_KEY is not set; title-anatomy needs it to classify titles")
        import anthropic
        client = anthropic.Anthropic()
    con.execute(DDL)
    stats = dict(api_calls=0, classified=0, classify_failed=0, refusals=0, skipped_by_cap=0, tokens_in=0, tokens_out=0)
    results = []
    for g in genres:
        hits, base = visual_style.select_groups(con, g, limit, now, seed)
        if len(hits) >= MIN_GROUP and len(base) >= MIN_GROUP:
            have = {r[0] for r in con.execute("SELECT video_id FROM title_features")}
            pending = [(v, grp) for grp, ids in (("hit", hits), ("baseline", base)) for v in ids if v not in have]
            info = load_info(con, [v for v, _ in pending])
            pending = [(v, grp) for v, grp in pending if info.get(v) and (info[v]["title"] or "").strip()]
            classify_pending(con, client, pending, g, {v: info[v]["title"] for v, _ in pending}, max_calls, stats)
        results.append(genre_result(con, g, hits, base, now))
    stats["cost_usd"] = cost_usd(stats["tokens_in"], stats["tokens_out"])
    md = render_report(results, stats)
    d = report_dir or config.REPORT_DIR
    d.mkdir(parents=True, exist_ok=True)
    (d / "title_anatomy.md").write_text(md, encoding="utf-8")
    return results, stats
