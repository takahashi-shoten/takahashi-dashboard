"""Channel / genre metrics and falsifiable hypothesis evaluation.

Caveat encoded in the output: search returns a *sample* (top results per query), so
genre metrics describe the observed sample, not the whole market. Channel-level
metrics are only trusted for channels whose full 90-day upload list was audited.
"""
import json
import re
from collections import Counter, defaultdict

from . import config
from .util import iso, utcnow, days_since, median, window_start

AI_PAT = re.compile(r"\b(ai[- ]generated|made with ai|ai animation|ai film|ai short|midjourney|sora|runway|"
                    r"kling|veo ?\d?|pika|elevenlabs|stable diffusion|#ai\b)|ai生成|ai動画|生成ai|ＡＩ", re.I)

CHANNEL_METRICS_CREATE = """
CREATE TABLE IF NOT EXISTS channel_metrics(
  channel_id TEXT PRIMARY KEY, title TEXT, genre TEXT, audited INTEGER, subscribers INTEGER,
  subs_hidden INTEGER, channel_age_days REAL, is_new INTEGER, is_small INTEGER,
  uploads_90d INTEGER, uploads_per_week REAL, mature_n INTEGER, long_n INTEGER, long_median REAL,
  short_n INTEGER, short_median REAL, ambiguous_n INTEGER, hits_n INTEGER, hit_share REAL,
  top1_share REAL, median_velocity REAL, ai_signal_share REAL, declared_synthetic INTEGER,
  main_lang TEXT, replicable INTEGER, computed_at TEXT);
"""
CHANNEL_METRICS_DDL = "DROP TABLE IF EXISTS channel_metrics;" + CHANNEL_METRICS_CREATE


def ai_signal(v) -> str:
    if v["synthetic_media"] == 1:
        return "declared"            # creator-declared altered/synthetic content (API field)
    text = " ".join([v["title"] or "", (v["description"] or "")[:1500], v["tags_json"] or ""])
    return "keyword" if AI_PAT.search(text) else "none_found"


def channel_genres(con):
    """Majority genre of the topics through which a channel's videos were discovered."""
    g = defaultdict(Counter)
    for r in con.execute("""SELECT v.channel_id, t.genre FROM discoveries d
                            JOIN videos v ON v.video_id=d.video_id JOIN topics t ON t.topic_id=d.topic_id"""):
        g[r[0]][r[1]] += 1
    return {c: cnt.most_common(1)[0][0] for c, cnt in g.items()}


def compute_channel_metrics(con, now=None):
    now = now or utcnow()
    since = iso(window_start(config.WINDOW_DAYS, now))
    mature_cut = iso(window_start(14, now))
    genres = channel_genres(con)
    con.executescript(CHANNEL_METRICS_DDL)
    chans = con.execute("SELECT * FROM c_latest").fetchall()
    for c in chans:
        vids = con.execute("""SELECT * FROM v_latest WHERE channel_id=? AND published_at>=?
                              AND category_id!='10' AND unavailable_at IS NULL""",
                           (c["channel_id"], since)).fetchall()
        if not vids:
            continue
        audited = int(bool(c["last_audited_at"]) and (c["audit_through"] or "9") <= since)
        mature = [v for v in vids if v["published_at"] <= mature_cut]
        longv = [v["view_count"] for v in mature if v["format_class"] == "long"]
        shortv = [v["view_count"] for v in mature if v["format_class"] == "short_likely"]
        views = [v["view_count"] for v in vids]
        hits = [v for v in vids if v["view_count"] >= config.MIN_VIEWS]
        total = sum(views) or 1
        age = days_since(c["channel_published_at"], now) if c["channel_published_at"] else None
        span_days = min(config.WINDOW_DAYS, age) if age else config.WINDOW_DAYS
        ai = [ai_signal(v) for v in vids]
        langs = Counter((v["default_audio_language"] or v["default_language"] or "und").split("-")[0] for v in vids)
        hit_share = len([v for v in mature if v["view_count"] >= config.MIN_VIEWS]) / len(mature) if mature else None
        med_all_mature = median([v["view_count"] for v in mature])
        replicable = None
        if audited:
            replicable = int(len(mature) >= config.REPL_MIN_UPLOADS
                             and (med_all_mature or 0) >= config.REPL_MIN_MEDIAN
                             and (hit_share or 0) >= config.REPL_MIN_HIT_SHARE)
        subs = c["subscriber_count"]
        con.execute("INSERT INTO channel_metrics VALUES(" + ",".join("?" * 26) + ")", (
            c["channel_id"], c["title"], genres.get(c["channel_id"]), audited, subs, c["subscribers_hidden"],
            age, int(age is not None and age <= config.NEW_CHANNEL_DAYS),
            None if subs is None else int(subs < config.SMALL_CHANNEL_SUBS),
            len(vids), len(vids) / (span_days / 7) if audited else None, len(mature),
            len(longv), median(longv), len(shortv), median(shortv),
            sum(1 for v in mature if v["format_class"] == "ambiguous"),
            len(hits), hit_share if audited else None, max(views) / total,
            median([v["view_count"] / days_since(v["published_at"], now) for v in vids]),
            sum(a != "none_found" for a in ai) / len(ai), sum(a == "declared" for a in ai),
            langs.most_common(1)[0][0], replicable, iso(now)))
    con.commit()


