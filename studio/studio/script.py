"""Script stage: Claude writes an original script + shot list + metadata, with measured cost."""
import json
import os
import re

from . import ledger

MODEL = os.environ.get("STUDIO_SCRIPT_MODEL", "claude-opus-5-5")

SCHEMA = {
    "type": "object",
    "properties": {
        "title_options": {"type": "array", "items": {"type": "string"}},
        "original_angle": {"type": "string"},
        "hook": {"type": "string"},
        "sections": {"type": "array", "items": {
            "type": "object",
            "properties": {"heading": {"type": "string"}, "narration": {"type": "string"},
                           "visual_prompt": {"type": "string"}, "seconds": {"type": "integer"}},
            "required": ["heading", "narration", "visual_prompt", "seconds"], "additionalProperties": False}},
        "thumbnail_text": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "fact_claims_to_verify": {"type": "array", "items": {"type": "string"}},
        "ai_disclosure_needed": {"type": "boolean"},
    },
    "required": ["title_options", "original_angle", "hook", "sections", "thumbnail_text", "description", "tags",
                 "fact_claims_to_verify", "ai_disclosure_needed"],
    "additionalProperties": False,
}

CHARS_PER_SEC = {"ja": 5.5, "en": 15.0}   # ja measured 2026-11-22 with real VOICEVOX (speaker 3, ノーマル): 5.50 chars/s; en still an assumption
LENGTH_TOLERANCE = 0.15

SYSTEM = """You write scripts for a faceless, AI-assisted video channel. Rules:
- The video must have a clear ORIGINAL angle; never paraphrase a reference video. Reference hits only show what titles/formats get clicked.
- Write in the requested language, in a natural spoken voice. No filler, no padding to hit a length.
- Be accurate. List every factual claim that must be verified before publishing in fact_claims_to_verify. Do not invent statistics, studies or quotes.
- No sexually explicit content, nothing involving minors, no real people's likenesses, no medical promises or cures.
- visual_prompt describes an original illustration/animation shot, never a copyrighted character or a real person.
- Set ai_disclosure_needed=true when visuals or voice are synthetic and realistic.
- thumbnail_text: the 8-14 character (ja) or 2-5 word (en) punchy line for the thumbnail: a concrete promise, a surprise or a tension, never the full title.
- LENGTH IS A HARD REQUIREMENT: the total number of characters in all `narration` fields must be within 10% of `target_narration_chars`
  (count characters, not words). Do not summarize or stop early; develop each section fully with examples and concrete detail.
  Set each section's `seconds` to its narration characters divided by `chars_per_second`, rounded."""
REVISE_SYSTEM = SYSTEM + """
You are REVISING an existing script. Return the complete revised script in the same schema. Follow the instruction exactly."""


def narration_chars(data):
    return sum(len(s["narration"]) for s in data["sections"])


