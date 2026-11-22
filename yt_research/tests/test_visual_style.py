import io
import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

from ytr import config, visual_style as vs
from ytr.db import connect
from ytr.util import iso, utcnow

NOW = utcnow()


def ago(d):
    return iso(NOW - timedelta(days=d))


def tiny_jpeg():
    try:
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (8, 8), (200, 30, 30)).save(buf, "JPEG")
        return buf.getvalue()
    except ImportError:  # Pillow is only a test nicety; any bytes work for the fake
        return b"\xff\xd8\xff\xe0fakejpeg\xff\xd9"


class FakeSession:
    def __init__(self, fail=()):
        self.urls, self.fail, self.img = [], set(fail), tiny_jpeg()

    def get(self, url, timeout=None):
        self.urls.append((url, timeout))
        vid = url.split("/vi/")[1].split("/")[0]
        if vid in self.fail:
            return SimpleNamespace(status_code=404, content=b"")
        return SimpleNamespace(status_code=200, content=self.img)


FEAT = dict(medium="photo", ai_look="unlikely", mood="neutral", palette="warm", subject="object",
            face_present=True, text_overlay="small", emotion="neutral")


class FakeClient:
    def __init__(self, refuse=(), feat_fn=None):
        self.calls, self.refuse = 0, set(refuse)
        self.kwargs = []
        self.feat_fn = feat_fn or (lambda n: FEAT)
        self.messages = self

    def create(self, **kw):
        self.calls += 1
        self.kwargs.append(kw)
        n = self.calls
        usage = SimpleNamespace(input_tokens=1000, output_tokens=100)
        if n in self.refuse:
            return SimpleNamespace(stop_reason="refusal", content=[], usage=usage)
        return SimpleNamespace(stop_reason="end_turn", usage=usage,
                               content=[SimpleNamespace(type="text", text=json.dumps(self.feat_fn(n)))])


def add_video(con, vid, topic_id, pub_days, views, cat="27", kind="disc"):
    con.execute("INSERT OR IGNORE INTO videos(video_id, channel_id, title, published_at, category_id) VALUES(?,?,?,?,?)",
                (vid, "c", "t", ago(pub_days), cat))
    con.execute("INSERT OR REPLACE INTO video_snapshots VALUES(?,?,?,?,?)", (vid, ago(0), views, 0, 0))
    if kind == "disc":
        con.execute("INSERT OR IGNORE INTO discoveries(video_id, topic_id) VALUES(?,?)", (vid, topic_id))
    elif kind == "date":
        con.execute("INSERT OR IGNORE INTO date_samples VALUES(?,?,?,?)", (vid, topic_id, 1, ago(0)))


def build(n_hit=25, n_base=25):
    con = connect(":memory:")
    con.execute("INSERT INTO topics(query, lang, region, genre) VALUES('q','ja','JP','g1')")
    con.execute("INSERT INTO topics(query, lang, region, genre) VALUES('q2','ja','JP','other')")
    for i in range(n_hit):
        add_video(con, f"hit{i}", 1, 20 + i, 60_000 + i * 1000)
    add_video(con, "music1", 1, 10, 9_000_000, cat="10")
    add_video(con, "lowviews", 1, 10, 100)
    add_video(con, "oldhit", 1, 200, 9_000_000)
    for i in range(n_base):
        add_video(con, f"base{i}", 1, 30 + i, 1000 + i, kind="date")
    add_video(con, "base_music", 1, 30, 10, cat="10", kind="date")
    add_video(con, "base_young", 1, 3, 10, kind="date")
    add_video(con, "hit0", 1, 20, 60_000, kind="date")   # also date-sampled: must be excluded from baseline
    con.commit()
    return con


def test_selection(tmp_path):
    con = build()
    hits, base = vs.select_groups(con, "g1", limit=40, now=NOW)
    assert len(hits) == 25 and "music1" not in hits and "oldhit" not in hits and "lowviews" not in hits
    assert "base_music" not in base and "base_young" not in base
    assert not set(hits) & set(base) and len(base) == 25
    hits2, base2 = vs.select_groups(con, "g1", limit=40, now=NOW)
    assert (hits, base) == (hits2, base2)
    h5, b5 = vs.select_groups(con, "g1", limit=5, now=NOW)
    assert len(h5) == 5 and len(b5) == 5
    # ordered by views/day: hit0 (60k / 20d) beats hit24 (84k / 44d)
    assert h5[0] == "hit0" or h5.index("hit0") < 3


def run(con, tmp_path, **kw):
    kw.setdefault("session", FakeSession())
    kw.setdefault("client", FakeClient())
    return vs.run(con, ["g1"], limit=25, report_dir=tmp_path / "rep", now=NOW, **kw)


def test_run_idempotent_cost_and_report(tmp_path, monkeypatch):
    con = build()
    session, client = FakeSession(), FakeClient()
    res, st = run(con, tmp_path, session=session, client=client)
    assert client.calls == 50 and st["classified_calls"] == 50
    assert st["tokens_in"] == 50_000 and st["tokens_out"] == 5_000
    assert st["cost_usd"] == pytest.approx(50_000 / 1e6 * 0.10 + 5_000 / 1e6 * 0.50)
    assert all(t == (vs.FETCH_TIMEOUT) for _, t in session.urls)
    assert session.urls[0][0].startswith("https://i.ytimg.com/vi/") and session.urls[0][0].endswith("/hqdefault.jpg")
    k = client.kwargs[0]
    assert k["model"] == "claude-haiku-5-5" and k["max_tokens"] <= 700
    assert not {"temperature", "top_p", "thinking"} & set(k)
    assert k["output_config"]["format"]["type"] == "json_schema"
    assert k["messages"][0]["content"][0]["source"]["media_type"] == "image/jpeg"
    assert con.execute("SELECT COUNT(*) FROM thumb_features").fetchone()[0] == 50
    # second run: nothing new
    client2, session2 = FakeClient(), FakeSession()
    _, st2 = run(con, tmp_path, session=session2, client=client2)
    assert client2.calls == 0 and not session2.urls and st2["cost_usd"] == 0
    assert con.execute("SELECT COUNT(*) FROM thumb_features").fetchone()[0] == 50
    md = (tmp_path / "rep" / "visual_style.md").read_text(encoding="utf-8")
    for s in ("注意事項", "相関", "生存者バイアス", "保存していません", "学習", "リフト", "上位3点", "ジャンル: g1"):
        assert s in md
    assert "データ不足" not in md


