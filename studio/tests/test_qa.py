import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import qa  # noqa: E402
from studio.errors import NotConnected  # noqa: E402

LONG_JA = "これは十分に長いナレーションの文章です。落ち着いた声で、ゆっくりと日常の小さな工夫について話していきます。"
LONG_EN = "This narration is long enough to pass the minimum word count check for a section in the script."


def make_script(narration=LONG_EN, **kw):
    s = dict(title_options=["A quiet morning"], original_angle="a", hook="h",
             sections=[dict(heading="s", narration=narration, visual_prompt="v", seconds=120)],
             description="d", tags=["x"], fact_claims_to_verify=[], ai_disclosure_needed=True)
    s.update(kw)
    return s


def ids(findings, sev=None):
    return {f["id"] for f in findings if sev is None or f["severity"] == sev}


def test_clean_script_has_no_findings():
    assert qa.rule_checks(make_script(), "en") == []


@pytest.mark.parametrize("text,lang,fid", [
    (LONG_JA + "この方法なら必ず治る", "ja", "medical_claim"),
    (LONG_EN + " It cures anxiety.", "en", "medical_claim"),
    (LONG_EN + " We offer guaranteed results.", "en", "medical_claim"),
    (LONG_JA + "元本保証で絶対儲かる", "ja", "investment_promise"),
    (LONG_EN + " This is guaranteed profit.", "en", "investment_promise"),
    (LONG_EN + " Here is how to commit suicide.", "en", "unsafe_content"),
    (LONG_JA + "自殺の方法を紹介", "ja", "unsafe_content"),
])
def test_block_rules(text, lang, fid):
    assert fid in ids(qa.rule_checks(make_script(text), lang), "block")


def test_description_is_also_scanned():
    assert "medical_claim" in ids(qa.rule_checks(make_script(description="100%効果"), "ja"), "block")


def test_missing_ai_disclosure_blocks():
    s = make_script()
    del s["ai_disclosure_needed"]
    assert "ai_disclosure_missing" in ids(qa.rule_checks(s, "en"), "block")


def test_numbers_without_claims_warn():
    text = LONG_EN + " Sales rose 40% in 2019."
    assert "unlisted_numbers" in ids(qa.rule_checks(make_script(text), "en"), "warn")
    assert "unlisted_numbers" not in ids(qa.rule_checks(make_script(text, fact_claims_to_verify=["40%"]), "en"))


def test_duration_and_short_sections_warn():
    s = make_script("too short")
    s["sections"][0]["seconds"] = 10
    assert {"duration", "short_section"} <= ids(qa.rule_checks(s, "en"), "warn")
    assert "short_section" in ids(qa.rule_checks(make_script("短い"), "ja"))
    assert "short_section" not in ids(qa.rule_checks(make_script(LONG_JA), "ja"))


def test_title_copy_warning():
    s = make_script(title_options=["How I Cook Rice!", "how i cook rice"])
    assert "title_copy" in ids(qa.rule_checks(s, "en", ["How I cook rice"]), "warn")
    assert "title_copy" not in ids(qa.rule_checks(make_script(), "en", ["How I cook rice"]))
    assert "title_copy" not in ids(qa.rule_checks(s, "en"))


class FakeClient:
    def __init__(self, verdict="pass", unverified=(), stop="end_turn"):
        self.calls = []
        self.beta = NS(messages=NS(create=self._create))
        self.data = dict(verdict=verdict, issues=[], unverified_claims=list(unverified))
        self.stop = stop

    def _create(self, **kw):
        self.calls.append(kw)
        return NS(stop_reason=self.stop, model="claude-opus-5-5", usage=NS(input_tokens=100, output_tokens=50),
                  content=[NS(type="text", text=json.dumps(self.data))])


def test_claude_reviewer_pattern_and_usage():
    c = FakeClient(unverified=["x"])
    r = qa.ClaudeReviewer(c).review(make_script(), "en")
    k = c.calls[0]
    assert k["model"] == "claude-opus-5-5" and k["fallbacks"] == "default" and k["thinking"] == {"type": "adaptive"}
    assert not {"temperature", "top_p"} & set(k)
    assert k["output_config"]["format"]["schema"]["additionalProperties"] is False
    assert "no web access" in k["system"].lower()
    assert r["reviewer"] == "claude" and r["usage"] == {"input_tokens": 100, "output_tokens": 50}
    assert r["unverified_claims"] == ["x"]


def test_claude_refusal_is_not_a_pass():
    assert qa.ClaudeReviewer(FakeClient(stop="refusal")).review(make_script(), "en")["verdict"] == "revise"


