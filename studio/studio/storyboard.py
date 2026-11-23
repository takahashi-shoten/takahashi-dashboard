"""Storyboard stage: split narration into ~15-20 s beats, have Claude plan one consistent image per beat, render them."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import ledger, visuals

MODEL = os.environ.get("STUDIO_STORYBOARD_MODEL", "claude-sonnet-5-5")
DEFAULT_TARGET_CHARS = {"ja": 85, "en": 225}   # ~15 s at the measured 5.5 chars/s (ja) / assumed 15 chars/s (en)
SHOTS = ["wide", "medium", "close_up", "hands_detail", "object", "environment", "over_shoulder", "back_view"]
NO_FACE_SHOTS = {"back_view", "hands_detail", "object", "environment", "over_shoulder"}

_ITEMS = {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "string"}, "description": {"type": "string"}},
    "required": ["id", "description"], "additionalProperties": False}}
SCHEMA = {
    "type": "object",
    "properties": {
        "style_bible": {"type": "object", "properties": {
            "look": {"type": "string"}, "cast": _ITEMS, "locations": _ITEMS},
            "required": ["look", "cast", "locations"], "additionalProperties": False},
        "beats": {"type": "array", "items": {"type": "object", "properties": {
            "section": {"type": "integer"}, "beat": {"type": "integer"},
            "shot": {"type": "string", "enum": SHOTS},
            "cast_ids": {"type": "array", "items": {"type": "string"}},
            "visual_prompt": {"type": "string"}},
            "required": ["section", "beat", "shot", "cast_ids", "visual_prompt"], "additionalProperties": False}},
    },
    "required": ["style_bible", "beats"], "additionalProperties": False,
}

SYSTEM = """You are the storyboard artist for a faceless video channel. You receive the narration split into numbered beats (section, beat, narration).
Return a style bible and exactly one image plan per beat, in the same order, with the same section and beat numbers.
Rules:
- style_bible.look: ONE paragraph in English: camera, lens, lighting, color grade. It is prepended to every image prompt, so keep it reusable.
- style_bible.cast: recurring characters (id, description). Each description is fixed and complete: age, build, hair, clothing, distinguishing features.
  Fictional people only, never a real person's likeness, no copyrighted characters, no minors, nothing sexual. Few characters are better than many.
- style_bible.locations: recurring settings (id, description). Reuse them across beats for consistency.
- Each beat's image illustrates what the narration says at that moment; where the narration is abstract, use a concrete visual metaphor.
- visual_prompt: English, concrete, ONE frame, no text, letters, signs or logos, names no real person, no copyrighted characters, no minors, nothing sexual.
  Do not repeat the cast description in it (it is added automatically from cast_ids).
- shot is one of: wide, medium, close_up, hands_detail, object, environment, over_shoulder, back_view.
- At least HALF of the beats must NOT show a clearly visible face (back_view, hands_detail, object, environment, over_shoulder), because face consistency
  across images is hard for the image model. Vary the shot type between neighbouring beats. cast_ids must be empty for object/environment shots.
