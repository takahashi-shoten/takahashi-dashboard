"""Reproducible analyses on the research DB (read-only) for the 2026-11-25 directive, items answerable WITHOUT new data.
Usage: python3 -I yt_research/analyses_2026-11-25.py <ytr.sqlite> <out_dir>
Rules: views = latest snapshot; age = days between publication and that snapshot; 'mature' = age >= 14 days (same as the existing pipeline); subscriber counts are CURRENT
(not at publication time) and are only used for coarse size classes; every number is descriptive and correlational. Sampling caveats are written into the output."""
import json
import re
import sqlite3
import statistics as S
import sys
from collections import Counter, defaultdict
from pathlib import Path

db, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
con.row_factory = sqlite3.Row

SQL_VIDEOS = """
SELECT v.video_id, v.channel_id, v.title, v.description, v.published_at, v.duration_s, v.format_class,
       coalesce(v.default_audio_language, v.default_language) lang,
       s.view_count views, s.observed_at obs,
       julianday(s.observed_at) - julianday(v.published_at) age_days,
       m.genre, m.subscribers subs, m.is_new, m.is_small, m.channel_age_days, m.replicable, m.long_median, m.short_median, m.main_lang,
       c.title channel_title, c.country
FROM videos v
JOIN video_snapshots s ON s.video_id = v.video_id AND s.observed_at = (SELECT max(observed_at) FROM video_snapshots WHERE video_id = v.video_id)
LEFT JOIN channel_metrics m ON m.channel_id = v.channel_id
LEFT JOIN channels c ON c.channel_id = v.channel_id
WHERE v.unavailable_at IS NULL"""
rows = [dict(r) for r in con.execute(SQL_VIDEOS)]
mature = [r for r in rows if r["age_days"] is not None and r["age_days"] >= 14 and r["views"] is not None]
R = {"definitions": {"views": "latest snapshot", "mature": "age >= 14 days", "hit": ">= 50,000 views (existing pipeline threshold)", "small": "current subs < 100,000", "new": "channel age <= 365 days",
                     "subs_note": "CURRENT subscribers, not subscribers at publication"},
     "n_videos": len(rows), "n_mature": len(mature)}
url = lambda r: f"https://www.youtube.com/watch?v={r['video_id']}"

# ---- A. standout videos from small AND new channels (the 'small channel breakout' question)
A = [r for r in mature if r["is_small"] and r["is_new"] and r["views"] >= 50_000]
R["A_small_new_channel_hits"] = dict(
    n_videos=len(A), n_channels=len({r["channel_id"] for r in A}),
    by_genre=Counter(r["genre"] for r in A).most_common(15), by_lang=Counter(r["lang"] for r in A).most_common(8),
    by_format=Counter(r["format_class"] for r in A).most_common(),
    top=[dict(url=url(r), title=r["title"][:70], channel=r["channel_title"], genre=r["genre"], lang=r["lang"], views=r["views"], age_days=round(r["age_days"]),
              subs_now=r["subs"], channel_age_days=round(r["channel_age_days"] or 0), format=r["format_class"]) for r in sorted(A, key=lambda r: -r["views"])[:25]])
fast = [r for r in A if (r["channel_age_days"] or 9999) <= 120]
R["A2_hits_from_channels_younger_than_120_days"] = dict(n_videos=len(fast), n_channels=len({r["channel_id"] for r in fast}), by_genre=Counter(r["genre"] for r in fast).most_common(10))

# ---- B. within-channel high vs low (needs >= 8 mature videos per channel)
by_ch = defaultdict(list)
for r in mature:
    by_ch[r["channel_id"]].append(r)
B = []
for cid, vs in by_ch.items():
    if len(vs) >= 8:
        med = S.median(v["views"] for v in vs)
        if med > 0:
            top = max(vs, key=lambda v: v["views"])
            B.append(dict(channel=top["channel_title"], genre=top["genre"], n=len(vs), median=med, top_views=top["views"], ratio=round(top["views"] / med, 1), top_url=url(top), top_title=top["title"][:60]))
ratios = sorted(b["ratio"] for b in B)
R["B_within_channel_outliers"] = dict(n_channels=len(B), ratio_quantiles={q: ratios[int(len(ratios) * q)] for q in (0.25, 0.5, 0.75, 0.9, 0.99)} if ratios else None,
                                       share_channels_top_ge_10x_median=round(sum(1 for r in ratios if r >= 10) / len(ratios), 3) if ratios else None,
                                       top=sorted(B, key=lambda b: -b["ratio"])[:15])

