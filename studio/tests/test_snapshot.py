import json
import sqlite3

import pytest

from studio import experiments as ex
from studio import knowledge as kb
from studio import ledger, snapshot


def _populate(tmp_path):
    db = tmp_path / "reg.sqlite"
    con = ledger.connect(db)
    ex.init(con)
    kb.init(con)
    kb.add(con, "action", "tiny first step: one minute a day", "https://y/1", "08:50", confidence=0.5)
    ex.create_experiment(con, dict(hypothesis="h", audience="a", desire="d", title="t", thumbnail_text="x", structure="s", length_s=60, tools=["claude"],
                                   **{k: "未確認" for k in ex.PLAN_FIELDS}, market="salon", channel_type="short_video"))
    con.commit()
    con.close()
    return db


def test_export_verify_restore_roundtrip_is_exact_and_append_only(tmp_path):
    db = _populate(tmp_path)
    s1 = snapshot.export(db, tmp_path / "snaps")
    s2 = snapshot.export(db, tmp_path / "snaps")
    assert s1 != s2 and s1.exists() and s2.exists()                    # a second export never overwrites the first
    assert snapshot.verify(s1) == (True, [])
    new = tmp_path / "restored.sqlite"
    counts = snapshot.restore(s1, new)
    assert counts["experiments"] == 1 and counts["knowledge"] == 1
    a, b = sqlite3.connect(db), sqlite3.connect(new)
    for t in ("experiments", "knowledge", "knowledge_history"):
        assert a.execute(f"SELECT * FROM {t} ORDER BY rowid").fetchall() == b.execute(f"SELECT * FROM {t} ORDER BY rowid").fetchall()
    with pytest.raises(FileExistsError):
        snapshot.restore(s1, new)                                       # never overwrites an existing DB


def test_corrupted_or_missing_files_fail_verification_and_block_restore(tmp_path):
    db = _populate(tmp_path)
    s = snapshot.export(db, tmp_path / "snaps")
    (s / "knowledge.jsonl").write_text('{"tampered": true}\n', encoding="utf-8")
    ok, problems = snapshot.verify(s)
    assert not ok and any("knowledge.jsonl" in p for p in problems)
    with pytest.raises(ValueError):
        snapshot.restore(s, tmp_path / "x.sqlite")
    s2 = snapshot.export(db, tmp_path / "snaps2")
    (s2 / "experiments.jsonl").unlink()
    assert not snapshot.verify(s2)[0]
