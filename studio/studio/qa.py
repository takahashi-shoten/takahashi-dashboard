"""QA stage: deterministic rule checks + independent LLM reviewers -> qa.json with a conservative decision.

A mock-only run can never produce "pass": that needs two non-mock reviewers agreeing, no rule blocks
and no unverified claims. Everything else is "needs_human" or "blocked". Nothing here publishes.
"""
import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Protocol

from .errors import NotConnected

MODEL = os.environ.get("STUDIO_QA_MODEL", "claude-opus-5-5")

# Small, conservative term lists (lowercase for en). Not exhaustive: the reviewers cover the rest.
BLOCK_TERMS = {
    "unsafe_content": [
        "ポルノ", "セックスの描写", "性行為の描写", "キチガイ", "ガイジ", "自殺の方法", "死に方を教", "自殺しよう",
        "porn", "explicit sex", "nigger", "faggot", "how to kill yourself", "how to commit suicide", "ways to self-harm",
    ],
    "medical_claim": ["必ず治る", "確実に治る", "100%効果", "１００％効果", "完治します", "cures ", "guaranteed results", "guaranteed cure", "100% effective"],
    "investment_promise": ["絶対儲かる", "絶対に儲かる", "元本保証", "確実に儲かる", "guaranteed profit", "guaranteed returns", "risk-free returns"],
}
NUM_RE = re.compile(r"\d|[０-９]|%|％")


def _f(id_, severity, message):
    return {"id": id_, "severity": severity, "message": message}


def _norm(t):
    return re.sub(r"[\W_]+", "", t.lower())


def rule_checks(script: dict, lang: str, reference_titles=None, short=False) -> list[dict]:
    out = []
    sections = script.get("sections", [])
    narration = "\n".join(s.get("narration", "") for s in sections)
    blob = (narration + "\n" + script.get("description", "")).lower() + " "
    for id_, terms in BLOCK_TERMS.items():
        hits = [t.strip() for t in terms if t.lower() in blob]
        if hits:
            out.append(_f(id_, "block", f"{id_} phrase(s) found: {', '.join(hits)}"))
    if not script.get("fact_claims_to_verify") and NUM_RE.search(narration):
        out.append(_f("unlisted_numbers", "warn", "narration has numbers/percentages/years but fact_claims_to_verify is empty"))
    if "ai_disclosure_needed" not in script:
        out.append(_f("ai_disclosure_missing", "block", "ai_disclosure_needed is missing"))
    total = sum(int(s.get("seconds", 0)) for s in sections)
    lo, hi = (30, 60) if short else (60, 900)     # Shorts are 45-60 s
    if not lo <= total <= hi:
        out.append(_f("duration", "warn", f"total {total}s is outside {lo}..{hi}"))
    titles = script.get("title_options") or []
    if reference_titles and titles:
        refs = [_norm(r) for r in reference_titles]
        if all(any(SequenceMatcher(None, _norm(t), r).ratio() >= 0.8 for r in refs) for t in titles):
            out.append(_f("title_copy", "warn", "every title option is a near-duplicate of a reference title"))
    for i, s in enumerate(sections, 1):
        n = s.get("narration", "")
        if (len(n.strip()) < (10 if short else 40)) if lang == "ja" else (len(n.split()) < (4 if short else 15)):
            out.append(_f("short_section", "warn", f"section {i} narration is too short"))
    return out


class Reviewer(Protocol):
    def review(self, script: dict, lang: str) -> dict: ...


def _result(name, verdict, issues, unverified, usage=None, model=None):
    # "model" is an extra key beyond the spec so the caller can price usage in the ledger.
    return {"reviewer": name, "verdict": verdict, "issues": issues, "unverified_claims": unverified, "usage": usage, "model": model}


REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "revise", "block"]},
        "issues": {"type": "array", "items": {"type": "string"}},
        "unverified_claims": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "issues", "unverified_claims"],
    "additionalProperties": False,
}

