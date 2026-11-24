"""Experiment registry and diagnosis: the closed loop of the business (docs/MANAGEMENT_PRINCIPLES.md).

plan -> produce -> publish -> measure (24h/72h/7d/28d) -> diagnose -> propose ONE change -> next experiment.
Every experiment has a unique id, a hypothesis, the ten planning facts (unknown = "未確認", never guessed), its costs and its measured results.
Diagnosis separates: too few impressions / low click-through / early drop-off / expectation mismatch, and refuses to conclude when data is insufficient.
Nothing here publishes or spends: it only records and analyses."""
import json
import sys
from datetime import datetime, timezone

from . import ledger

UNKNOWN = "未確認"
PLAN_FIELDS = [      # the ten planning facts (principles section 2)
    "audience_and_desire", "evidence_of_desire", "competitor_videos", "competitor_channel_scale_and_distribution",
    "room_for_individual_ai", "differentiation", "cost_and_time_estimate", "monetization_path", "what_this_tests", "failure_metrics"]
CHECKPOINTS = ("24h", "72h", "7d", "28d")

DDL = """
CREATE TABLE IF NOT EXISTS experiments(
  experiment_id TEXT PRIMARY KEY, project_id INTEGER, status TEXT, hypothesis TEXT, audience TEXT, desire TEXT, plan_json TEXT,
  title TEXT, thumbnail_text TEXT, structure TEXT, length_s INTEGER, tools_json TEXT,
  cost_usd REAL, production_minutes REAL, published_at TEXT, video_id TEXT,
  parent_id TEXT, changed_factor TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS experiment_results(
  experiment_id TEXT, checkpoint TEXT, observed_at TEXT, impressions REAL, ctr REAL, views REAL, avg_view_duration_s REAL,
  avg_view_pct REAL, subs_gained REAL, revenue_usd REAL, unavailable_json TEXT, PRIMARY KEY(experiment_id, checkpoint));
CREATE TABLE IF NOT EXISTS experiment_analysis(
  experiment_id TEXT, checkpoint TEXT, diagnosis TEXT, confidence TEXT, evidence_json TEXT, next_change TEXT, created_at TEXT,
  PRIMARY KEY(experiment_id, checkpoint));
"""


def init(con):
    con.executescript(DDL)
    con.commit()


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id(con):
    init(con)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    n = con.execute("SELECT COUNT(*) FROM experiments WHERE experiment_id LIKE ?", (f"E-{day}-%",)).fetchone()[0] + 1
    return f"E-{day}-{n:02d}"


def create_experiment(con, plan, parent_id=None, changed_factor=None):
    """plan: dict with hypothesis, audience, desire, title, thumbnail_text, structure, length_s, tools and every PLAN_FIELDS key
    (use "未確認" for unknown facts; a missing key is an error so nothing is silently guessed)."""
    init(con)
    missing = [k for k in ["hypothesis"] + PLAN_FIELDS if k not in plan or plan[k] in (None, "", [], {})]
    if missing:
        raise ValueError(f"plan incomplete (use '{UNKNOWN}' for unknown facts): {missing}")
    eid = new_id(con)
    con.execute("INSERT INTO experiments(experiment_id,status,hypothesis,audience,desire,plan_json,title,thumbnail_text,structure,length_s,tools_json,"
                "parent_id,changed_factor,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (eid, "planned", plan["hypothesis"], plan.get("audience", ""), plan.get("desire", ""),
                 json.dumps({k: plan[k] for k in PLAN_FIELDS}, ensure_ascii=False), plan.get("title"), plan.get("thumbnail_text"),
                 plan.get("structure"), plan.get("length_s"), json.dumps(plan.get("tools", []), ensure_ascii=False), parent_id, changed_factor, _now()))
    con.commit()
    return eid


def create_from_file(con, path, **kw):
    """Register an experiment from a plan JSON file (experiments/plans/*.json). Plans are kept in git as the experiment record."""
    with open(path, encoding="utf-8") as f:
        return create_experiment(con, json.load(f), **kw)


def attach_production(con, eid, project_id, minutes=None):
    """Link the production project; cost is summed from the ledger (measured/estimated as recorded there)."""
    usd = con.execute("SELECT COALESCE(SUM(usd),0) FROM costs WHERE project_id=?", (project_id,)).fetchone()[0]
    con.execute("UPDATE experiments SET project_id=?, cost_usd=?, production_minutes=?, status='produced' WHERE experiment_id=?",
                (project_id, usd, minutes, eid))
    con.commit()
    return usd


def mark_published(con, eid, video_id, published_at):
    con.execute("UPDATE experiments SET video_id=?, published_at=?, status='published' WHERE experiment_id=?", (video_id, published_at, eid))
    con.commit()


def record_result(con, eid, checkpoint, metrics, unavailable=()):
    """metrics keys (None/absent = 未取得): impressions, ctr (0-1), views, avg_view_duration_s, avg_view_pct (0-100), subs_gained, revenue_usd."""
    if checkpoint not in CHECKPOINTS:
        raise ValueError(f"checkpoint must be one of {CHECKPOINTS}")
    init(con)
    g = metrics.get
    con.execute("INSERT OR REPLACE INTO experiment_results VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (eid, checkpoint, _now(), g("impressions"), g("ctr"), g("views"), g("avg_view_duration_s"), g("avg_view_pct"),
                 g("subs_gained"), g("revenue_usd"), json.dumps(list(unavailable))))
    con.execute("UPDATE experiments SET status='measuring' WHERE experiment_id=? AND status IN ('published','measuring')", (eid,))
    con.commit()


