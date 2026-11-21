import json
from datetime import timedelta

import pytest

from ytr import config, topics, analyze, report
from ytr.api import YouTubeClient, QuotaExceeded
from ytr.collect import Cycle
from ytr.db import connect
from ytr.util import parse_duration, format_class, iso, utcnow, median

NOW = utcnow()


def ago(days):
    return iso(NOW - timedelta(days=days))


class Resp:
    def __init__(self, code, body):
        self.status_code, self._b = code, body
        self.text = json.dumps(body)

    def json(self):
        return self._b


class FakeYT:
    """Simulates videos/channels/search/playlistItems over an in-memory world."""

    def __init__(self):
        self.calls = []
        self.fail_next = []
        self.channels = {}
        self.videos = {}

    def add_channel(self, cid, subs, age_days, n, views, dur="PT8M"):
        self.channels[cid] = dict(id=cid, snippet=dict(title=cid, publishedAt=ago(age_days)),
                                  statistics=dict(subscriberCount=str(subs), videoCount=str(n), viewCount="1"),
                                  contentDetails=dict(relatedPlaylists=dict(uploads="UU" + cid)))
        for i in range(n):
            vid = f"{cid}_v{i}"
            self.videos[vid] = dict(id=vid, snippet=dict(channelId=cid, channelTitle=cid, title=f"t{i}",
                                                         publishedAt=ago(15 + i * 3), categoryId="27", tags=["roman army", "history"]),
                                    contentDetails=dict(duration=dur), status={},
                                    statistics=dict(viewCount=str(views[i % len(views)]), likeCount="1"))

    def get(self, url, params=None, headers=None, timeout=None):
        ep = url.rsplit("/", 1)[1]
        self.calls.append(ep)
        if self.fail_next:
            return self.fail_next.pop(0)
        if ep == "search":
            ids = sorted(self.videos, key=lambda v: -int(self.videos[v]["statistics"]["viewCount"]))[:50]
            return Resp(200, {"items": [{"id": {"videoId": v}} for v in ids]})
        if ep == "videos":
            return Resp(200, {"items": [self.videos[i] for i in params["id"].split(",") if i in self.videos]})
        if ep == "channels":
            return Resp(200, {"items": [self.channels[i] for i in params["id"].split(",") if i in self.channels]})
        if ep == "playlistItems":
            cid = params["playlistId"][2:]
            items = [dict(contentDetails=dict(videoId=v, videoPublishedAt=d["snippet"]["publishedAt"]))
                     for v, d in self.videos.items() if d["snippet"]["channelId"] == cid]
            items.sort(key=lambda x: x["contentDetails"]["videoPublishedAt"], reverse=True)
            return Resp(200, {"items": items})
        raise AssertionError(ep)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "REPORT_DIR", tmp_path / "reports")
    con = connect(":memory:")
    topics.ensure_seeds(con)
    fake = FakeYT()
    # replicable small/new channel: 8 videos, all ~80k
    fake.add_channel("NEWHIT", 20_000, 120, 8, [80_000, 60_000, 90_000])
    # one-hit wonder: 1 big, rest tiny
    fake.add_channel("ONEHIT", 5_000, 900, 8, [2_000_000, 1_000, 800, 1_200, 900, 700, 1_100, 600])
    # big established channel
    fake.add_channel("BIG", 3_000_000, 3000, 6, [500_000])
    yt = YouTubeClient(con, run_id=1, budget=5000, session=fake, sleep=lambda s: None)
    return con, fake, yt


def test_duration_and_format():
    assert parse_duration("PT1H2M3S") == 3723
    assert parse_duration("PT45S") == 45
    assert format_class(45) == "short_likely"
    assert format_class(120) == "ambiguous"
    assert format_class(600) == "long"
    assert median([3, 1, 2]) == 2 and median([1, 2, 3, 4]) == 2.5


def test_cycle_dedup_snapshots_and_metrics(env):
    con, fake, yt = env
    stats = Cycle(con, yt, 1).run(searches=2, audit_reserve=0)
    assert stats["searches"] == 2
    # second search returns the same videos -> all duplicates, not new rows
    assert stats["duplicate_videos"] >= stats["new_videos"] > 0
    n_videos = con.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    assert n_videos == len(fake.videos)
    assert stats["channels_audited"] == 3
    # snapshot time series kept per (video, observed_at)
    assert con.execute("SELECT COUNT(*) FROM video_snapshots").fetchone()[0] >= n_videos

    analyze.compute_channel_metrics(con)
    m = {r["channel_id"]: r for r in con.execute("SELECT * FROM channel_metrics")}
    assert m["NEWHIT"]["replicable"] == 1 and m["NEWHIT"]["is_new"] == 1 and m["NEWHIT"]["is_small"] == 1
    assert m["ONEHIT"]["replicable"] == 0          # single viral hit is not replicable
    assert m["ONEHIT"]["top1_share"] > 0.9
    assert m["NEWHIT"]["audited"] == 1


def test_quota_accounting_and_quota_exceeded(env):
    con, fake, yt = env
    yt.search_videos("x", ago(90))
    assert yt.spent == 100 and yt.used_today() == 100
    fake.fail_next = [Resp(403, {"error": {"message": "quota", "errors": [{"reason": "quotaExceeded"}]}})]
    with pytest.raises(QuotaExceeded):
        yt.videos(["a"])


