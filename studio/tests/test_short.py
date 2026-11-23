import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from studio import edit, ledger, produce, qa, script, storyboard, visuals, voice  # noqa: E402
from test_gemini import IMG, Session  # noqa: E402

BEAT = "Ancient potters shaped wet clay by hand. Then fire changed everything."


def short_script(n_beats=7, chars_each=100, titles=("How did ancient humans make clay pots? #shorts",)):
    narr = [(BEAT + " ") * 3 for _ in range(n_beats)]
    narr = [n[:chars_each].strip() for n in narr]
    return dict(title_options=list(titles), original_angle="a", hook="h", thumbnail_text="Clay pots", description="d", tags=["x"],
                fact_claims_to_verify=["c"], ai_disclosure_needed=True,
                sections=[dict(heading=f"b{i}", narration=n, visual_prompt="a potter's hands shaping clay", seconds=1) for i, n in enumerate(narr, 1)])


class Client:
    """Returns the queued script payloads in order and records the calls."""

    def __init__(self, payloads):
        self.payloads, self.calls = list(payloads), []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        return NS(stop_reason="end_turn", model="claude-opus-5-5", usage=NS(input_tokens=1000, output_tokens=2000),
                  content=[NS(type="text", text=json.dumps(self.payloads.pop(0)))])


def new_project(lang="en"):
    con = ledger.connect(":memory:")
    pid = con.execute("INSERT INTO projects(genre,lang,platform,title,status,brief_json,created_at) VALUES('g',?,'youtube','t','brief',?,?)",
                      (lang, json.dumps({"lang": lang, "genre": "g", "reference_hits": []}), ledger.now())).lastrowid
    con.commit()
    return con, pid


# ---------- script ----------
def test_short_length_loop_expands_then_accepts():
    con, pid = new_project()
    c = Client([short_script(7, 40), short_script(7, 100)])       # 280 chars << 700 target; 700 is on target
    data = script.write_short(con, c, pid, target_seconds=50)
    assert len(c.calls) == 2 and "EXPAND" in c.calls[1]["messages"][0]["content"]
    assert "youtube short" in json.loads(c.calls[0]["messages"][0]["content"])["format"]
    assert abs(script.narration_chars(data) - 700) / 700 <= 0.2
    assert data["title_options"] == ["How did ancient humans make clay pots?"] and all(len(t) <= 60 for t in data["title_options"])
    assert data["sections"][0]["seconds"] == round(len(data["sections"][0]["narration"]) / 14.0)
    assert script.spoken_seconds(data, 14.0) <= 59


def test_short_trims_when_over_cap_and_raises_if_still_too_long():
    con, pid = new_project()
    c = Client([short_script(8, 140), short_script(8, 100)])       # 1120 chars = 80 s, then fine
    data = script.write_short(con, c, pid)
    assert "TRIM" in c.calls[1]["messages"][0]["content"] and script.narration_chars(data) <= script.short_limits(14.0)[1]
    con, pid = new_project()
    too_long = [short_script(8, 140)] * 3
    with pytest.raises(ValueError, match="too long"):
        script.write_short(con, Client(too_long), pid)


def test_short_beat_count_is_enforced_and_titles_trimmed():
    con, pid = new_project()
    c = Client([short_script(4, 175, titles=("x" * 80 + " #Shorts",)), short_script(7, 100)])
    data = script.write_short(con, c, pid)
    assert "between 6 and 9" in c.calls[1]["messages"][0]["content"] and len(data["sections"]) == 7
    c2 = Client([short_script(7, 100, titles=("y" * 80 + " #Shorts",))])
    con, pid = new_project()
    d2 = script.write_short(con, c2, pid)
    assert all(len(t) <= 60 and "#" not in t for t in d2["title_options"])


