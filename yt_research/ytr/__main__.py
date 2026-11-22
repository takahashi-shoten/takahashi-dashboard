"""CLI: python -m ytr {run,verify-seeds,analyze,status}"""
import argparse
import json
import sys

from . import config, topics, analyze, report, llm, seeds
from .api import YouTubeClient, QuotaExceeded, BudgetExhausted, ApiError
from .collect import Cycle
from .db import connect, log_error
from .util import iso, utcnow


def start_run(con):
    cur = con.execute("INSERT INTO runs(started_at, status) VALUES(?, 'running')", (iso(utcnow()),))
    con.commit()
    return cur.lastrowid


def finish_run(con, run_id, status, summary, units, error=None):
    con.execute("UPDATE runs SET finished_at=?, status=?, units_used=?, summary_json=?, error=? WHERE run_id=?",
                (iso(utcnow()), status, units, json.dumps(summary, default=str), error, run_id))
    con.commit()


def do_analyze(con, use_llm):
    analyze.compute_channel_metrics(con)
    gms = analyze.compute_genre_metrics(con)
    analyze.ensure_rule_hypotheses(con, gms.keys())
    llm_result = None
    if use_llm and llm.available() and gms:
        try:
            llm_result = llm.propose(con, gms)
        except Exception as e:  # noqa: BLE001 - LLM failure must not break data pipeline
            log_error(con, None, "llm", repr(e))
            llm_result = {"error": repr(e)[:300]}
    changes = analyze.evaluate_hypotheses(con, gms)
    expanded = topics.expand_from_hits(con)
    return gms, changes, llm_result, expanded


def _visual_style(a):
    from . import visual_style
    if not a.genre:
        raise SystemExit("visual-style: --genre is required")
    con = connect(config.DB_PATH)
    _, stats = visual_style.run(con, a.genre, limit=a.limit or 40, max_images=a.max_images)
    print(json.dumps(stats, indent=1))
    return 0


def _title_anatomy(a):
    from . import title_anatomy
    if not a.genre:
        raise SystemExit("title-anatomy: --genre is required")
    con = connect(config.DB_PATH)
    _, stats = title_anatomy.run(con, a.genre, limit=a.limit or 60, max_calls=a.max_calls)
    print(json.dumps(stats, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ytr")
    ap.add_argument("cmd", choices=["run", "verify-seeds", "analyze", "status", "visual-style", "title-anatomy"])
    ap.add_argument("--genre", action="append", default=[])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-images", type=int, default=200)
    ap.add_argument("--max-calls", type=int, default=40)
    ap.add_argument("--budget", type=int, default=config.RUN_BUDGET)
    ap.add_argument("--searches", type=int, default=config.SEARCHES_PER_RUN)
    ap.add_argument("--no-llm", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "visual-style":
        return _visual_style(a)
    if a.cmd == "title-anatomy":
        return _title_anatomy(a)
    con = connect(config.DB_PATH)
    topics.ensure_seeds(con)

    # recover runs that died mid-way (container killed etc.)
    con.execute("UPDATE runs SET status='aborted', finished_at=? WHERE status='running'", (iso(utcnow()),))
    con.commit()

    if a.cmd == "status":
        print(json.dumps(report.counts(con), indent=1))
        return 0
    if a.cmd == "analyze":
        gms, changes, llm_result, expanded = do_analyze(con, not a.no_llm)
        report.write(con, {"analyze_only": True, "expanded_topics": expanded}, gms, changes, llm_result=llm_result)
        print((config.REPORT_DIR / "latest.md").read_text())
        return 0

    run_id = start_run(con)
    yt = YouTubeClient(con, run_id, budget=a.budget)
    seed_results, status, err, summary = None, "ok", None, {}
    try:
        if a.cmd == "verify-seeds":
            seed_results = seeds.verify(con, yt)
            summary = {"seed_cases": len(seed_results)}
        else:
            if con.execute("SELECT COUNT(*) FROM seed_cases WHERE verified_at IS NOT NULL").fetchone()[0] == 0:
                seed_results = seeds.verify(con, yt)
            summary = Cycle(con, yt, run_id).run(searches=a.searches)
    except (QuotaExceeded, BudgetExhausted, ApiError) as e:
        status, err = "failed", repr(e)
        log_error(con, run_id, "run", err)
    summary["units_this_run"] = yt.spent
    summary["quota_remaining_today"] = yt.remaining_today()
    gms, changes, llm_result, expanded = do_analyze(con, not a.no_llm)
    summary["expanded_topics"] = expanded
    if seed_results is None and con.execute("SELECT COUNT(*) FROM seed_cases").fetchone()[0]:
        seed_results = [(r["video_id"], r["label"], r["reported_views"], r["verification"])
                        for r in con.execute("SELECT * FROM seed_cases")]
    report.write(con, summary, gms, changes, seed_results, llm_result)
    finish_run(con, run_id, status, summary, yt.spent, err)
    print(json.dumps({"status": status, "error": err, **summary}, ensure_ascii=False, indent=1, default=str))
    return 0 if status == "ok" else 2


def _entry():
    try:
        return main()
    finally:
        # fold the WAL into the main file so the DB is a single portable file
        try:
            c = connect(config.DB_PATH)
            c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            c.close()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(_entry())
