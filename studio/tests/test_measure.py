from studio import experiments as ex
from studio import ledger, measure, youtube
from tests.test_experiments import plan


def fake_snapshot_factory(values):
    def snap(con, project_id, video_id, published_at, session=None, now=None, checkpoint=None):
        youtube.ensure_schema(con)
        obs = "2026-12-01T00:00:00Z"
        for m, v in values.items():
            youtube._store(con, project_id, video_id, obs, 168.0, m, v)
        youtube._store(con, project_id, video_id, obs, 168.0, "checkpoint", 168.0, "checkpoint", checkpoint)
        con.commit()
        return {"stored": len(values), "age_hours": 168.0, "unavailable_metrics": ["estimatedRevenue"]}
    return snap


def test_measure_stores_checkpoint_diagnoses_and_is_idempotent(tmp_path, monkeypatch):
    con = ledger.connect(tmp_path / "m.sqlite")
    eid = ex.create_experiment(con, plan())
    ex.mark_published(con, eid, "VID1", "2026-11-24T00:00:00Z")
    monkeypatch.setattr(youtube, "snapshot", fake_snapshot_factory(
        {"views": 120.0, "averageViewDuration": 300.0, "averageViewPercentage": 30.0, "videoThumbnailImpressionsClickRate": 4.5,
         "videoThumbnailImpressions": 2500.0, "subscribersGained": 3.0, "subscribersLost": 1.0}))
    from datetime import datetime, timezone
    now = datetime(2026, 12, 2, tzinfo=timezone.utc)            # 8 days after publication: 24h, 72h and 7d are due
    done = measure.run_once(con, now=now)
    assert {d["checkpoint"] for d in done} == {"24h", "72h", "7d"}
    r = con.execute("SELECT * FROM experiment_results WHERE experiment_id=? AND checkpoint='7d'", (eid,)).fetchone()
    assert r["impressions"] == 2500 and abs(r["ctr"] - 0.045) < 1e-9 and r["subs_gained"] == 2 and r["revenue_usd"] is None   # revenue: 未取得
    assert measure.run_once(con, now=now) == []                  # nothing is measured twice
    assert "E-" in measure.report(con)


def test_results_empty_without_checkpoint(tmp_path):
    con = ledger.connect(tmp_path / "m.sqlite")
    assert measure.results_from_metrics(con, "NOPE", "7d") == {}
