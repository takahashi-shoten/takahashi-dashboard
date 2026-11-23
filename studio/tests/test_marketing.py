import json
import types

from studio import ledger, marketing


class FakeClient:
    def __init__(self, data):
        self.data = data
        self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(create=self.create))
        self.last = None

    def create(self, **kw):
        self.last = kw
        return types.SimpleNamespace(usage=types.SimpleNamespace(input_tokens=100, output_tokens=50), model=kw["model"],
                                     stop_reason="end_turn", content=[types.SimpleNamespace(type="text", text=json.dumps(self.data))])


def _data():
    v = lambda p: dict(principle=p, title="t", thumbnail_text="x", hook="h", cta="c", why_ja="w", evidence_basis="hypothesis", claims_to_verify=[])
    return dict(audience="a", pain_or_desire="p", variants=[v("AIDA"), v("PAS")], recommended_index=0, learning_note_ja="n")


def test_generate_and_judge(tmp_path):
    con = ledger.connect(tmp_path / "s.sqlite")
    cl = FakeClient(_data())
    grp, data = marketing.generate_copy(con, cl, 1, "新NISA", "ja")
    assert "past_lessons" in cl.last["messages"][0]["content"]
    ids = [r["experiment_id"] for r in con.execute("SELECT experiment_id FROM experiments WHERE grp=?", (grp,))]
    assert len(ids) == 2
    marketing.record_result(con, ids[0], "ctr", 200, 20)
    marketing.record_result(con, ids[1], "ctr", 200, 5)
    assert marketing.judge_group(con, grp)["verdict"] == "inconclusive"      # too little data: no winner called
    marketing.record_result(con, ids[0], "ctr", 5000, 500)
    marketing.record_result(con, ids[1], "ctr", 5000, 300)
    assert marketing.judge_group(con, grp)["verdict"] == "decided"
    assert marketing.past_lessons(con)[0]["verdict"] in ("winner", "loser")


def test_equal_rates_inconclusive(tmp_path):
    con = ledger.connect(tmp_path / "s.sqlite")
    grp, _ = marketing.generate_copy(con, FakeClient(_data()), 1, "t", "ja")
    ids = [r["experiment_id"] for r in con.execute("SELECT experiment_id FROM experiments")]
    for i in ids:
        marketing.record_result(con, i, "ctr", 5000, 250)
    assert marketing.judge_group(con, grp)["verdict"] == "inconclusive"
