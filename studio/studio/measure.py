"""Measurement loop: for every published experiment, fetch YouTube data at each due checkpoint (24h/72h/7d/28d), store comparable results,
diagnose the funnel and record the proposed single change. Safe to run repeatedly (a checkpoint is stored once). Needs the YT_OAUTH_* secrets.

CLI:  python -m studio.measure register PLAN.json | publish EID VIDEO_ID PUBLISHED_AT | run | report     (registry path: STUDIO_DB)"""
import json
import sys

from . import experiments as ex
from . import ledger, youtube

METRIC_MAP = {   # experiment field -> candidate analytics metric names, first available wins
    "views": ["views", "data_api.viewCount"],
    "avg_view_duration_s": ["averageViewDuration"],
    "avg_view_pct": ["averageViewPercentage"],
    "impressions": ["videoThumbnailImpressions", "impressions"],
    "ctr": ["videoThumbnailImpressionsClickRate", "impressionsClickThroughRate"],
    "revenue_usd": ["estimatedRevenue"],
}


def results_from_metrics(con, video_id, checkpoint):
    """Latest stored totals (no breakdown dimension) for this checkpoint -> dict for experiments.record_result. Absent = None (未取得).
    CTR from the Analytics API is documented as a percentage, so it is divided by 100 (assumption: verify with the first real data)."""
    youtube.ensure_schema(con)
    obs = con.execute("SELECT observed_at FROM video_metrics WHERE video_id=? AND metric='checkpoint' AND dimension_value=? ORDER BY observed_at DESC LIMIT 1",
                      (video_id, checkpoint)).fetchone()
    if not obs:
        return {}
    rows = {r[0]: r[1] for r in con.execute(
        "SELECT metric, value FROM video_metrics WHERE video_id=? AND observed_at=? AND dimension IS NULL", (video_id, obs[0]))}
    out = {}
    for field, names in METRIC_MAP.items():
        for n in names:
            if n in rows and rows[n] is not None:
                out[field] = rows[n]
                break
    if out.get("ctr") is not None:
        out["ctr"] = out["ctr"] / 100.0
    if "subscribersGained" in rows:
        out["subs_gained"] = rows["subscribersGained"] - (rows.get("subscribersLost") or 0)
    return out


def run_once(con, session=None, now=None):
    """Measure every published experiment at its due checkpoints. Returns a list of what was done (for the log)."""
    ex.init(con)
    done = []
    for e in con.execute("SELECT * FROM experiments WHERE video_id IS NOT NULL AND published_at IS NOT NULL AND status IN ('published','measuring','analyzed')").fetchall():
        for cp in youtube.due_checkpoints(e["published_at"], now=now, con=con, video_id=e["video_id"]):
            snap = youtube.snapshot(con, e["project_id"] or 0, e["video_id"], e["published_at"], session=session, now=now, checkpoint=cp)
            res = results_from_metrics(con, e["video_id"], cp)
            ex.record_result(con, e["experiment_id"], cp, res, unavailable=snap.get("unavailable_metrics", []))
            d = ex.diagnose(con, e["experiment_id"], cp)
            ex.save_analysis(con, e["experiment_id"], cp, d)
            done.append(dict(experiment=e["experiment_id"], checkpoint=cp, diagnosis=d["diagnosis"], confidence=d["confidence"],
                             unavailable=snap.get("unavailable_metrics", [])))
    return done


def report(con):
    ex.init(con)
    lines = []
    for e in con.execute("SELECT * FROM experiments ORDER BY experiment_id").fetchall():
        lines.append(f"{e['experiment_id']} [{e['status']}] {e['title']} cost=${(e['cost_usd'] or 0):.2f} published={e['published_at'] or '未公開'}")
        for a in con.execute("SELECT checkpoint, diagnosis, confidence, next_change FROM experiment_analysis WHERE experiment_id=? ORDER BY checkpoint", (e["experiment_id"],)):
            lines.append(f"   {a['checkpoint']}: {a['diagnosis']} ({a['confidence']}) -> {a['next_change']}")
    lines.append(json.dumps(ex.spend_summary(con), ensure_ascii=False))
    return "\n".join(lines)


def main(argv=None):
    argv = argv or sys.argv[1:]
    con = ledger.connect()
    ex.init(con)
    cmd = argv[0] if argv else "report"
    if cmd == "register":
        print(ex.create_from_file(con, argv[1]))
    elif cmd == "publish":
        ex.mark_published(con, argv[1], argv[2], argv[3])
        print("ok")
    elif cmd == "check":
        print(json.dumps(youtube.connection_check(), ensure_ascii=False, indent=1))
    elif cmd == "run":
        print(json.dumps(run_once(con), ensure_ascii=False, indent=1))
    else:
        print(report(con))
    return 0


if __name__ == "__main__":
    sys.exit(main())