MIN_IMPRESSIONS = 1000        # below this the click-through rate is not interpretable
MIN_VIEWS = 100               # below this retention figures are not interpretable
DEFAULT_CTR_BENCHMARK = None  # unverified: no published benchmark is assumed; the channel's own earlier results are used once available


def channel_ctr_baseline(con, exclude_eid=None, min_impressions=MIN_IMPRESSIONS):
    rows = con.execute("SELECT ctr FROM experiment_results WHERE checkpoint IN ('7d','28d') AND impressions>=? AND ctr IS NOT NULL AND experiment_id!=?",
                       (min_impressions, exclude_eid or "")).fetchall()
    v = sorted(r[0] for r in rows)
    return (v[len(v) // 2], len(v)) if len(v) >= 3 else (None, len(v))


def diagnose(con, eid, checkpoint="7d"):
    """Funnel diagnosis. Returns dict(diagnosis, confidence, evidence, missing_data, next_change). Never concludes from insufficient data."""
    init(con)
    r = con.execute("SELECT * FROM experiment_results WHERE experiment_id=? AND checkpoint=?", (eid, checkpoint)).fetchone()
    if r is None:
        return dict(diagnosis="no_data", confidence="none", evidence={}, missing_data=["measurement at " + checkpoint], next_change="measure first")
    imp, ctr, views, pct = r["impressions"], r["ctr"], r["views"], r["avg_view_pct"]
    ev = dict(impressions=imp, ctr=ctr, views=views, avg_view_pct=pct)
    missing = [k for k, v in ev.items() if v is None]
    if imp is None:
        return dict(diagnosis="impressions_unavailable", confidence="none", evidence=ev, missing_data=missing + ["audience retention curve"],
                    next_change="cannot separate 'not shown' from 'not clicked': obtain impression data before changing anything")
    if imp < MIN_IMPRESSIONS:
        return dict(diagnosis="too_few_impressions", confidence="low", evidence=ev, missing_data=missing,
                    next_change="YouTube showed the video to very few people: do not judge title/thumbnail yet; wait for more data or test a different topic/format signal")
    base, n_base = channel_ctr_baseline(con, exclude_eid=eid)
    if ctr is None:
        return dict(diagnosis="ctr_unavailable", confidence="none", evidence=ev, missing_data=missing, next_change="obtain click-through rate")
    if base is None:
        ev["ctr_benchmark"] = "未確認 (fewer than 3 earlier measured experiments on this channel)"
        low_ctr = None
    else:
        ev["channel_median_ctr"], ev["baseline_n"] = base, n_base
        low_ctr = ctr < base * 0.7
    if low_ctr:
        return dict(diagnosis="low_click_through", confidence="medium", evidence=ev, missing_data=missing,
                    next_change="change ONLY the thumbnail (or only the title); keep the content so the effect is attributable")
    if views is not None and views >= MIN_VIEWS and pct is not None:
        if pct < 25:
            return dict(diagnosis="early_drop_off_suspected", confidence="low", evidence=ev,
                        missing_data=missing + ["audience retention curve (first 10s / 30s) not yet collected"],
                        next_change="change ONLY the opening (first 10 seconds); verify with the retention curve before concluding")
        if low_ctr is False and pct >= 25:
            return dict(diagnosis="funnel_ok_scale_limited", confidence="low", evidence=ev, missing_data=missing,
                        next_change="clicks and watch time look acceptable relative to this channel: test the same format on a new topic to confirm it repeats")
    return dict(diagnosis="inconclusive", confidence="low", evidence=ev, missing_data=missing + ["more experiments for a baseline"],
                next_change="not enough data to attribute: run the next experiment changing a single factor")


def save_analysis(con, eid, checkpoint, d):
    con.execute("INSERT OR REPLACE INTO experiment_analysis VALUES(?,?,?,?,?,?,?)",
                (eid, checkpoint, d["diagnosis"], d["confidence"], json.dumps({"evidence": d["evidence"], "missing": d["missing_data"]}, ensure_ascii=False),
                 d["next_change"], _now()))
    con.execute("UPDATE experiments SET status='analyzed' WHERE experiment_id=?", (eid,))
    con.commit()


def spend_summary(con):
    """Costs per experiment and per analysed experiment (learning), from recorded production costs."""
    init(con)
    rows = con.execute("SELECT experiment_id, cost_usd, status FROM experiments").fetchall()
    total = sum(r["cost_usd"] or 0 for r in rows)
    learned = [r for r in rows if r["status"] == "analyzed"]
    return dict(experiments=len(rows), total_usd=round(total, 4), analyzed=len(learned),
                usd_per_analyzed=round(sum(r["cost_usd"] or 0 for r in learned) / len(learned), 4) if learned else None)


def main(argv=None):
    argv = argv or sys.argv[1:]
    con = ledger.connect()
    init(con)
    for r in con.execute("SELECT experiment_id, status, title, cost_usd, published_at FROM experiments ORDER BY experiment_id"):
        print(dict(r))
    print(spend_summary(con))
    return 0


if __name__ == "__main__":
    sys.exit(main())
