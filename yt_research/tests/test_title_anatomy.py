import json
import re
from datetime import timedelta
from types import SimpleNamespace

import pytest

from ytr import analyze, title_anatomy as ta
from ytr.db import connect
from ytr.util import iso, utcnow

NOW = utcnow()


def ago(d):
    return iso(NOW - timedelta(days=d))


def feat(**kw):
    f = dict(hook_type="other", emotion="none", specificity="medium", time_sensitivity="evergreen",
             audience_pain_or_desire="x", topic_cluster="misc", real_person_story=False, clickbait_level="low")
    f.update(kw)
    return f


class FakeClient:
    """Parses '<index>: <title>' lines from the prompt; answers with feat_fn(title) keyed by index."""

    def __init__(self, feat_fn=None, drop=(), refuse=(), fail=()):
        self.calls, self.kwargs, self.batches = 0, [], []
        self.feat_fn, self.drop, self.refuse, self.fail = feat_fn or (lambda t: feat()), set(drop), set(refuse), set(fail)
        self.messages = self

    def create(self, **kw):
        self.calls += 1
        self.kwargs.append(kw)
        if self.calls in self.fail:
            raise RuntimeError("boom")
        lines = [m for m in re.findall(r"^(\d+): (.*)$", kw["messages"][0]["content"], re.M)]
        self.batches.append(lines)
        usage = SimpleNamespace(input_tokens=1000, output_tokens=100)
        if self.calls in self.refuse:
            return SimpleNamespace(stop_reason="refusal", content=[], usage=usage)
        items = [{"index": int(i), **self.feat_fn(t)} for i, t in lines if int(i) not in self.drop]
        return SimpleNamespace(stop_reason="end_turn", usage=usage,
                               content=[SimpleNamespace(type="text", text=json.dumps({"items": items}))])


def add_video(con, vid, topic_id, pub_days, views, title=None, kind="disc", channel="c", dur=1200):
    con.execute("""INSERT OR IGNORE INTO videos(video_id, channel_id, title, published_at, category_id, duration_s, format_class)
                   VALUES(?,?,?,?,?,?,?)""",
                (vid, channel, title if title is not None else f"title {vid}", ago(pub_days), "27", dur, "long"))
    con.execute("INSERT OR REPLACE INTO video_snapshots VALUES(?,?,?,?,?)", (vid, ago(0), views, 0, 0))
    if kind == "disc":
        con.execute("INSERT OR IGNORE INTO discoveries(video_id, topic_id) VALUES(?,?)", (vid, topic_id))
    else:
        con.execute("INSERT OR IGNORE INTO date_samples VALUES(?,?,?,?)", (vid, topic_id, 1, ago(0)))


def build(n_hit=25, n_base=25):
    con = connect(":memory:")
    con.executescript(analyze.CHANNEL_METRICS_CREATE)
    con.execute("INSERT INTO topics(query, lang, region, genre) VALUES('q','ja','JP','g1')")
    for i in range(n_hit):
        add_video(con, f"hit{i}", 1, 20 + i, 60_000 + i * 1000, title=f"【第{i}回】hit {i}", dur=1200 + i * 10)
    for i in range(n_base):
        add_video(con, f"base{i}", 1, 30 + i, 1000 + i, title=f"plain base {i}", kind="date", channel="c2", dur=600)
    con.execute("""INSERT INTO channel_metrics(channel_id, subscribers, channel_age_days, uploads_90d)
                   VALUES('c', 5000, 100, 9)""")
    con.execute("""INSERT INTO channel_metrics(channel_id, subscribers, channel_age_days, uploads_90d)
                   VALUES('c2', 100000, 2000, 30)""")
    con.commit()
    return con


def run(con, tmp_path, **kw):
    kw.setdefault("client", FakeClient())
    return ta.run(con, ["g1"], limit=kw.pop("limit", 25), report_dir=tmp_path / "rep", now=NOW, **kw)