def compute_genre_metrics(con):
    out = {}
    rows = con.execute("SELECT * FROM channel_metrics WHERE genre IS NOT NULL").fetchall()
    by = defaultdict(list)
    for r in rows:
        by[r["genre"]].append(r)
    for g, rs in by.items():
        with_hits = [r for r in rs if r["hits_n"] > 0]
        audited = [r for r in with_hits if r["audited"]]
        repl = [r for r in audited if r["replicable"]]
        hit_views = sorted((con.execute(
            "SELECT COALESCE(SUM(view_count),0) FROM v_latest WHERE channel_id=? AND view_count>=? AND category_id!='10' AND published_at>=?",
            (r["channel_id"], config.MIN_VIEWS, iso(window_start(config.WINDOW_DAYS)))).fetchone()[0]
            for r in with_hits), reverse=True)
        tot = sum(hit_views) or 1
        out[g] = dict(
            genre=g, channels_with_hits=len(with_hits), audited_channels=len(audited),
            replicable_channels=len(repl),
            replicable_rate=(len(repl) / len(audited)) if audited else None,
            replicable_new_channels=sum(1 for r in repl if r["is_new"]),
            replicable_small_channels=sum(1 for r in repl if r["is_small"]),
            top3_share=sum(hit_views[:3]) / tot if with_hits else None,
            hhi=sum((x / tot) ** 2 for x in hit_views) if with_hits else None,
            median_long_median=median([r["long_median"] for r in audited if r["long_median"]]),
            median_short_median=median([r["short_median"] for r in audited if r["short_median"]]),
            median_uploads_per_week=median([r["uploads_per_week"] for r in audited]),
            ai_signal_channels=sum(1 for r in with_hits if (r["ai_signal_share"] or 0) >= 0.5),
            langs=dict(Counter(r["main_lang"] for r in with_hits).most_common(5)),
        )
    return out


# ---------------------------------------------------------------------------
# Hypotheses: each is a machine-checkable test so it can be *refuted* by data.
# test = {"metric": <genre metric>, "op": ">="|"<=", "threshold": x,
#         "support_metric": <genre metric>, "min_support": n}
METRICS = ["channels_with_hits", "audited_channels", "replicable_channels", "replicable_rate",
           "replicable_new_channels", "replicable_small_channels", "top3_share", "hhi",
           "median_long_median", "median_short_median", "median_uploads_per_week", "ai_signal_channels"]

RULE_TEMPLATES = [
    ("entry", "新規チャンネル(開設365日以内)でも再現性ある成功が複数存在する",
     dict(metric="replicable_new_channels", op=">=", threshold=2, support_metric="audited_channels", min_support=8)),
    ("open", "上位3チャンネルがヒット再生の60%未満(寡占ではない)",
     dict(metric="top3_share", op="<=", threshold=0.6, support_metric="channels_with_hits", min_support=8)),
    ("repl", "監査済みヒットチャンネルの25%以上が単発でなく再現性を持つ",
     dict(metric="replicable_rate", op=">=", threshold=0.25, support_metric="audited_channels", min_support=8)),
]


def ensure_rule_hypotheses(con, genres):
    now = iso(utcnow())
    for g in genres:
        for key, stmt, test in RULE_TEMPLATES:
            con.execute("""INSERT OR IGNORE INTO hypotheses(hyp_id, genre, statement, test_json, source, status,
                           created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)""",
                        (f"{g}:{key}", g, stmt, json.dumps(test), "rule", "untested", now, now))
    con.commit()


def evaluate(test, gm):
    if gm is None:
        return "insufficient_data", {}
    sup = gm.get(test["support_metric"]) or 0
    val = gm.get(test["metric"])
    ev = {test["metric"]: val, test["support_metric"]: sup}
    if sup < test["min_support"] or val is None:
        return "insufficient_data", ev
    ok = val >= test["threshold"] if test["op"] == ">=" else val <= test["threshold"]
    return ("supported" if ok else "refuted"), ev


def evaluate_hypotheses(con, gms):
    """Returns list of status changes (these are what is worth reporting)."""
    changes = []
    now = iso(utcnow())
    for h in con.execute("SELECT * FROM hypotheses").fetchall():
        status, ev = evaluate(json.loads(h["test_json"]), gms.get(h["genre"]))
        if status != h["status"]:
            changes.append(dict(hyp_id=h["hyp_id"], genre=h["genre"], statement=h["statement"],
                                old=h["status"], new=status, evidence=ev))
            con.execute("INSERT INTO hypothesis_log(hyp_id, ts, old_status, new_status, evidence_json) VALUES(?,?,?,?,?)",
                        (h["hyp_id"], now, h["status"], status, json.dumps(ev)))
        con.execute("UPDATE hypotheses SET status=?, evidence_json=?, updated_at=? WHERE hyp_id=?",
                    (status, json.dumps(ev), now, h["hyp_id"]))
    con.commit()
    return changes
