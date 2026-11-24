import pytest

from studio import experiments as ex
from studio import ledger


def plan(**kw):
    p = dict(hypothesis="h", audience="a", desire="curiosity", title="t", thumbnail_text="x", structure="s", length_s=1200, tools=["claude"])
    p.update({k: "未確認" for k in ex.PLAN_FIELDS})
    p.update(kw)
    return p


def test_plan_requires_all_ten_facts_and_a_hypothesis(tmp_path):
    con = ledger.connect(tmp_path / "e.sqlite")
    bad = plan()
    del bad["failure_metrics"]
    with pytest.raises(ValueError):
        ex.create_experiment(con, bad)
    eid = ex.create_experiment(con, plan())
    assert eid.startswith("E-") and eid.endswith("-01")
    assert ex.create_experiment(con, plan()).endswith("-02")


def test_cost_is_summed_from_ledger(tmp_path):
    con = ledger.connect(tmp_path / "e.sqlite")
    eid = ex.create_experiment(con, plan())
    con.execute("INSERT INTO costs(project_id,stage,provider,model,input_tokens,output_tokens,usd,created_at) VALUES(7,'script','a','m',1,1,0.5,'t')")
    con.execute("INSERT INTO costs(project_id,stage,provider,model,input_tokens,output_tokens,usd,created_at) VALUES(7,'images','g','m',0,1,2.0,'t')")
    assert ex.attach_production(con, eid, 7, minutes=14) == 2.5


def test_diagnosis_never_concludes_from_too_little_data(tmp_path):
    con = ledger.connect(tmp_path / "e.sqlite")
    eid = ex.create_experiment(con, plan())
    assert ex.diagnose(con, eid, "7d")["diagnosis"] == "no_data"
    ex.record_result(con, eid, "7d", dict(impressions=300, ctr=0.01, views=3, avg_view_pct=5))
    d = ex.diagnose(con, eid, "7d")
    assert d["diagnosis"] == "too_few_impressions" and d["confidence"] == "low"       # a 1% CTR on 300 impressions is not a verdict
    ex.record_result(con, eid, "24h", dict(views=10))
    assert ex.diagnose(con, eid, "24h")["diagnosis"] == "impressions_unavailable"


def test_low_ctr_is_attributed_to_one_factor_once_a_baseline_exists(tmp_path):
    con = ledger.connect(tmp_path / "e.sqlite")
    for ctr in (0.06, 0.05, 0.07):
        e = ex.create_experiment(con, plan())
        ex.record_result(con, e, "7d", dict(impressions=5000, ctr=ctr, views=250, avg_view_pct=40))
    t = ex.create_experiment(con, plan())
    ex.record_result(con, t, "7d", dict(impressions=5000, ctr=0.02, views=100, avg_view_pct=40))
    d = ex.diagnose(con, t, "7d")
    assert d["diagnosis"] == "low_click_through" and "ONLY the thumbnail" in d["next_change"]
    # without a baseline the CTR is not judged
    con2 = ledger.connect(tmp_path / "e2.sqlite")
    t2 = ex.create_experiment(con2, plan())
    ex.record_result(con2, t2, "7d", dict(impressions=5000, ctr=0.02, views=100, avg_view_pct=40))
    assert ex.diagnose(con2, t2, "7d")["diagnosis"] == "inconclusive"
    assert ex.diagnose(con2, t2, "7d")["evidence"]["ctr_benchmark"].startswith("未確認")


def test_early_drop_off_is_only_suspected_and_names_missing_data(tmp_path):
    con = ledger.connect(tmp_path / "e.sqlite")
    for ctr in (0.05, 0.05, 0.05):
        e = ex.create_experiment(con, plan())
        ex.record_result(con, e, "7d", dict(impressions=4000, ctr=ctr, views=200, avg_view_pct=40))
    t = ex.create_experiment(con, plan())
    ex.record_result(con, t, "7d", dict(impressions=4000, ctr=0.05, views=200, avg_view_pct=10))
    d = ex.diagnose(con, t, "7d")
    assert d["diagnosis"] == "early_drop_off_suspected" and d["confidence"] == "low"
    assert any("retention curve" in m for m in d["missing_data"])
    ex.save_analysis(con, t, "7d", d)
    assert ex.spend_summary(con)["analyzed"] == 1