# ---------- visuals ----------
def test_aspect_ratio_follows_size(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert visuals.aspect_ratio((1920, 1080)) == "16:9" and visuals.aspect_ratio((1080, 1920)) == "9:16"
    s = Session([__import__("test_gemini").Resp(200, IMG)])
    visuals.GeminiImage(session=s).generate("a potter", tmp_path / "v.png", size=(1080, 1920))
    assert s.calls[0][1]["generationConfig"]["imageConfig"]["aspectRatio"] == "9:16"
    assert Image.open(tmp_path / "v.png").size == (1080, 1920)
    s2 = Session([__import__("test_gemini").Resp(200, IMG)])
    visuals.GeminiImage(session=s2).generate("a potter", tmp_path / "h.png")
    assert s2.calls[0][1]["generationConfig"]["imageConfig"]["aspectRatio"] == "16:9"
    assert Image.open(tmp_path / "h.png").size == (1920, 1080)


def test_vertical_request_keeps_the_400_fallback(monkeypatch, tmp_path):
    from test_gemini import Resp
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    s = Session([Resp(400, {"error": {"message": "bad"}}), Resp(200, IMG)])
    visuals.GeminiImage(session=s).generate("x", tmp_path / "a.png", size=(1080, 1920))
    assert s.calls[1][1]["generationConfig"]["responseModalities"] == ["TEXT", "IMAGE"]
    assert Image.open(tmp_path / "a.png").size == (1080, 1920)


def test_mock_image_honors_size(tmp_path):
    visuals.MockImage().generate("p", tmp_path / "m.png", size=(1080, 1920))
    assert Image.open(tmp_path / "m.png").size == (1080, 1920)


def test_one_beat_per_section_and_render_size(tmp_path):
    sc = short_script(3, 100)
    plan = storyboard._plan_beats(sc, "en", beats_per_section=1)
    assert [(b["section"], b["beat"]) for b in plan] == [(1, 1), (2, 1), (3, 1)]
    long_sc = {"sections": [dict(narration="First sentence of the beat. " * 12)] * 2}
    assert len(storyboard._plan_beats(long_sc, "en")) > 2 and len(storyboard._plan_beats(long_sc, "en", 1)) == 2               # default splitting is unchanged
    beats = [{"section": b["section"], "beat": 1, "chars": 10, "narration": b["narration"], "shot": "object", "cast_ids": [],
              "visual_prompt": "a clay pot", "replaced": False} for b in plan]
    (tmp_path / "storyboard.json").write_text(json.dumps({"style_bible": {"look": "photo", "cast": [], "locations": []}, "beats": beats}))
    paths = storyboard.render_beats(tmp_path, visuals.MockImage(), size=(1080, 1920))
    assert len(paths) == 3 and all(Image.open(p).size == (1080, 1920) for p in paths)


# ---------- edit ----------
def probe(path, entries, stream=None):
    cmd = ["ffprobe", "-v", "error"] + (["-select_streams", stream] if stream else []) + ["-show_entries", entries, "-of", "json", str(path)]
    return json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)


def make_project(p, texts, secs):
    (p / "voice").mkdir(); (p / "visuals").mkdir()
    (p / "script.json").write_text(json.dumps({"sections": [dict(narration=t) for t in texts]}))
    for i, (t, d) in enumerate(zip(texts, secs), 1):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=24000", "-t", str(d),
                        "-ac", "1", str(p / "voice" / f"section_{i:02d}.wav")], check=True)
        Image.new("RGB", (1080, 1920), (40 * i % 255, 90, 160)).save(p / "visuals" / f"section_{i:02d}.png")
    (p / "voice" / "durations.json").write_text(json.dumps({f"{i:02d}": d for i, d in enumerate(secs, 1)}))


def test_caption_groups_are_3_to_5_words():
    for n in range(3, 40):
        groups = edit.caption_groups(" ".join(f"w{i}" for i in range(n)))
        assert all(3 <= len(g.split()) <= 5 for g in groups) and " ".join(groups).split() == [f"w{i}" for i in range(n)]
    assert edit.caption_groups("Hi there") == ["Hi there"] and edit.caption_groups("") == []


def test_caption_timing_is_proportional_with_02_pauses():
    secs = [dict(narration="aaaa bbbb cccc dddd eeee ffff"), dict(narration="one two three")]
    ev = edit.make_caption_events(secs, [3.0, 1.0], fps=30)
    assert [(round(a, 2), round(b, 2), t) for a, b, t in ev] == [
        (0.0, 1.5, "aaaa bbbb cccc"), (1.5, 3.0, "dddd eeee ffff"), (3.2, 4.2, "one two three")]


