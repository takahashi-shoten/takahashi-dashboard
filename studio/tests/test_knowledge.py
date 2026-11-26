from studio import knowledge as kb
from studio import ledger


def con(tmp_path):
    c = ledger.connect(tmp_path / "k.sqlite")
    kb.init(c)
    return c


def test_single_source_confidence_is_capped_and_search_ranks(tmp_path):
    c = con(tmp_path)
    k1 = kb.add(c, "hook", "the video opens with a concrete number and a question in the first 5 seconds", "https://y/1", "00:03", confidence=0.95)
    kb.add(c, "cta", "ends with a free-resource offer", "https://y/2", "25:10")
    assert c.execute("SELECT confidence FROM knowledge WHERE knowledge_id=?", (k1,)).fetchone()[0] == kb.SINGLE_SOURCE_CAP
    r = kb.search(c, "opening hook number question")
    assert r[0]["knowledge_id"] == k1 and kb.search(c, "", category="cta")[0]["category"] == "cta"


def test_ingest_keeps_facts_and_drops_empty_ones(tmp_path):
    c = con(tmp_path)
    n = kb.ingest_analysis(c, {"findings": [dict(category="hook", time="00:02", observed_fact="says 'ten years ago I had nothing'", interpretation="relatable low start", source="audio", confidence=0.8),
                                           dict(category="cta", time="25:00", observed_fact="", interpretation="probably asks to subscribe")]}, "https://y/1")
    assert n == 1 and c.execute("SELECT status, origin FROM knowledge").fetchone()[:] == ("observed", "video_analysis:audio")


def test_internal_success_never_becomes_market_validated_but_market_failure_invalidates(tmp_path):
    c = con(tmp_path)
    k = kb.add(c, "title", "numbers in titles raise CTR", confidence=0.5)
    for _ in range(3):
        kb.record_outcome(c, k, "E-1", "worked", "internal review", market_result=False)
    assert c.execute("SELECT status FROM knowledge WHERE knowledge_id=?", (k,)).fetchone()[0] == "tested_internal"
    for _ in range(4):
        kb.record_outcome(c, k, "E-2", "failed", "CTR below channel median at 7d", market_result=True)
    assert c.execute("SELECT status FROM knowledge WHERE knowledge_id=?", (k,)).fetchone()[0] == "invalidated"
    assert kb.search(c, "numbers titles") == []                                   # invalidated knowledge is not used any more
    assert kb.search(c, "numbers titles", include_invalidated=True)


def test_for_task_records_which_knowledge_was_used(tmp_path):
    c = con(tmp_path)
    k = kb.add(c, "hook", "open with a scene, not a greeting")
    assert kb.for_task(c, "write opening hook", used_in="E-3")[0]["knowledge_id"] == k
    assert c.execute("SELECT used_in, task FROM knowledge_uses").fetchone()[:] == ("E-3", "write opening hook")


def test_second_market_success_on_validated_knowledge_becomes_repeat_validated(tmp_path):
    c = con(tmp_path)
    k = kb.add(c, "title", "specific numbers in the title", confidence=0.5)
    for _ in range(2):
        kb.record_outcome(c, k, "E1", "worked", market_result=True)
    assert c.execute("SELECT status FROM knowledge WHERE knowledge_id=?", (k,)).fetchone()[0] == "market_validated"
    kb.record_outcome(c, k, "E2", "worked", market_result=True)
    assert c.execute("SELECT status FROM knowledge WHERE knowledge_id=?", (k,)).fetchone()[0] == "repeat_validated"
    kb.record_outcome(c, k, "E3", "failed", market_result=True)
    assert c.execute("SELECT status FROM knowledge WHERE knowledge_id=?", (k,)).fetchone()[0] in ("repeat_validated", "invalidated")


def _kb(tmp_path):
    import sqlite3
    from studio import knowledge as k
    con = sqlite3.connect(tmp_path / "k.sqlite")
    con.row_factory = sqlite3.Row
    k.add(con, "hook", "冒頭で常識を否定", confidence=0.5, status="observed")
    k.add(con, "hook", "弱い仮説", confidence=0.2, status="hypothesis")
    k.add(con, "trust", "出典明示", confidence=0.5, status="observed")
    bad = k.add(con, "retention", "棄却済み", confidence=0.5, status="observed")
    con.execute("UPDATE knowledge SET status='invalidated' WHERE knowledge_id=?", (bad,))
    con.commit()
    return con


def test_consult_logs_use_and_skips_invalidated(tmp_path):
    from studio import knowledge as k
    con = _kb(tmp_path)
    got = k.consult(con, used_in="brief:test")
    cats = [g["category"] for g in got]
    assert cats == ["hook", "trust"] and got[0]["content"] == "冒頭で常識を否定"   # strongest first, one per category, invalidated skipped
    assert got[0]["status"] == "observed" and "conditions" in got[0]
    uses = con.execute("SELECT used_in, task FROM knowledge_uses").fetchall()
    assert len(uses) == 2 and all(u["used_in"] == "brief:test" for u in uses)


def test_brief_carries_labelled_knowledge_and_can_be_switched_off(tmp_path):
    import sqlite3
    from studio import brief
    db = tmp_path / "ytr.sqlite"
    c = sqlite3.connect(db)
    c.executescript("""CREATE TABLE videos(video_id, title, channel_id, duration_s, format_class, published_at, category_id);
    CREATE TABLE video_snapshots(video_id, observed_at, view_count); CREATE TABLE channels(channel_id, title);
    CREATE TABLE discoveries(video_id, topic_id); CREATE TABLE topics(topic_id, genre);""")
    c.commit()
    con = _kb(tmp_path)
    con.close()
    b = brief.make_brief(str(db), "g", "ja", kb_path=tmp_path / "k.sqlite")
    assert [k["category"] for k in b["knowledge_used"]] == ["hook", "trust"] and "NOT established" in b["knowledge_note"]
    assert brief.make_brief(str(db), "g", "ja", kb_path=tmp_path / "k.sqlite", use_knowledge=False)["knowledge_used"] == []
    n = sqlite3.connect(tmp_path / "k.sqlite").execute("SELECT COUNT(*) FROM knowledge_uses").fetchone()[0]
    assert n == 2    # the switched-off call logged nothing


def test_register_attaches_knowledge_when_terms_given(tmp_path, monkeypatch):
    import json
    from studio import experiments as ex, ledger, measure
    _kb(tmp_path).close()
    monkeypatch.setenv("STUDIO_KNOWLEDGE_DB", str(tmp_path / "k.sqlite"))
    p = dict(hypothesis="h", audience="a", desire="d", title="t", thumbnail_text="x", structure="s", length_s=0, tools=["x"], knowledge_terms=["出典"])
    p.update({k: "未確認" for k in ex.PLAN_FIELDS})
    f = tmp_path / "plan.json"
    f.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
    con = ledger.connect(tmp_path / "e.sqlite")
    ex.init(con)
    eid = measure.register(con, str(f))
    used = json.loads(con.execute("SELECT knowledge_used_json FROM experiments WHERE experiment_id=?", (eid,)).fetchone()[0])
    assert [u["status"] for u in used] == ["observed"] and used[0]["reason"].startswith("matched terms")
    import sqlite3
    assert sqlite3.connect(tmp_path / "k.sqlite").execute("SELECT used_in FROM knowledge_uses").fetchone()[0] == eid
