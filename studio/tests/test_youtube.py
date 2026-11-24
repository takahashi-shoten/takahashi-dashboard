import json
from datetime import datetime, timedelta, timezone

import pytest

from studio import ledger, youtube as yt
from studio.errors import NotConnected

SECRETS = {"YT_OAUTH_CLIENT_ID": "cid-SECRET1", "YT_OAUTH_CLIENT_SECRET": "csec-SECRET2",
           "YT_OAUTH_REFRESH_TOKEN": "rtok-SECRET3"}


class R:
    def __init__(self, status=200, js=None, headers=None):
        self.status_code, self._js, self.headers = status, js if js is not None else {}, headers or {}

    def json(self):
        return self._js


class Fake:
    def __init__(self, analytics=None):
        self.calls, self.analytics = [], analytics

    def post(self, url, **kw):
        self.calls.append(("POST", url, kw))
        if url == yt.TOKEN_URL:
            return R(200, {"access_token": "AT"})
        if url == yt.UPLOAD_URL:
            return R(200, headers={"Location": "https://upload.example/sess"})
        return R(404)

    def put(self, url, **kw):
        self.calls.append(("PUT", url, kw))
        if url.startswith("https://upload.example"):
            return R(200, {"id": "VID1", "status": {"privacyStatus": "private"}})
        return R(200, {"id": "VID1", "status": json.loads(kw["data"])["status"]})

    def get(self, url, **kw):
        self.calls.append(("GET", url, kw))
        if url == yt.ANALYTICS_URL:
            return self.analytics(kw["params"])
        if url.endswith("/videos"):
            return R(200, {"items": [{"id": "VID1", "statistics": {"viewCount": "5"},
                                      "status": {"privacyStatus": "private"}}]})
        return R(200, {"items": []})


@pytest.fixture(autouse=True)
def env(monkeypatch):
    for k, v in SECRETS.items():
        monkeypatch.setenv(k, v)


@pytest.fixture
def con():
    c = ledger.connect(":memory:")
    yield c
    c.close()


@pytest.fixture
def video(tmp_path):
    p = tmp_path / "v.mp4"
    p.write_bytes(b"x" * 10)
    return p


def test_token_exchange():
    s = Fake()
    assert yt.access_token(s) == "AT"
    assert s.calls[0][2]["data"]["grant_type"] == "refresh_token"


def test_not_connected(monkeypatch):
    monkeypatch.delenv("YT_OAUTH_REFRESH_TOKEN")
    with pytest.raises(NotConnected, match="YT_OAUTH_REFRESH_TOKEN"):
        yt.access_token(Fake())


def test_resumable_upload_default_private(video, con):
    s = Fake()
    vid = yt.upload_video(video, "t", "d", ["a"], session=s, con=con, project_id=1)
    assert vid == "VID1"
    init = [c for c in s.calls if c[1] == yt.UPLOAD_URL][0][2]
    assert init["params"] == {"uploadType": "resumable", "part": "snippet,status"}
    st = json.loads(init["data"])["status"]
    assert st["privacyStatus"] == "private" and st["containsSyntheticMedia"] is True
    assert st["selfDeclaredMadeForKids"] is False
    assert [c for c in s.calls if c[0] == "PUT"][0][2]["data"] == b"x" * 10
    row = con.execute("SELECT * FROM steps WHERE stage='youtube_upload'").fetchone()
    art = json.loads(row["artifact_json"])
    assert art["video_id"] == "VID1" and art["privacy"] == "private"


def test_public_refused_without_approval(video, con):
    s = Fake()
    with pytest.raises(yt.ApprovalRequired):
        yt.upload_video(video, "t", privacy="public", session=s, con=con, project_id=1)
    assert s.calls == []  # nothing sent
    with pytest.raises(yt.ApprovalRequired):
        yt.set_privacy("VID1", "public", con, 1, session=s)
    yt.approve(con, 2, "publish_public", "me")
    with pytest.raises(yt.ApprovalRequired):  # approval is per project
        yt.set_privacy("VID1", "public", con, 1, session=s)


def test_public_allowed_with_approval(video, con):
    yt.approve(con, 1, "publish_public", "me")
    s = Fake()
    assert yt.upload_video(video, "t", privacy="public", session=s, con=con, project_id=1) == "VID1"
    yt.set_privacy("VID1", "unlisted", con, 1, session=s)
    yt.set_privacy("VID1", "public", con, 1, session=s)


def analytics_fn(bad):
    def f(params):
        ms = params["metrics"].split(",")
        if any(m in bad for m in ms):
            return R(400, {"error": {"message": "nope"}})
        dims = params.get("dimensions")
        hdr = ([{"name": dims}] if dims else []) + [{"name": m} for m in ms]
        row = (["X"] if dims else []) + [1] * len(ms)
        return R(200, {"columnHeaders": hdr, "rows": [row]})
    return f


def test_unavailable_metric_fallback():
    s = Fake(analytics_fn({"impressions", "estimatedRevenue"}))
    rep = yt.analytics_report(["VID1"], "2026-01-01", "2026-01-02",
                              yt.CORE_METRICS + ["impressions", "estimatedRevenue"], None, s)
    assert rep["unavailable_metrics"] == ["impressions", "estimatedRevenue"]
    assert rep["metrics"] == yt.CORE_METRICS and rep["rows"]
    assert [c for c in s.calls if c[1] == yt.ANALYTICS_URL][0][2]["params"]["filters"] == "video==VID1"


def test_snapshot_and_checkpoints(con):
    pub = datetime(2026, 1, 1, tzinfo=timezone.utc)
    now = pub + timedelta(hours=80)
    assert yt.due_checkpoints(pub, now) == ["24h", "72h"]
    assert yt.due_checkpoints(pub, pub + timedelta(hours=1)) == []
    s = Fake(analytics_fn({"videoThumbnailImpressions", "videoThumbnailImpressionsClickRate", "impressions", "impressionsClickThroughRate", "estimatedRevenue"}))
    res = yt.snapshot(con, 1, "VID1", pub, s, now, checkpoint="24h")
    assert set(res["unavailable_metrics"]) == {"videoThumbnailImpressions", "videoThumbnailImpressionsClickRate", "impressions", "impressionsClickThroughRate", "estimatedRevenue"}
    assert yt.due_checkpoints(pub, now, con, "VID1") == ["72h"]
    m = {r["metric"] for r in con.execute("SELECT metric FROM video_metrics")}
    assert {"views", "data_api.viewCount"} <= m
    d = con.execute("SELECT dimension, dimension_value FROM video_metrics WHERE dimension='country'").fetchone()
    assert d["dimension_value"] == "X"


def test_no_secret_leak(caplog):
    class Bad(Fake):
        def post(self, url, **kw):
            return R(401, {"error": "invalid_grant", "error_description": "rtok-SECRET3 csec-SECRET2"})
    with pytest.raises(yt.YouTubeError) as e:
        yt.access_token(Bad())
    for v in SECRETS.values():
        assert v not in str(e.value) and v not in caplog.text
