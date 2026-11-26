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


class _R:
    def __init__(self, code, body):
        self.status_code, self._b, self.text, self.headers = code, body, str(body), {}

    def json(self):
        return self._b


class _Sess:
    def __init__(self, scope_ok=True, channel=True):
        self.scope_ok, self.channel = scope_ok, channel

    def post(self, url, **kw):
        return _R(200, {"access_token": "TOKEN-SECRET"})

    def get(self, url, **kw):
        if "tokeninfo" in url:
            sc = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/yt-analytics.readonly"
            return _R(200, {"scope": sc if self.scope_ok else "https://www.googleapis.com/auth/youtube"})
        if "youtubeanalytics" in url:
            return _R(200, {"columnHeaders": [], "rows": [[1]]})
        return _R(200, {"items": [{"id": "UC1", "snippet": {"title": "静かなる逆転劇"}, "statistics": {"subscriberCount": "0", "videoCount": "0"}}] if self.channel else []})


def test_connection_check_reports_each_step_and_never_leaks_secrets(monkeypatch):
    for k in ("YT_OAUTH_CLIENT_ID", "YT_OAUTH_CLIENT_SECRET", "YT_OAUTH_REFRESH_TOKEN"):
        monkeypatch.setenv(k, "x-" + k)
    out = youtube.connection_check(_Sess())
    assert out["token"] == "ok" and out["scopes_missing"] == [] and out["analytics"] == "ok"
    assert out["channel"]["title"] == "静かなる逆転劇"
    assert "TOKEN-SECRET" not in str(out) and "x-YT_OAUTH" not in str(out)
    bad = youtube.connection_check(_Sess(scope_ok=False, channel=False))
    assert len(bad["scopes_missing"]) == 2 and "no channel" in bad["channel"]


def test_connection_check_without_secrets_says_not_connected(monkeypatch):
    for k in ("YT_OAUTH_CLIENT_ID", "YT_OAUTH_CLIENT_SECRET", "YT_OAUTH_REFRESH_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    out = youtube.connection_check(_Sess())
    assert out["token"].startswith("not connected") and not any(out["secrets_present"].values())