def test_batching_idempotency_cost_and_report(tmp_path):
    con = build()
    client = FakeClient()
    res, st = run(con, tmp_path, client=client)
    assert client.calls == 2 and [len(b) for b in client.batches] == [25, 25]
    assert [i for i, _ in client.batches[0]] == [str(i) for i in range(25)]
    assert st["classified"] == 50 and st["api_calls"] == 2
    assert st["tokens_in"] == 2000 and st["tokens_out"] == 200
    assert st["cost_usd"] == pytest.approx(2000 / 1e6 * 0.10 + 200 / 1e6 * 0.50)
    k = client.kwargs[0]
    assert k["model"] == "claude-haiku-5-5" and not {"temperature", "top_p", "thinking"} & set(k)
    assert k["output_config"]["format"]["type"] == "json_schema"
    assert con.execute("SELECT COUNT(*) FROM title_features").fetchone()[0] == 50
    client2 = FakeClient()
    _, st2 = run(con, tmp_path, client=client2)
    assert client2.calls == 0 and st2["cost_usd"] == 0
    assert con.execute("SELECT COUNT(*) FROM title_features").fetchone()[0] == 50
    md = (tmp_path / "rep" / "title_anatomy.md").read_text(encoding="utf-8")
    for s in ("注意事項", "相関", "生存者バイアス", "視聴維持率", "サンプルが小さい", "タイトル・長さ",
              "小型モデル", "プレイブック案", "仮説", "リフト", "ジャンル: g1", "数値の事実", "話題クラスタ"):
        assert s in md
    assert "データ不足" not in md


def test_batches_split_over_25(tmp_path):
    con = build(n_hit=30, n_base=30)
    client = FakeClient()
    run(con, tmp_path, client=client, limit=30)
    assert [len(b) for b in client.batches] == [25, 25, 10]


def test_max_calls_cap(tmp_path):
    con = build(30, 30)
    client = FakeClient()
    _, st = run(con, tmp_path, client=client, max_calls=2, limit=30)
    assert client.calls == 2 and st["skipped_by_cap"] == 10 and st["classified"] == 50


def test_missing_item_failure_and_refusal(tmp_path):
    con = build()
    client = FakeClient(drop={3}, refuse={2})
    _, st = run(con, tmp_path, client=client)
    assert st["classify_failed"] == 1 and st["refusals"] == 25 and st["classified"] == 24
    assert con.execute("SELECT COUNT(*) FROM title_features WHERE features_json LIKE '%unclassified%'").fetchone()[0] == 25
    client2 = FakeClient(fail={1})
    _, st2 = run(build(), tmp_path, client=client2)
    assert st2["classify_failed"] == 25 and st2["classified"] == 25


def test_lift_rules(tmp_path):
    con = build()
    # hits: first 20 question; baseline: 2 question (<3 -> no lift), others other
    def f(t):
        if t.startswith("【"):
            return feat(hook_type="question", emotion="fear")
        n = int(t.split()[-1])
        return feat(hook_type="question" if n < 2 else "other", emotion="fear" if n < 10 else "none")
    run(con, tmp_path, client=FakeClient(feat_fn=f))
    hits, base = ta.visual_style.select_groups(con, "g1", 25, NOW)
    r = ta.genre_result(con, "g1", hits, base, NOW)
    rows = {t["value"]: t for t in r["tables"]["hook_type"]}
    assert rows["question"]["base_n"] == 2 and rows["question"]["lift"] is None
    assert rows["other"]["hit_n"] == 0
    emo = {t["value"]: t for t in r["tables"]["emotion"]}
    assert emo["fear"]["lift"] == pytest.approx(1.0 / (10 / 25))
    # derived attributes: all hit titles contain digits and brackets, no baseline title has brackets
    br = {t["value"]: t for t in r["tables"]["has_bracket"]}
    assert br["true"]["hit_share"] == 1.0 and br["true"]["base_n"] == 0 and br["true"]["lift"] is None
    dg = {t["value"]: t for t in r["tables"]["has_digit"]}
    assert dg["true"]["hit_n"] == 25 and dg["true"]["base_n"] == 25 and dg["true"]["lift"] == pytest.approx(1.0)
    # sorted by lift desc, None last
    lifts = [t["lift"] for t in r["tables"]["emotion"]]
    assert lifts == sorted(lifts, key=lambda x: (x is None, -(x or 0)))


def test_insufficient_data(tmp_path):
    con = build(n_hit=10, n_base=25)
    client = FakeClient()
    res, _ = run(con, tmp_path, client=client)
    assert client.calls == 0 and res[0]["insufficient"] == ["hit"] and not res[0]["tables"]
    md = (tmp_path / "rep" / "title_anatomy.md").read_text(encoding="utf-8")
    assert "データ不足" in md and "相関" in md
    assert "### " not in md.split("ジャンル: g1")[1]