def test_lift_computation(tmp_path):
    con = build()
    # hits: first 15 are illustration, rest photo; baseline all photo except 5 illustration
    def feat(n):
        f = dict(FEAT)
        f["medium"] = "illustration_2d" if (n <= 15 or 26 <= n <= 30) else "photo"
        return f
    # classification order is by pending list: hits first, then baseline (single-thread order not guaranteed
    # with the pool), so compute expectations from stored rows instead
    run(con, tmp_path, client=FakeClient(feat_fn=feat))
    hits, base = vs.select_groups(con, "g1", 25, NOW)
    r = vs.genre_result(con, "g1", hits, base)
    rows = {t["value"]: t for t in r["tables"]["medium"]}
    assert rows["illustration_2d"]["hit_n"] + rows["photo"]["hit_n"] == 25
    t = rows["photo"]
    assert t["lift"] == pytest.approx(t["hit_share"] / t["base_share"])
    assert r["tables"]["medium"][0]["lift"] >= r["tables"]["medium"][-1]["lift"] or r["tables"]["medium"][-1]["lift"] is None
    # constant attribute: baseline count of rare value < 3 -> no lift
    assert all(t["lift"] is None for t in r["tables"]["medium"] if t["base_n"] < vs.MIN_BASE_COUNT)


def test_refusal_and_failures(tmp_path):
    con = build()
    session = FakeSession(fail={"hit1", "base1"})
    client = FakeClient(refuse={3})
    _, st = run(con, tmp_path, session=session, client=client)
    assert st["fetch_failed"] == 2 and st["refusals"] == 1
    assert client.calls == 48   # failed fetches never reach the API
    assert con.execute("SELECT COUNT(*) FROM thumb_features").fetchone()[0] == 48
    assert con.execute("SELECT COUNT(*) FROM thumb_features WHERE features_json LIKE '%unclassified%'").fetchone()[0] == 1
    # refusal rows are excluded from stats
    hits, base = vs.select_groups(con, "g1", 25, NOW)
    r = vs.genre_result(con, "g1", hits, base)
    assert r["hit_n"] + r["base_n"] == 47


def test_insufficient_data(tmp_path):
    con = build(n_hit=10, n_base=25)
    client = FakeClient()
    res, st = run(con, tmp_path, client=client)
    assert client.calls == 0                      # not worth spending on a genre that cannot be evaluated
    assert res[0]["insufficient"] == ["hit"] and not res[0]["tables"]
    md = (tmp_path / "rep" / "visual_style.md").read_text(encoding="utf-8")
    assert "データ不足" in md and "リフト" in md and "相関" in md
    assert "### " not in md.split("ジャンル: g1")[1]


def test_group_with_few_classified_is_insufficient(tmp_path):
    con = build()
    res, _ = run(con, tmp_path, session=FakeSession(fail={f"hit{i}" for i in range(10)}))
    assert res[0]["insufficient"] == ["hit"]


def test_max_images_cap(tmp_path):
    con = build()
    client = FakeClient()
    _, st = run(con, tmp_path, client=client, max_images=30)
    assert client.calls == 30 and st["skipped_by_cap"] == 20


def test_no_thumbnails_on_disk(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    con = build()
    run(con, tmp_path)
    assert not [p for p in tmp_path.rglob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    assert [p.name for p in (tmp_path / "rep").iterdir()] == ["visual_style.md"]


def test_missing_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    con = build()
    with pytest.raises(vs.MissingApiKey):
        vs.run(con, ["g1"], report_dir=tmp_path, session=FakeSession())


def test_schema_shape():
    assert vs.SCHEMA["additionalProperties"] is False
    assert set(vs.SCHEMA["required"]) == set(vs.SCHEMA["properties"]) == {
        "medium", "ai_look", "mood", "palette", "subject", "face_present", "text_overlay", "emotion"}
    assert vs.PRICE["claude-haiku-5-5"] == (0.10, 0.50)


def test_baseline_falls_back_to_same_channel_non_hits_and_is_labelled(tmp_path):
    con = build(n_hit=25, n_base=0)                      # no date-sampled baseline at all
    for i in range(30):                                  # same channel "c": uploads that did not reach the hit threshold
        add_video(con, f"nonhit{i}", 1, 25 + i, 2000 + i, kind="none")
    add_video(con, "nonhit_young", 1, 3, 50, kind="none")        # too young: excluded
    add_video(con, "nonhit_music", 1, 30, 50, cat="10", kind="none")
    con.commit()
    hits, base = vs.select_groups(con, "g1", limit=25)
    assert len(hits) == 25 and len(base) == 25
    assert all(b.startswith("nonhit") for b in base) and "nonhit_young" not in base and "nonhit_music" not in base
    assert not set(hits) & set(base)
    assert "同じチャンネル" in vs.BASELINE_SOURCE["g1"]
    hits2, base2 = vs.select_groups(build(n_hit=25, n_base=25), "g1", limit=25)
    assert "date_samples" in vs.BASELINE_SOURCE["g1"] and all(b.startswith("base") for b in base2)