- Photographic style (real camera, natural light) when style is "photo". When style is "manga": Japanese comic illustration (clean bold line art, flat bright colours,
  expressive exaggerated faces and emotions, simple readable backgrounds); style_bible.look must say so, and for manga at least a THIRD of the beats should
  avoid a clearly visible face (hands, documents, objects, back views) while the rest show strong emotion. Otherwise original illustration style."""

SAFE_FALLBACK = ("An empty quiet interior at a calm moment, soft natural light falling across a table with a few simple everyday objects, "
                 "no people, no text, shallow depth of field")


def _sentences(text, lang):
    """Splits at sentence ends; terminators, closing quotes and following whitespace stay attached, so the pieces re-join to `text`."""
    ends = "。！？!?" if lang == "ja" else ".!?"
    closers = "」』）)\"'”’"
    out, start, i, n = [], 0, 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            while i < n and text[i] == "\n":
                i += 1
            out.append(text[start:i])
            start = i
        elif ch in ends:
            j = i + 1
            while j < n and text[j] in ends + closers:
                j += 1
            ok = lang == "ja" or j >= n or text[j].isspace()   # en: "3.5" is not a sentence end
            if ok:
                while j < n and text[j] in " 　\t":
                    j += 1
                out.append(text[start:j])
                start = j
            i = j
        else:
            i += 1
    if start < n:
        out.append(text[start:])
    return out


def split_beats(narration, lang, target_chars=None):
    if not narration.strip():
        return []
    target = target_chars or DEFAULT_TARGET_CHARS.get(lang, DEFAULT_TARGET_CHARS["en"])
    beats, cur = [], ""
    for s in _sentences(narration, lang):
        if cur and len(cur) + len(s) > target:
            beats.append(cur)
            cur = ""
        cur += s
    if cur:
        beats.append(cur)
    if len(beats) > 1 and len(beats[-1]) < 0.4 * target:
        tail = beats.pop()
        beats[-1] += tail
    return beats


def _plan_beats(script, lang, beats_per_section=None):
    """beats_per_section=1: every section is exactly one beat (Shorts: one image per narration beat, no further splitting)."""
    if beats_per_section == 1:
        return [{"section": si, "beat": 1, "narration": sec["narration"]} for si, sec in enumerate(script["sections"], 1) if sec["narration"].strip()]
    return [{"section": si, "beat": bi, "narration": b}
            for si, sec in enumerate(script["sections"], 1)
            for bi, b in enumerate(split_beats(sec["narration"], lang), 1)]


def _call(con, client, project_id, model, payload):
    resp = client.beta.messages.create(
        model=model, max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEM, messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
    served = getattr(resp, "model", None)
    priced = served if served in ledger.PRICES else (model if model in ledger.PRICES else "claude-sonnet-5-5")
    ledger.record_cost(con, project_id, "storyboard", "anthropic", priced, resp.usage.input_tokens, resp.usage.output_tokens)
    if resp.stop_reason == "refusal":
        raise RuntimeError("storyboard: the model refused to produce the storyboard")
    return json.loads(next(b.text for b in resp.content if b.type == "text"))


def make_storyboard(con, client, project_id, project_dir, lang, style=None, model=None, beats_per_section=None, vertical=False):
    project_dir = Path(project_dir)
    model = model or MODEL
    style = style or os.environ.get("STUDIO_VISUAL_STYLE", "photo")
    script = json.loads((project_dir / "script.json").read_text(encoding="utf-8"))
    plan = _plan_beats(script, lang, beats_per_section)
    if not plan:
        raise ValueError("script has no narration to storyboard")
    payload = {"lang": lang, "style": style, "beats": plan}
    if vertical:
        payload["frame"] = "vertical 9:16 (1080x1920) frames for a YouTube Short: compose for portrait, subject centered, keep the lower third calm for captions"
    payload["instruction"] = (f"Return EXACTLY {len(plan)} beats, one for each input beat, with the same section and beat numbers. "
                              "Do not add, split, merge or skip beats.")
    want = [(b["section"], b["beat"]) for b in plan]
    data, got = None, []
    for _ in range(2):
        cand = _call(con, client, project_id, model, payload)
        by_key = {}
        for b in cand["beats"]:
            by_key.setdefault((b["section"], b["beat"]), b)       # keep the first entry for a key; extras and duplicates are ignored
        got = [(b["section"], b["beat"]) for b in cand["beats"]]
        if all(k in by_key for k in want):
            data = dict(cand, beats=[by_key[k] for k in want])    # exactly the wanted beats, in order
            break
    if data is None:
        raise ValueError(f"storyboard beats mismatch: expected {len(want)} beats in order, model returned {len(got)} (after one retry)")
    bible = data["style_bible"]
    cast_ids = {c["id"] for c in bible["cast"]}
    beats = []
    for p, b in zip(plan, data["beats"]):
        prompt, replaced = b["visual_prompt"], False
        if visuals.check_prompt(prompt):
            prompt, replaced = SAFE_FALLBACK, True
        beats.append({"section": p["section"], "beat": p["beat"], "chars": len(p["narration"]), "narration": p["narration"],
                      "shot": "environment" if replaced else b["shot"],
                      "cast_ids": [] if replaced else [c for c in b["cast_ids"] if c in cast_ids],
                      "visual_prompt": prompt, "replaced": replaced})
    sb = {"style_bible": bible, "beats": beats}
    (project_dir / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
    return sb


def final_prompt(bible, beat):
    cast = {c["id"]: c["description"] for c in bible["cast"]}
    parts = [bible["look"]] + [f"{i}: {cast[i]}" for i in beat["cast_ids"] if i in cast] + [beat["visual_prompt"]]
    return "\n".join(parts)


def render_beats(project_dir, image_provider, max_workers=3, size=(1920, 1080)):
    project_dir = Path(project_dir)
    sb = json.loads((project_dir / "storyboard.json").read_text(encoding="utf-8"))
    out = project_dir / "visuals"
    jobs = [(out / f"section_{b['section']:02d}_{b['beat']:02d}.png", final_prompt(sb["style_bible"], b), b) for b in sb["beats"]]
    bad = [f"section {b['section']} beat {b['beat']}: {', '.join(r)}" for _, p, b in jobs if (r := visuals.check_prompt(p))]
    if bad:
        raise ValueError("beat prompt rejected: " + "; ".join(bad))
    out.mkdir(parents=True, exist_ok=True)
    usage = []

    def run(job):
        path, prompt, b = job
        if path.exists():
            return
        image_provider.generate(prompt, path, size)
        # best effort: last_usage lives on the shared provider, so with several workers it can be overwritten by another
        # thread between generate() and this read; treat the per-image attribution as approximate.
        u = getattr(image_provider, "last_usage", None)
        if u is not None:
            usage.append({"section": b["section"], "beat": b["beat"], "usage": u})

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as ex:
        list(ex.map(run, jobs))
    if usage:
        usage.sort(key=lambda x: (x["section"], x["beat"]))
        (out / "usage.json").write_text(json.dumps(usage, ensure_ascii=False, indent=2), encoding="utf-8")
    return sorted(j[0] for j in jobs)