def _call(con, client, project_id, stage, system, payload):
    resp = client.beta.messages.create(
        model=MODEL, max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=system, messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
    usd = ledger.record_cost(con, project_id, stage, "anthropic", resp.model if getattr(resp, "model", None) in ledger.PRICES else MODEL,
                             resp.usage.input_tokens, resp.usage.output_tokens)
    if resp.stop_reason == "refusal":
        ledger.add_step(con, project_id, stage, "failed", detail="model refused")
        return None, usd
    return json.loads(next(b.text for b in resp.content if b.type == "text")), usd


def _normalize_seconds(data, rate):
    for s in data["sections"]:
        s["seconds"] = max(1, round(len(s["narration"]) / rate))
    return data


def write_script(con, client, project_id, target_seconds=480, max_fixes=2, chars_per_sec=None):
    """Writes the script, then re-prompts (up to `max_fixes` times) while its spoken length misses the target by > tolerance."""
    p = con.execute("SELECT brief_json FROM projects WHERE project_id=?", (project_id,)).fetchone()
    brief = json.loads(p["brief_json"])
    rate = chars_per_sec or CHARS_PER_SEC.get(brief.get("lang"), 5.5)
    target = int(target_seconds * rate)
    data, total = _call(con, client, project_id, "script", SYSTEM,
                        {"brief": brief, "target_seconds": target_seconds, "target_narration_chars": target, "chars_per_second": rate})
    if data is None:
        return None
    fixes = 0
    while fixes < max_fixes and abs(narration_chars(data) - target) / target > LENGTH_TOLERANCE:
        n = narration_chars(data)
        verb = "EXPAND (add substance, examples, concrete detail; no padding)" if n < target else "TRIM (cut repetition, keep the best material)"
        fixed, usd = _call(con, client, project_id, "script_fix", REVISE_SYSTEM, {
            "instruction": f"The narration is {n} characters but the target is {target} (+-10%). {verb}. Keep the original angle, hook and section structure.",
            "target_narration_chars": target, "chars_per_second": rate, "script": data})
        total += usd
        if fixed is None:
            break
        data, fixes = fixed, fixes + 1
    _normalize_seconds(data, rate)
    ledger.add_step(con, project_id, "script", "done", data,
                    detail=f"cost_usd={total:.4f} narration_chars={narration_chars(data)} target={target} fixes={fixes}")
    con.execute("UPDATE projects SET status='script', title=? WHERE project_id=?", (data["title_options"][0], project_id))
    con.commit()
    return data


def revise_with_feedback(con, client, project_id, data, issues, unverified_claims, lang="ja", chars_per_sec=None, short=False):
    """Applies QA feedback: removes or softens claims that cannot be verified, keeps the length."""
    rate = chars_per_sec or (SHORT_CHARS_PER_SEC if short else CHARS_PER_SEC).get(lang, 5.5)
    n = narration_chars(data)
    revised, _ = _call(con, client, project_id, "script_revise", SHORT_REVISE_SYSTEM if short else REVISE_SYSTEM, {
        "instruction": ("Fix the reviewer's issues. For every unverified claim: remove it, or rewrite it as a clearly hedged general statement "
                        "without invented numbers, studies or quotes; never keep a precise statistic you cannot source. List what remains "
                        "in fact_claims_to_verify. Keep total narration length within 10% of the current length."),
        "issues": issues, "unverified_claims": unverified_claims, "current_narration_chars": n, "chars_per_second": rate, "script": data})
    if revised is None:
        return data
    if short:
        _, cap = short_limits(rate)
        if narration_chars(revised) > cap or spoken_seconds(revised, rate) > SHORT_MAX_SECONDS:
            return data                     # a revision that would break the 59 s cap is discarded
        _clean_short_titles(revised)
    _normalize_seconds(revised, rate)
    ledger.add_step(con, project_id, "script", "done", revised, detail="revised after QA feedback")
    return revised


# ---------- Shorts (vertical, 45-60 s) ----------
SHORT_CHARS_PER_SEC = {"ja": 5.5, "en": 14.0}
SHORT_TOLERANCE = 0.20
SHORT_MAX_SECONDS = 59.0
SHORT_PAUSE = 0.2            # silence after each beat in the assembled Short (edit.SHORT_PAUSE has the same value)
SHORT_MIN_BEATS, SHORT_MAX_BEATS = 6, 9
SHORT_TITLE_MAX = 60

SHORT_SYSTEM = """You write scripts for a faceless, AI-assisted YouTube SHORTS channel (vertical 9:16, 45-60 seconds, narrated). Rules:
- ONE idea only. Open with a hook in the first 2 seconds: a concrete question or a surprising claim (e.g. "How did ancient humans make the first clay pots?").
  The hook is the narration of the first beat.
- `sections` are the narration BEATS: between 6 and 9 beats, each 1-2 SHORT spoken sentences. No filler, no throat-clearing, no "in this video".
- Build curiosity beat by beat and put the surprising payoff in the FINAL beats. The very last line must loop back to the opening
  (echo the hook's wording or question) so the Short invites a rewatch.
- Write in the requested language, natural spoken voice, short sentences. Never paraphrase a reference video; reference hits only show what gets clicked.
- Be accurate. List every factual claim that must be verified before publishing in fact_claims_to_verify. Do not invent statistics, studies, dates or quotes.
  Prefer vivid, well-established facts over precise numbers.
- No sexually explicit content, nothing involving minors, no real people's likenesses, no medical promises or cures.
- visual_prompt: one original, concrete, photographable frame per beat (vertical composition), no text, letters or logos, never a copyrighted character or a real person.
- title_options: 2-3 options, each at most 60 characters, a question or a surprise. Do NOT include the #shorts tag.
- thumbnail_text: a 2-4 word line (it is optional for Shorts but the field must be filled).
- Set ai_disclosure_needed=true when visuals or voice are synthetic and realistic.
- LENGTH IS A HARD REQUIREMENT: the total number of characters in all `narration` fields must be within 20% of `target_narration_chars`
  (count characters, not words) and NEVER above `max_narration_chars`. Set each section's `seconds` to its narration characters divided by `chars_per_second`, rounded."""
SHORT_REVISE_SYSTEM = SHORT_SYSTEM + """
You are REVISING an existing Short script. Return the complete revised script in the same schema. Follow the instruction exactly."""


def short_limits(rate, target_seconds=50):
    """(target_chars, max_chars) for a Short: the cap leaves room for the per-beat pauses of the assembled video."""
    target = int(target_seconds * rate)
    cap = int((SHORT_MAX_SECONDS - SHORT_PAUSE * SHORT_MAX_BEATS) * rate)
    return min(target, cap), cap


def spoken_seconds(data, rate):
    """Estimated total video length: narration at `rate` chars/s plus the pause after every beat."""
    return narration_chars(data) / rate + SHORT_PAUSE * len(data["sections"])


def _clean_short_titles(data):
    out = []
    for t in data["title_options"]:
        t = re.sub(r"#shorts?\b", "", t, flags=re.I).strip(" -|\u3000")
        if len(t) > SHORT_TITLE_MAX:
            t = t[:SHORT_TITLE_MAX].rstrip(" ,;:-")
        if t:
            out.append(t)
    data["title_options"] = out or ["Untitled Short"]
    return data


def _short_problem(data, rate, target, cap):
    n, beats = narration_chars(data), len(data["sections"])
    if n > cap or spoken_seconds(data, rate) > SHORT_MAX_SECONDS:
        return f"TRIM: the narration is {n} characters, over the hard cap of {cap} (the video must stay under {int(SHORT_MAX_SECONDS)} s). Cut the weakest material."
    if abs(n - target) / target > SHORT_TOLERANCE:
        verb = "EXPAND (add a concrete detail or one more beat; no padding)" if n < target else "TRIM (cut repetition, keep the hook and the payoff)"
        return f"The narration is {n} characters but the target is {target} (+-20%). {verb}."
    if not SHORT_MIN_BEATS <= beats <= SHORT_MAX_BEATS:
        return f"The script has {beats} beats; it must have between {SHORT_MIN_BEATS} and {SHORT_MAX_BEATS}."
    return None


def write_short(con, client, project_id, target_seconds=50, chars_per_sec=None, max_fixes=2):
    """Writes a vertical Short script (sections = narration beats, same schema as write_script). Re-prompts while the spoken
    length misses the target by > 20%, the beat count is outside 6..9 or the total would exceed 59 s; raises ValueError if still over the cap."""
    p = con.execute("SELECT brief_json FROM projects WHERE project_id=?", (project_id,)).fetchone()
    brief = json.loads(p["brief_json"])
    rate = chars_per_sec or SHORT_CHARS_PER_SEC.get(brief.get("lang"), 14.0)
    target, cap = short_limits(rate, target_seconds)
    base = {"target_narration_chars": target, "max_narration_chars": cap, "chars_per_second": rate, "beats": f"{SHORT_MIN_BEATS}-{SHORT_MAX_BEATS}"}
    data, total = _call(con, client, project_id, "script", SHORT_SYSTEM, {"brief": brief, "target_seconds": target_seconds, "format": "youtube short 9:16", **base})
    if data is None:
        return None
    fixes = 0
    while fixes < max_fixes and (problem := _short_problem(data, rate, target, cap)):
        fixed, usd = _call(con, client, project_id, "script_fix", SHORT_REVISE_SYSTEM, {
            "instruction": problem + " Keep the opening question, the payoff and the closing loop.", **base, "script": data})
        total += usd
        if fixed is None:
            break
        data, fixes = fixed, fixes + 1
    if narration_chars(data) > cap or spoken_seconds(data, rate) > SHORT_MAX_SECONDS:
        raise ValueError(f"short script too long: {narration_chars(data)} characters (cap {cap}) after {fixes} fix(es)")
    _clean_short_titles(data)
    _normalize_seconds(data, rate)
    ledger.add_step(con, project_id, "script", "done", data,
                    detail=f"short cost_usd={total:.4f} narration_chars={narration_chars(data)} target={target} cap={cap} fixes={fixes}")
    con.execute("UPDATE projects SET status='script', title=? WHERE project_id=?", (data["title_options"][0], project_id))
    con.commit()
    return data
