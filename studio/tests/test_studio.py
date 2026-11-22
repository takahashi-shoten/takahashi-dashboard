import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import brief, ledger, pipeline, script  # noqa: E402


def make_ytr(path):
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE videos(video_id, channel_id, title, published_at, duration_s, format_class, category_id);
    CREATE TABLE video_snapshots(video_id, observed_at, view_count);
    CREATE TABLE channels(channel_id, title);
    CREATE TABLE topics(topic_id, genre);
    CREATE TABLE discoveries(video_id, topic_id);
    INSERT INTO channels VALUES('c1','Chan');
    INSERT INTO topics VALUES(1,'cozy_life');
    INSERT INTO videos VALUES('v1','c1','Hit A','2026-11-01',600,'long','22'),('v2','c1','Music','2026-11-01',200,'long','10'),('v3','c1','Small','2026-11-01',600,'long','22');
    INSERT INTO video_snapshots VALUES('v1','t',900000),('v2','t',900000),('v3','t',100);
    INSERT INTO discoveries VALUES('v1',1),('v2',1),('v3',1);""")
    c.commit(); c.close()


class FakeClient:
    def __init__(self):
        self.calls = []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        data = dict(title_options=["T1"], original_angle="a", hook="h",
                    sections=[dict(heading="s", narration="n", visual_prompt="v", seconds=30)],
                    description="d", tags=["x"], fact_claims_to_verify=["c"], ai_disclosure_needed=True)
        return NS(stop_reason="end_turn", model="claude-opus-5-5", usage=NS(input_tokens=2000, output_tokens=6000),
                  content=[NS(type="text", text=json.dumps(data))])


def test_brief_excludes_music_and_small(tmp_path):
    db = tmp_path / "ytr.sqlite"; make_ytr(db)
    b = brief.make_brief(str(db), "cozy_life", "en")
    assert [h["title"] for h in b["reference_hits"]] == ["Hit A"]


def test_script_cost_is_measured_and_logged(tmp_path):
    db = tmp_path / "ytr.sqlite"; make_ytr(db)
    con = ledger.connect(":memory:")
    pid = brief.create_project(con, brief.make_brief(str(db), "cozy_life", "en"))
    fake = FakeClient()
    data = script.write_script(con, fake, pid, max_fixes=0)
    assert data["title_options"] == ["T1"]
    k = fake.calls[0]
    assert k["model"] == "claude-opus-5-5" and k["fallbacks"] == "default" and "temperature" not in k
    # 2000 in * $4/M + 6000 out * $20/M = 0.008 + 0.12
    assert abs(ledger.profit(con, pid)["cost_usd"] - 0.128) < 1e-9


def test_status_is_honest_and_publish_needs_approval(tmp_path):
    con = ledger.connect(":memory:")
    pid = brief.create_project(con, dict(genre="g", lang="en", platform="youtube", reference_hits=[]))
    st = {s: v for s, v, _ in pipeline.status(con, pid)}
    assert st["brief"] == "done" and st["voice"] == "not_connected" and st["visuals"] == "not_connected"
    assert not pipeline.is_publish_approved(con, pid)
    pipeline.approve_publish(con, pid, "owner")
    assert pipeline.is_publish_approved(con, pid)


def test_script_length_is_corrected_by_reprompting(tmp_path):
    db = tmp_path / "ytr.sqlite"; make_ytr(db)
    con = ledger.connect(":memory:")
    pid = brief.create_project(con, brief.make_brief(str(db), "cozy_life", "ja"))

    def script_with(n):
        return dict(title_options=["T"], original_angle="a", hook="h", description="d", tags=["x"], fact_claims_to_verify=[],
                    ai_disclosure_needed=True, sections=[dict(heading="s", narration="あ" * n, visual_prompt="v", seconds=1)])

    sizes = iter([1000, 2600])          # first too short (target 2640 = 480 s * 5.5), then within tolerance
    calls = []

    class C(FakeClient):
        def _create(self, **kw):
            calls.append(kw)
            r = super()._create(**kw)
            r.content[0].text = json.dumps(script_with(next(sizes)))
            return r
    c = C()
    data = script.write_script(con, c, pid, target_seconds=480)
    assert len(calls) == 2 and "EXPAND" in calls[1]["messages"][0]["content"]
    assert abs(script.narration_chars(data) - 2640) / 2640 <= 0.15
    assert data["sections"][0]["seconds"] == round(2600 / 5.5)
    assert ledger.profit(con, pid)["cost_usd"] > 0.2           # two calls were paid for and recorded