# ---- C. language x genre supply / demand (strong selection caveat: topics were chosen by us)
G = defaultdict(lambda: defaultdict(list))
chs = defaultdict(lambda: defaultdict(set))
for r in mature:
    lang = (r["lang"] or "none").split("-")[0]
    if lang in ("ja", "en"):
        G[r["genre"]][lang].append(r["views"])
        chs[r["genre"]][lang].add(r["channel_id"])
C = []
for g, d in G.items():
    row = dict(genre=g)
    for lang in ("ja", "en"):
        v = d.get(lang, [])
        row[lang] = dict(videos=len(v), channels=len(chs[g][lang]), median_views=S.median(v) if v else None, hit_rate=round(sum(1 for x in v if x >= 50_000) / len(v), 3) if v else None)
    C.append(row)
C.sort(key=lambda x: -(x["en"]["videos"] + x["ja"]["videos"]))
R["C_genre_by_language"] = dict(note="Genres/topics were selected by our own search design (see audit); a language with few videos may simply have had fewer queries. Not a supply-gap proof.", rows=C[:30])
both = [c for c in C if c["ja"]["videos"] >= 200 and c["en"]["videos"] >= 200]
R["C2_candidates_en_stronger_than_ja"] = sorted([dict(genre=c["genre"], en_hit=c["en"]["hit_rate"], ja_hit=c["ja"]["hit_rate"], en_median=c["en"]["median_views"], ja_median=c["ja"]["median_views"],
                                                      ja_channels=c["ja"]["channels"], en_channels=c["en"]["channels"]) for c in both], key=lambda c: -((c["en_hit"] or 0) - (c["ja_hit"] or 0)))[:10]

# ---- E. monetisation-path signals in video descriptions (keyword matching; presence != revenue)
PAT = {"affiliate_or_store": r"amzn\.to|amazon\.(co|com)|a8\.net|rakuten|affiliate|アフィリエイト|\bshop\b|store|booth\.pm|base\.shop|stores\.jp",
       "email_list_or_line": r"メルマガ|newsletter|substack|beehiiv|lin\.ee|line\.me|LINE公式|mailchimp|stepmail",
       "course_membership_or_product": r"udemy|skool|gumroad|stan\.store|teachable|patreon|ko-fi|buymeacoffee|memberships?|メンバーシップ|オンラインサロン|講座|note\.com|coconala|ココナラ",
       "sponsorship_or_business": r"sponsor|business inquir|お仕事|ご依頼|お問い合わせ|collab|ビジネス"}
rx = {k: re.compile(p, re.I) for k, p in PAT.items()}
E_by_class = defaultdict(lambda: Counter())
for r in mature:
    d = r["description"] or ""
    cls = "small_new" if (r["is_small"] and r["is_new"]) else ("small" if r["is_small"] else ("large" if r["is_small"] == 0 else "unknown"))
    E_by_class[cls]["videos"] += 1
    for k, p in rx.items():
        if p.search(d):
            E_by_class[cls][k] += 1
R["E_monetisation_signals_in_descriptions"] = dict(note="keyword presence in descriptions only; says nothing about revenue; descriptions missing for ~16% of videos",
                                                    by_channel_size={k: dict(v, **{kk + "_pct": round(100 * v[kk] / v["videos"], 1) for kk in PAT if v["videos"]}) for k, v in E_by_class.items()})
hits_ = [r for r in mature if r["views"] >= 50_000]
nh = [r for r in mature if r["views"] < 50_000]
def share(rs, k):
    return round(100 * sum(1 for r in rs if rx[k].search(r["description"] or "")) / max(1, len(rs)), 1)
R["E2_link_presence_hit_vs_nonhit"] = {k: dict(hit_pct=share(hits_, k), nonhit_pct=share(nh, k)) for k in PAT} | dict(n_hit=len(hits_), n_nonhit=len(nh))

# ---- F. non-face / replicable evidence available in the DB: replicable-flagged channels by genre (existing definition)
rep = [r for r in {r["channel_id"]: r for r in mature if r["replicable"]}.values()]
R["F_replicable_channels_by_genre"] = Counter(r["genre"] for r in rep).most_common(15)

(out / "analyses.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: R[k] for k in R if k not in ("A_small_new_channel_hits", "B_within_channel_outliers", "C_genre_by_language")}, ensure_ascii=False, indent=1, default=str)[:6000])