def test_assemble_short_is_vertical_with_audio_and_captions(tmp_path):
    texts = ["How did ancient humans make the first clay pots?", "They did not start with a wheel at all.", "Fire was the real secret behind it."]
    make_project(tmp_path, texts, [2.0, 1.5, 1.5])
    out = edit.assemble_short(tmp_path)
    assert out.name == "short.mp4"
    v = probe(out, "stream=width,height,codec_name", "v")["streams"][0]
    a = probe(out, "stream=codec_name", "a")["streams"]
    assert (v["width"], v["height"], v["codec_name"]) == (1080, 1920, "h264") and a and a[0]["codec_name"] == "aac"
    dur = float(probe(out, "format=duration")["format"]["duration"])
    assert abs(dur - (5.0 + 3 * 0.2)) < 0.15 and dur <= 59
    ass = (tmp_path / "short.ass").read_text()
    assert "PlayResY: 1920" in ass and ass.count("Dialogue:") == 6 and "DejaVu Sans" in ass


def test_assemble_short_rejects_over_59_seconds(tmp_path):
    make_project(tmp_path, ["Some narration here for the long one."] * 3, [20.0, 20.0, 18.9])   # 58.9 + 0.6 = 59.5
    with pytest.raises(ValueError, match="limit is 59"):
        edit.assemble_short(tmp_path)
    assert not (tmp_path / "short.mp4").exists()