def test_numeric_facts_and_clusters(tmp_path):
    con = build()
    def f(t):
        if t.startswith("【"):
            n = int(re.search(r"hit (\d+)", t).group(1))
            cl = "ancient civilizations" if n < 10 else ("new NISA reform" if n < 15 else f"solo {n}")
            return feat(topic_cluster=cl)
        return feat(topic_cluster="ancient civilizations")   # baseline must not feed clusters
    res, _ = run(con, tmp_path, client=FakeClient(feat_fn=f))
    r = res[0]
    cl = {c["cluster"]: c for c in r["clusters"]}
    assert set(cl) == {"ancient civilizations", "new nisa reform"}      # singletons dropped (<3), lowercased
    assert cl["ancient civilizations"]["n"] == 10 and cl["new nisa reform"]["n"] == 5
    assert len(cl["new nisa reform"]["examples"]) == 2
    # ranking in the report: by count first, by median views second
    md = (tmp_path / "rep" / "title_anatomy.md").read_text(encoding="utf-8")
    sec = md.split("ヒット本数の多い順")[1]
    assert sec.index("ancient civilizations") < sec.index("new nisa reform")
    assert "再生数中央値の高い順" in md
    best = sorted(r["clusters"], key=lambda c: (-c["median_views"], -c["n"]))[0]["cluster"]
    assert best == "new nisa reform"                                   # views grow with i, so hits 10..14 beat 0..9
    h, b = r["facts"]["hit"], r["facts"]["base"]
    assert h["median_long_min"] == pytest.approx(sorted(20 + i * 10 / 60 for i in range(25))[12])
    assert b["median_long_min"] == pytest.approx(10)
    assert h["digit_share"] == 1.0 and b["digit_share"] == 1.0 and h["bracket_share"] == 1.0 and b["bracket_share"] == 0
    assert h["median_subs"] == 5000 and b["median_subs"] == 100000
    assert h["young_share"] == 1.0 and b["young_share"] == 0.0
    assert h["median_uploads_90d"] == pytest.approx(9 * 90 / ta.config.WINDOW_DAYS)
    assert h["median_vpd"] > b["median_vpd"]
    # playbook: +-25% of the hit median, labelled as hypotheses
    m = h["median_long_min"]
    assert f"{m * 0.75:.1f}〜{m * 1.25:.1f} 分" in md
    assert "仮説" in md and "上位5件" in md and "上位3点" in md


def test_missing_channel_metrics_table_is_tolerated(tmp_path):
    con = build()
    con.execute("DROP TABLE channel_metrics")
    res, _ = run(con, tmp_path)
    assert res[0]["facts"]["hit"]["median_subs"] is None
    assert "-" in (tmp_path / "rep" / "title_anatomy.md").read_text(encoding="utf-8")


def test_missing_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with pytest.raises(ta.MissingApiKey):
        ta.run(build(), ["g1"], report_dir=tmp_path)


def test_schema_shape():
    item = ta.SCHEMA["properties"]["items"]["items"]
    assert ta.SCHEMA["additionalProperties"] is False and item["additionalProperties"] is False
    assert set(item["required"]) == set(item["properties"]) == {
        "index", "hook_type", "emotion", "specificity", "time_sensitivity", "audience_pain_or_desire",
        "topic_cluster", "real_person_story", "clickbait_level"}
    assert item["properties"]["hook_type"]["enum"][0] == "question" and len(item["properties"]["hook_type"]["enum"]) == 10
    assert item["properties"]["real_person_story"] == {"type": "boolean"}


def test_cli_subcommand_wired(monkeypatch, tmp_path):
    from ytr import __main__ as m
    seen = {}
    monkeypatch.setattr(ta, "run", lambda con, genres, limit, max_calls: seen.update(g=genres, l=limit, c=max_calls) or ({}, {}))
    monkeypatch.setattr(m, "connect", lambda p: build())
    assert m.main(["title-anatomy", "--genre", "a", "--genre", "b"]) == 0
    assert seen == dict(g=["a", "b"], l=60, c=40)