REVIEW_SYSTEM = """You are a skeptical fact-checker and platform-policy reviewer for a faceless AI-assisted video channel.
Review the script for: factual accuracy, advertiser-friendly platform rules, medical or financial claims and promises,
originality (not a paraphrase of someone else's video), minors, sexual content, and real-person likeness or defamation.
You have NO web access. If you cannot verify a claim, say so plainly: put it in unverified_claims and do not assume it is true.
Never pass a script merely because nothing looks wrong; pass only if you positively see no problem AND no claim is unverified.
verdict: "block" for policy violations or harmful/false claims, "revise" for fixable issues, "pass" otherwise.
issues: short concrete problems. Reply in English."""


class ClaudeReviewer:
    name = "claude"

    def __init__(self, client, model=MODEL):
        self.client, self.model = client, model

    def describe(self):
        return dict(stage="qa", status="done", note=f"Claude reviewer {self.model} (no web access; cannot verify facts)")

    def review(self, script, lang):
        user = json.dumps({"lang": lang, "script": script}, ensure_ascii=False)
        resp = self.client.beta.messages.create(
            model=self.model, max_tokens=8000,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            thinking={"type": "adaptive"},
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": REVIEW_SCHEMA}},
            system=REVIEW_SYSTEM, messages=[{"role": "user", "content": user}])
        usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
        model = getattr(resp, "model", None) or self.model
        if resp.stop_reason == "refusal":  # a refusing reviewer is never a pass
            return _result(self.name, "revise", ["reviewer refused to review"], [], usage, model)
        d = json.loads(next(b.text for b in resp.content if b.type == "text"))
        return _result(self.name, d["verdict"], d["issues"], d["unverified_claims"], usage, model)


WEB_REVIEW_SYSTEM = REVIEW_SYSTEM.replace(
    "You have NO web access. If you cannot verify a claim, say so plainly: put it in unverified_claims and do not assume it is true.",
    "You HAVE a web search tool: use it to check every concrete factual claim (numbers, studies, laws, named facts) against reputable sources "
    "before judging. Only claims you could not confirm after searching go in unverified_claims; claims you confirmed or found contradicted go in "
    "issues (contradicted) or nothing (confirmed). Do not assume anything is true without a source.\n"
    "Reply with ONLY one JSON object, no prose: {\"verdict\": \"pass\"|\"revise\"|\"block\", \"issues\": [str], \"unverified_claims\": [str]}.")


def _extract_json(text):
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < a:
        raise ValueError("reviewer returned no JSON object")
    return json.loads(text[a:b + 1])


class WebClaudeReviewer(ClaudeReviewer):
    """Claude with the server-side web search tool, so claims can actually be checked. Still the SAME vendor as ClaudeReviewer:
    it is not an independent second opinion. Web search is billed per search on top of tokens (check the usage page; price not hardcoded)."""
    name = "claude_web"

    def __init__(self, client, model=MODEL, max_searches=8, max_resumes=4):
        super().__init__(client, model)
        self.max_searches, self.max_resumes = max_searches, max_resumes

    def describe(self):
        return dict(stage="qa", status="done", note=f"Claude reviewer {self.model} with web search (max {self.max_searches} searches)")

    def review(self, script, lang):
        messages = [{"role": "user", "content": json.dumps({"lang": lang, "script": script}, ensure_ascii=False)}]
        tin = tout = searches = 0
        resp = None
        for _ in range(self.max_resumes + 1):
            resp = self.client.beta.messages.create(
                model=self.model, max_tokens=12000,
                betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                thinking={"type": "adaptive"}, output_config={"effort": "medium"},
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": self.max_searches}],
                system=WEB_REVIEW_SYSTEM, messages=messages)
            tin += resp.usage.input_tokens
            tout += resp.usage.output_tokens
            st = getattr(resp.usage, "server_tool_use", None)
            searches += int(getattr(st, "web_search_requests", 0) or 0) if st is not None else 0
            if resp.stop_reason != "pause_turn":
                break
            messages = messages + [{"role": "assistant", "content": resp.content}]   # server resumes on the trailing server_tool_use block
        usage = {"input_tokens": tin, "output_tokens": tout, "web_searches": searches}
        model = getattr(resp, "model", None) or self.model
        if resp.stop_reason in ("refusal", "pause_turn"):    # refusal or never finished: never a pass
            return _result(self.name, "revise", [f"reviewer did not finish ({resp.stop_reason})"], [], usage, model)
        text = "".join(b.text for b in resp.content if b.type == "text")
        try:
            d = _extract_json(text)
            return _result(self.name, d["verdict"], d["issues"], d["unverified_claims"], usage, model)
        except (ValueError, KeyError, json.JSONDecodeError):
            return _result(self.name, "revise", ["reviewer reply was not valid JSON"], [], usage, model)


