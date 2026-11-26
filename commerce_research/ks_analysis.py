"""Kickstarter-style campaign analysis on the SQLite loaded by profile_csv.py (table raw_0). Stdlib only (sqlite3 + statistics).
Separates PLEDGED (supporter commitments) from settled money (not available in the data), and revenue from profit (not available). Usage: python3 ks_analysis.py DB TABLE"""
import sqlite3, sys, statistics as st, collections, json
con = sqlite3.connect(sys.argv[1]); con.row_factory = sqlite3.Row
T = sys.argv[2] if len(sys.argv) > 2 else "raw_0"
rows = [dict(r) for r in con.execute(f'SELECT * FROM "{T}"')]
def f(x):
    try: return float(x)
    except Exception: return None
# de-duplicate: keep the latest observation per id (collected_at), outcome rows only
latest = {}
for r in rows:
    k = r["id"]
    if k not in latest or (r.get("collected_at") or "") >= (latest[k].get("collected_at") or ""): latest[k] = r
rows = list(latest.values())
out = {"unique_campaigns": len(rows)}
done = [r for r in rows if r["state"] in ("successful", "failed")]
out["resolved_success_fail"] = collections.Counter(r["state"] for r in done)
for r in done:
    r["_goal_usd"] = (f(r["goal"]) or 0) * (f(r["static_usd_rate"]) or 1)
    r["_pl"] = f(r["usd_pledged"]); r["_b"] = f(r["backers_count"]); r["_ok"] = r["state"] == "successful"
def rate(sub): return round(sum(r["_ok"] for r in sub) / len(sub), 3) if sub else None
out["overall_success_rate_among_resolved"] = rate(done)
# category
cat = collections.defaultdict(list)
for r in done: cat[(r["category_parent_name"], r["category_name"])].append(r)
out["by_category(n>=150)"] = sorted([(k[0] + "/" + k[1], len(v), rate(v), round(st.median([x["_goal_usd"] for x in v])), round(st.median([x["_pl"] or 0 for x in v]))) for k, v in cat.items() if len(v) >= 150], key=lambda x: -x[2])
# goal bands
bands = [(0, 1000), (1000, 5000), (5000, 20000), (20000, 100000), (100000, 10**12)]
out["by_goal_usd_band(n,success_rate,median_backers,median_pledged_usd)"] = []
for lo, hi in bands:
    s = [r for r in done if lo <= r["_goal_usd"] < hi]
    if s: out["by_goal_usd_band(n,success_rate,median_backers,median_pledged_usd)"].append((f"{lo}-{hi}", len(s), rate(s), st.median([r["_b"] or 0 for r in s]), round(st.median([r["_pl"] or 0 for r in s]))))
# average pledge per backer (successful), price-point proxy
pp = [r["_pl"] / r["_b"] for r in done if r["_ok"] and r["_b"] and r["_pl"]]
out["pledge_per_backer_usd_successful(median,p25,p75)"] = [round(x, 1) for x in (st.median(pp), *st.quantiles(pp, n=4)[::2])]
# text: blurb length and staff_pick
def L(r): return len(r["blurb"] or "")
for name, fn in (("blurb_len<=60", lambda r: L(r) <= 60), ("blurb_len>60", lambda r: L(r) > 60), ("staff_pick", lambda r: r["staff_pick"] in ("true", "True", "1")), ("not_staff_pick", lambda r: r["staff_pick"] not in ("true", "True", "1"))):
    s = [r for r in done if fn(r)]; out.setdefault("text/flags(n,success_rate)", []).append((name, len(s), rate(s)))
# concentration: share of pledges from top 10% of successful campaigns
pl = sorted([r["_pl"] or 0 for r in done if r["_ok"]], reverse=True); tot = sum(pl) or 1
out["pledge_concentration"] = dict(successful_n=len(pl), top10pct_share=round(sum(pl[: len(pl) // 10]) / tot, 3), top1pct_share=round(sum(pl[: len(pl) // 100]) / tot, 3), median_pledged_usd=round(st.median(pl)))
# success among 'small-goal': proxy for low-cost products
out["country_top(n,success_rate)"] = [(k, len(v), rate(v)) for k, v in sorted(collections.defaultdict(list, {c: [r for r in done if r["country"] == c] for c in set(r["country"] for r in done)}).items(), key=lambda kv: -len(kv[1]))[:6]]
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