# ---------- sub-cuts ----------
def _busy_png(path, size=(1080, 1920)):
    """High-contrast image (checkerboard + horizontal gradient + bright patch) so different framings differ strongly."""
    from PIL import ImageDraw
    w, h = size
    img = Image.linear_gradient("L").resize((w, h)).convert("RGB")
    d = ImageDraw.Draw(img)
    for gx in range(0, w, 90):
        for gy in range(0, h, 90):
            if (gx // 90 + gy // 90) % 2:
                d.rectangle([gx, gy, gx + 89, gy + 89], fill=(255, 40, 40))
    d.rectangle([600, 150, 900, 450], fill=(255, 255, 255))
    img.save(path)


def _frame(video, t, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", str(video), "-frames:v", "1", str(out)], check=True)
    return Image.open(out).convert("L").crop((0, 0, 1080, 1300))      # above the caption band


def test_cut_counts_sum_and_size():
    for frames in (1, 2, 30, 77, 216, 231, 1700):
        c = edit.cut_counts(frames, 3.0)
        assert sum(c) == frames and min(c) >= 1 and len(c) == max(1, round(frames / 30 / 3.0))
        assert len(c) == 1 or all(2.0 <= n / 30 <= 4.0 for n in c)
    assert edit.cut_counts(210, 3.0) == [105, 105] and len(edit.cut_counts(231, 3.0)) == 3


def test_consecutive_moves_differ():
    fs = [edit._cut_filter(i, 90, 30, edit.SHORT_SIZE) for i in range(13)]
    assert all(a != b for a, b in zip(fs, fs[1:])) and fs[0] == fs[6] and len(set(fs[:6])) == 6


def test_short_subcuts_change_picture_and_keep_duration(tmp_path):
    texts = ["How did ancient humans make the first clay pots?", "They did not start with a wheel at all."]
    make_project(tmp_path, texts, [6.8, 2.8])      # spans 7.0 s -> 2 cuts, 3.0 s -> 1 cut
    for i in (1, 2):
        _busy_png(tmp_path / "visuals" / f"section_{i:02d}.png")
    out = edit.assemble_short(tmp_path)
    dur = float(probe(out, "format=duration")["format"]["duration"])
    assert abs(dur - 10.0) < 0.1
    n1 = edit.cut_counts(round(7.0 * 30), 3.0)
    assert n1 == [105, 105]
    b = n1[0] / 30
    a = _frame(out, b - 1 / 30, tmp_path / "a.png"); c = _frame(out, b + 1 / 30, tmp_path / "b.png")
    from PIL import ImageChops, ImageStat
    assert ImageStat.Stat(ImageChops.difference(a, c)).mean[0] > 20
    # a frame within a cut barely moves compared with the jump at the cut
    d = _frame(out, 1.0, tmp_path / "d.png"); e = _frame(out, 1.0 + 1 / 30, tmp_path / "e.png")
    assert ImageStat.Stat(ImageChops.difference(d, e)).mean[0] < 5
    # section boundary also a hard cut with a different framing
    f = _frame(out, 7.0 - 1 / 30, tmp_path / "f.png"); g = _frame(out, 7.0 + 1 / 30, tmp_path / "g.png")
    assert ImageStat.Stat(ImageChops.difference(f, g)).mean[0] > 20


def test_short_cut_seconds_zero_is_old_behavior(tmp_path):
    texts = ["How did ancient humans make the first clay pots?", "They did not start with a wheel at all."]
    make_project(tmp_path, texts, [6.8, 2.8])
    old = edit.assemble_short(tmp_path, cut_seconds=0)
    d0 = float(probe(old, "format=duration")["format"]["duration"])
    new = edit.assemble_short(tmp_path)
    assert abs(d0 - float(probe(new, "format=duration")["format"]["duration"])) < 0.05 and abs(d0 - 10.0) < 0.1


def test_short_guard_with_cuts(tmp_path):
    make_project(tmp_path, ["Some narration here for the long one."] * 3, [20.0, 20.0, 18.9])
    with pytest.raises(ValueError, match="limit is 59"):
        edit.assemble_short(tmp_path, cut_seconds=3.0)


def test_long_form_cut_seconds_option(tmp_path):
    texts = ["First part of the story goes here.", "Second part of the story."]
    make_project(tmp_path, texts, [6.8, 2.0])
    for i in (1, 2):
        Image.new("RGB", (1920, 1080), (30, 60, 90)).save(tmp_path / "visuals" / f"section_{i:02d}.png")
    base = edit.assemble(tmp_path)
    d0 = float(probe(base, "format=duration")["format"]["duration"])
    fast = edit.assemble(tmp_path, cut_seconds=3.0)
    assert abs(float(probe(fast, "format=duration")["format"]["duration"]) - d0) < 0.1 and abs(d0 - 9.6) < 0.15


# ---------- produce_short ----------
def test_produce_short_end_to_end_with_mocks(tmp_path, monkeypatch):
    con, pid = new_project("en")
    sc = short_script(7, 100)
    monkeypatch.setattr(script, "write_short", lambda *a, **k: json.loads(json.dumps(sc)))

    def fake_storyboard(con_, client, project_id, d, lang, **k):
        assert k.get("beats_per_section") == 1 and k.get("vertical") is True
        plan = storyboard._plan_beats(sc, lang, 1)
        beats = [{"section": b["section"], "beat": 1, "chars": len(b["narration"]), "narration": b["narration"], "shot": "object",
                  "cast_ids": [], "visual_prompt": "a clay pot on a table", "replaced": False} for b in plan]
        out = {"style_bible": {"look": "photo", "cast": [], "locations": []}, "beats": beats}
        (Path(d) / "storyboard.json").write_text(json.dumps(out))
        return out
    monkeypatch.setattr(storyboard, "make_storyboard", fake_storyboard)
    rep = produce.produce_short(con, pid, "en", client=None, voice_provider=voice.MockVoice(), image_provider=visuals.MockImage(),
                                reviewers=[qa.MockReviewer()], work_root=tmp_path)
    d = tmp_path / str(pid)
    assert rep["format"] == "short" and rep["is_mock"] is True and rep["ready_to_publish"] is False
    assert rep["qa"]["decision"] == "needs_human" and rep["final_seconds"] <= 59
    assert "short.mp4" in rep["files"] and (d / "report.json").exists()
    v = probe(d / "short.mp4", "stream=width,height", "v")["streams"][0]
    assert (v["width"], v["height"]) == (1080, 1920) and probe(d / "short.mp4", "stream=codec_name", "a")["streams"]
    assert Image.open(d / "visuals" / "section_01_01.png").size == (1080, 1920)
    assert rep["stages"]["voice"]["status"] == "mock" and rep["stages"]["visuals"]["status"] == "mock"


def test_produce_short_blocked_qa_stops_before_assets(tmp_path, monkeypatch):
    con, pid = new_project("en")
    bad = short_script(7, 100); bad["sections"][0]["narration"] = "This cures everything, guaranteed cure."
    monkeypatch.setattr(script, "write_short", lambda *a, **k: bad)
    monkeypatch.setattr(storyboard, "make_storyboard", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not be called")))
    rep = produce.produce_short(con, pid, "en", None, voice.MockVoice(), visuals.MockImage(), [qa.MockReviewer()], work_root=tmp_path)
    assert rep["qa"]["decision"] == "blocked" and "no paid asset" in rep["stopped"]


def test_cli_has_format_flag():
    src = Path(produce.__file__).read_text()
    assert '"--format"' in src and 'default="long"' in src and "produce_short" in src