class GeminiReviewer:
    """Independent second opinion: Gemini with Google Search grounding, over REST. Verified only by studio/gemini_live_test.py."""
    name = "gemini"

    def __init__(self, model=None, session=None):
        self.model = model or os.environ.get("STUDIO_GEMINI_REVIEW_MODEL", "gemini-pro-latest")
        self.session = session

    def describe(self):
        ok = bool(os.environ.get("GEMINI_API_KEY"))
        return dict(stage="qa", status="done" if ok else "not_connected",
                    note=f"Gemini reviewer {self.model} with Google Search" + ("" if ok else " (needs GEMINI_API_KEY)"))

    def review(self, script, lang):
        from . import gemini
        body = {"systemInstruction": {"parts": [{"text": WEB_REVIEW_SYSTEM.replace("web search tool", "Google Search tool")}]},
                "contents": [{"parts": [{"text": json.dumps({"lang": lang, "script": script}, ensure_ascii=False)}]}],
                "tools": [{"google_search": {}}]}
        resp = gemini.generate_content(self.model, body, self.session)
        u = gemini.usage(resp)
        usage = {"input_tokens": u["input_tokens"], "output_tokens": u["output_tokens"] + u["thought_tokens"]}
        try:
            d = _extract_json(gemini.text_of(resp))
            return _result(self.name, d["verdict"], d["issues"], d["unverified_claims"], usage, self.model)
        except (ValueError, KeyError, json.JSONDecodeError):
            return _result(self.name, "revise", ["reviewer reply was not valid JSON"], [], usage, self.model)


class MockReviewer:
    name = "mock"

    def describe(self):
        return dict(stage="qa", status="mock", note="MOCK reviewer: always passes, never counts toward approval")

    def review(self, script, lang):
        return _result(self.name, "pass", ["mock"], [])


def describe():
    return dict(stage="qa", status="mock",
                note="rule checks are real; LLM reviewers need ANTHROPIC_API_KEY / GEMINI_API_KEY; pass requires 2 non-mock reviewers")


def decide(rule_findings, reviews):
    reasons = [f"rule {f['id']}: {f['message']}" for f in rule_findings if f["severity"] == "block"]
    reasons += [f"{r['reviewer']} blocked" for r in reviews if r["verdict"] == "block"]
    if reasons:
        return "blocked", reasons
    # independence: reviewers from the same vendor ("claude", "claude_web") count once; "pass" needs two different vendors
    real_pass = {r["reviewer"].split("_")[0] for r in reviews if r["reviewer"] != "mock" and r["verdict"] == "pass"}
    unverified = [c for r in reviews for c in r["unverified_claims"]]
    if len(real_pass) < 2:
        reasons.append(f"only {len(real_pass)} independent (different-vendor, non-mock) reviewer(s) passed (need 2)")
    reasons += [f"{r['reviewer']} asks for revision" for r in reviews if r["verdict"] == "revise"]
    if unverified:
        reasons.append(f"{len(unverified)} unverified claim(s)")
    return ("needs_human", reasons) if reasons else ("pass", ["2+ non-mock reviewers passed, no blocks, no unverified claims"])


def run_qa(project_dir: Path, lang: str, reviewers: list, reference_titles=None, short=False) -> dict:
    project_dir = Path(project_dir)
    script = json.loads((project_dir / "script.json").read_text(encoding="utf-8"))
    findings = rule_checks(script, lang, reference_titles, short)
    reviews = [r.review(script, lang) for r in reviewers]
    decision, reasons = decide(findings, reviews)
    unverified = list(dict.fromkeys(c for r in reviews for c in r["unverified_claims"]))
    out = {"decision": decision, "rule_findings": findings, "reviews": reviews, "unverified_claims": unverified, "reasons": reasons}
    (project_dir / "qa.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