def test_gemini_not_connected(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(NotConnected, match="GEMINI_API_KEY"):
        qa.GeminiReviewer().review(make_script(), "en")
    assert qa.GeminiReviewer().describe()["status"] == "not_connected"


def fake(name, verdict="pass", unverified=()):
    return NS(review=lambda s, l: qa._result(name, verdict, [], list(unverified)))


def run(tmp_path, reviewers, script=None):
    (tmp_path / "script.json").write_text(json.dumps(script or make_script()), encoding="utf-8")
    out = qa.run_qa(tmp_path, "en", reviewers)
    assert json.loads((tmp_path / "qa.json").read_text(encoding="utf-8")) == out
    return out


def test_mock_only_can_never_pass(tmp_path):
    out = run(tmp_path, [qa.MockReviewer(), qa.MockReviewer(), qa.MockReviewer()])
    assert out["decision"] == "needs_human"
    assert qa.MockReviewer().describe()["status"] == "mock"


def test_one_real_plus_mock_is_not_pass(tmp_path):
    assert run(tmp_path, [fake("claude"), qa.MockReviewer()])["decision"] == "needs_human"


def test_two_real_passes_pass(tmp_path):
    out = run(tmp_path, [fake("claude"), fake("gemini")])
    assert out["decision"] == "pass" and out["unverified_claims"] == []


def test_unverified_claims_need_human(tmp_path):
    out = run(tmp_path, [fake("claude", unverified=["c1"]), fake("gemini", unverified=["c1"])])
    assert out["decision"] == "needs_human" and out["unverified_claims"] == ["c1"]


def test_revise_needs_human_and_block_blocks(tmp_path):
    assert run(tmp_path, [fake("claude"), fake("gemini", "revise")])["decision"] == "needs_human"
    assert run(tmp_path, [fake("claude"), fake("gemini", "block")])["decision"] == "blocked"


def test_rule_block_overrides_passing_reviewers(tmp_path):
    out = run(tmp_path, [fake("claude"), fake("gemini")], script=make_script(LONG_EN + " guaranteed profit"))
    assert out["decision"] == "blocked" and out["rule_findings"]


def test_describe():
    assert qa.describe()["stage"] == "qa" and qa.describe()["status"] == "mock"


def test_web_reviewer_resumes_paused_turn_and_parses_json():
    from types import SimpleNamespace as NS
    calls = []

    class C:
        def __init__(self):
            self.beta = NS(messages=NS(create=self.create))

        def create(self, **kw):
            calls.append(kw)
            if len(calls) == 1:
                return NS(stop_reason="pause_turn", model="claude-opus-5-5", content=[NS(type="server_tool_use")],
                          usage=NS(input_tokens=100, output_tokens=10, server_tool_use=NS(web_search_requests=3)))
            return NS(stop_reason="end_turn", model="claude-opus-5-5",
                      content=[NS(type="text", text='Findings:\n{"verdict":"pass","issues":[],"unverified_claims":["x"]}')],
                      usage=NS(input_tokens=50, output_tokens=20, server_tool_use=NS(web_search_requests=2)))
    r = qa.WebClaudeReviewer(C()).review(make_script(), "ja")
    assert len(calls) == 2 and calls[0]["tools"][0]["type"] == "web_search_20260209"
    assert calls[1]["messages"][-1]["role"] == "assistant"              # resumed with the paused content, no extra user text
    assert r["usage"] == {"input_tokens": 150, "output_tokens": 30, "web_searches": 5}
    assert r["verdict"] == "pass" and r["unverified_claims"] == ["x"] and r["reviewer"] == "claude_web"


def test_web_reviewer_never_passes_on_bad_json():
    from types import SimpleNamespace as NS

    class C:
        def __init__(self):
            self.beta = NS(messages=NS(create=lambda **kw: NS(stop_reason="end_turn", model="claude-opus-5-5", content=[NS(type="text", text="all good")],
                                                              usage=NS(input_tokens=1, output_tokens=1))))
    assert qa.WebClaudeReviewer(C()).review(make_script(), "ja")["verdict"] == "revise"


def test_same_vendor_reviewers_do_not_count_as_two():
    ok = {"verdict": "pass", "issues": [], "unverified_claims": [], "usage": None, "model": None}
    dec, reasons = qa.decide([], [dict(ok, reviewer="claude"), dict(ok, reviewer="claude_web")])
    assert dec == "needs_human" and "independent" in reasons[0]
    dec, _ = qa.decide([], [dict(ok, reviewer="claude_web"), dict(ok, reviewer="gemini")])
    assert dec == "pass"


def test_web_reviewer_verifies_long_scripts_in_chunks_and_merges():
    import types
    from studio import qa

    class Client:
        def __init__(self):
            self.calls = []
            self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(create=self.create))

        def create(self, **kw):
            self.calls.append(kw)
            n = len(self.calls)
            body = '{"verdict": "%s", "issues": ["i%d"], "unverified_claims": ["u%d"]}' % ("pass" if n == 1 else "revise", n, n)
            return types.SimpleNamespace(stop_reason="end_turn", model="claude-opus-5-5", content=[types.SimpleNamespace(type="text", text=body)],
                                         usage=types.SimpleNamespace(input_tokens=10, output_tokens=5, server_tool_use=types.SimpleNamespace(web_search_requests=3)))

    c = Client()
    rev = qa.WebClaudeReviewer(c)
    script = {"title_options": ["t"], "sections": [{"heading": str(i), "narration": "x", "visual_prompt": "v", "seconds": 1} for i in range(10)]}
    r = rev.review(script, "ja")
    assert len(c.calls) == 3                                  # 10 sections -> 3 passes of at most 4
    assert r["verdict"] == "revise" and r["issues"] == ["i1", "i2", "i3"] and r["unverified_claims"] == ["u1", "u2", "u3"]
    assert r["usage"]["web_searches"] == 9 and r["usage"]["input_tokens"] == 30
    assert "ONLY the factual claims" in c.calls[0]["messages"][0]["content"]