def test_retry_on_5xx(env):
    con, fake, yt = env
    fake.fail_next = [Resp(503, {"error": {"message": "busy"}})]
    assert yt.channels(["BIG"])[0]["id"] == "BIG"
    # failed attempt is also recorded (it consumed quota)
    assert con.execute("SELECT COUNT(*) FROM api_calls WHERE http_status=503").fetchone()[0] == 1


def test_budget_stops_cycle_cleanly(env):
    con, fake, yt = env
    yt.budget = 150
    stats = Cycle(con, yt, 1).run(searches=5, audit_reserve=0)
    assert stats["searches"] + stats["date_samples"] == 1 and yt.spent <= 150


def test_hypothesis_lifecycle(env):
    con, *_ = env
    test = dict(metric="replicable_new_channels", op=">=", threshold=2, support_metric="audited_channels", min_support=3)
    assert analyze.evaluate(test, {"replicable_new_channels": 5, "audited_channels": 1})[0] == "insufficient_data"
    assert analyze.evaluate(test, {"replicable_new_channels": 5, "audited_channels": 4})[0] == "supported"
    assert analyze.evaluate(test, {"replicable_new_channels": 0, "audited_channels": 9})[0] == "refuted"


def test_full_analyze_and_report(env):
    con, fake, yt = env
    Cycle(con, yt, 1).run(searches=1, audit_reserve=0)
    analyze.compute_channel_metrics(con)
    gms = analyze.compute_genre_metrics(con)
    analyze.ensure_rule_hypotheses(con, gms)
    changes = analyze.evaluate_hypotheses(con, gms)
    assert changes  # untested -> insufficient_data etc.
    text = report.write(con, {"t": 1}, gms, changes)
    assert "重複排除件数" in text and "NEWHIT" in text
    assert (config.REPORT_DIR / "exports" / "channel_metrics.csv").exists()


def test_topic_scheduler_rotates_genres(env):
    con, *_ = env
    sel = topics.select_topics(con, 10)
    assert len({r["genre"] for r in sel}) == 10


def test_ai_signal():
    row = dict(synthetic_media=None, title="Roman camp | AI animation", description="", tags_json="[]")
    assert analyze.ai_signal(row) == "keyword"
    row = dict(synthetic_media=1, title="x", description="", tags_json="[]")
    assert analyze.ai_signal(row) == "declared"


def test_legacy_v2_analyze_case_ported(env):
    """Same expectation as legacy youtube_audit_v2/test_analyze.py: views 1000/60000/100000 -> median 60000, 2 hits."""
    con, fake, yt = env
    fake.channels.clear(); fake.videos.clear()
    fake.add_channel("DEMO", 1000, 400, 3, [1_000, 60_000, 100_000])
    Cycle(con, yt, 1).run(searches=1, audit_reserve=0)
    analyze.compute_channel_metrics(con)
    r = con.execute("SELECT * FROM channel_metrics WHERE channel_id='DEMO'").fetchone()
    assert r["long_median"] == 60_000 and r["hits_n"] == 2 and abs(r["hit_share"] - 2 / 3) < 1e-9
    assert r["replicable"] == 0     # only 3 mature uploads < REPL_MIN_UPLOADS: one strong month is not proof


def test_seed_queries_include_legacy():
    legacy = {"雑学 なぜ", "都市伝説 考察", "AI cinematic story", "world maps explained"}
    assert legacy <= {q for *_, q in topics.SEEDS}
    assert len({(q, l, r) for _, l, r, q in topics.SEEDS}) == len(topics.SEEDS)  # no duplicate seeds


def test_date_sampling_base_rates(env):
    con, fake, yt = env
    stats = Cycle(con, yt, 1).run(searches=4, audit_reserve=0)
    assert stats["date_samples"] == 1 and stats["date_sample_videos"] > 0
    assert con.execute("SELECT COUNT(*) FROM search_runs WHERE mode='date'").fetchone()[0] == 1
    analyze.compute_channel_metrics(con)
    gm = analyze.compute_genre_metrics(con)
    g = next(m for m in gm.values() if m["base_videos"])
    # fake world: 3 channels, NEWHIT/BIG reach 50k, ONEHIT has one 2M video -> all 3 channels "reach"
    assert g["base_channels"] == 3 and g["base_channel_hit_rate"] == 1.0
    assert 0 < g["base_hit_rate"] < 1


def test_migration_on_old_db(tmp_path):
    import sqlite3
    p = tmp_path / "old.sqlite"
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE topics(topic_id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT, lang TEXT, region TEXT,"
              " genre TEXT, source TEXT, status TEXT DEFAULT 'active', created_at TEXT, runs INTEGER DEFAULT 0,"
              " last_run_at TEXT, yield_score REAL, notes TEXT, UNIQUE(query, lang, region))")
    c.commit(); c.close()
    con = connect(p)
    assert "date_sampled_at" in {r[1] for r in con.execute("PRAGMA table_info(topics)")}


def test_priority_genres_searched_first(env):
    con, *_ = env
    sel = topics.select_topics(con, 9)
    assert {r["genre"] for r in sel} <= set(config.PRIORITY_GENRES)
    assert len({r["genre"] for r in sel}) == 9      # still one per genre


def test_report_has_coverage_section(env):
    con, fake, yt = env
    Cycle(con, yt, 1).run(searches=2, audit_reserve=0)
    analyze.compute_channel_metrics(con)
    gms = analyze.compute_genre_metrics(con)
    text = report.write(con, {}, gms, [])
    assert "調査の進み具合" in text and "検索未実施" in text
