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
