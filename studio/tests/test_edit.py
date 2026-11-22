import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import edit  # noqa: E402


def test_split_lines_ja_and_en():
    ja = edit.split_lines("今日はいい天気ですね。散歩に行きましょう、そして公園で本を読みます！")
    assert ja == ["今日はいい天気ですね", "散歩に行きましょう、", "そして公園で本を読みます！"]
    long_ja = edit.split_lines("あ" * 50)
    assert all(len(l) <= 22 for l in long_ja) and "".join(long_ja) == "あ" * 50
    en = edit.split_lines("This is a fairly long sentence that must be wrapped across lines. Short one.")
    assert all(len(l) <= 42 for l in en) and en[-1] == "Short one."


def test_srt_timing_includes_pause_offsets():
    secs = [dict(narration="こんにちは。さようなら。"), dict(narration="Hello there")]
    srt = edit.make_srt(secs, [2.0, 1.0], fps=30)
    blocks = [b.split("\n") for b in srt.strip().split("\n\n")]
    # section 1: 5 + 5 chars -> 1 s each; section 2 starts at 2.0 + 0.4 pause
    assert [b[1] for b in blocks] == [
        "00:00:00,000 --> 00:00:01,000", "00:00:01,000 --> 00:00:02,000", "00:00:02,400 --> 00:00:03,400"]
    assert blocks[0][2] == "こんにちは" and blocks[2][2] == "Hello there"


def test_describe():
    assert edit.describe()["status"] == "done"


def _probe(path, entries):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries, "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def test_end_to_end(tmp_path):
    p = tmp_path
    (p / "voice").mkdir(); (p / "visuals").mkdir()
    texts = ["今日は新しい動画を作ります。まずは準備から始めましょう。", "This is the second section of the test."]
    (p / "script.json").write_text(json.dumps({"sections": [dict(narration=t) for t in texts]}, ensure_ascii=False))
    for i, colour in enumerate([(200, 60, 60), (40, 120, 220)], 1):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono", "-t", "1",
                        str(p / "voice" / f"section_{i:02d}.wav")], check=True)
        im = Image.new("RGB", (1920, 1080), colour)
        ImageDraw.Draw(im).ellipse((600, 200, 1300, 900), fill=(240, 240, 100))
        im.save(p / "visuals" / f"section_{i:02d}.png")
    # no durations.json: must be re-measured with ffprobe
    t0 = time.time()
    final = edit.assemble(p)
    print(f"assemble seconds: {time.time() - t0:.1f}")
    shorts = edit.make_shorts(p)
    thumb = edit.make_thumbnail(p, "初めての動画制作：AIで作る 3分ガイド")

    v = _probe(final, "stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt:format=duration")
    vs = next(s for s in v["streams"] if s["codec_type"] == "video")
    assert (vs["width"], vs["height"], vs["codec_name"], vs["pix_fmt"]) == (1920, 1080, "h264", "yuv420p")
    num, den = map(int, vs["r_frame_rate"].split("/"))
    assert abs(num / den - 30) < 0.5
    assert any(s["codec_type"] == "audio" and s["codec_name"] == "aac" for s in v["streams"])
    assert abs(float(v["format"]["duration"]) - 2.8) < 0.3

    s = _probe(shorts, "stream=codec_type,width,height:format=duration")
    sv = next(x for x in s["streams"] if x["codec_type"] == "video")
    assert (sv["width"], sv["height"]) == (1080, 1920) and float(s["format"]["duration"]) <= 59

    assert Image.open(thumb).size == (1280, 720)
    assert (p / "final.srt").read_text("utf-8").startswith("1\n00:00:00,000")

    frame = p / "frame.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.7", "-i", str(final), "-frames:v", "1", str(frame)], check=True)
    assert ImageStat.Stat(Image.open(frame).convert("L")).mean[0] > 5

    sf = p / "sf.png"   # burned-in subtitles must put bright text in the lower band of shorts
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5", "-i", str(shorts), "-frames:v", "1", str(sf)], check=True)
    band = Image.open(sf).convert("L").crop((0, 1350, 1080, 1700))
    assert band.getextrema()[1] > 200


def _mkproject(p, texts, voice_secs):
    (p / "voice").mkdir(); (p / "visuals").mkdir()
    (p / "script.json").write_text(json.dumps({"sections": [dict(narration=t) for t in texts]}, ensure_ascii=False))
    for i, d in enumerate(voice_secs, 1):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono", "-t", str(d),
                        str(p / "voice" / f"section_{i:02d}.wav")], check=True)


def _solid(path, colour):
    Image.new("RGB", (1920, 1080), colour).save(path)


def _frame_mean(video, t, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", str(out)], check=True)
    return ImageStat.Stat(Image.open(out).convert("RGB")).mean


def _dur(path):
    return float(_probe(path, "format=duration")["format"]["duration"])


def test_split_frames():
    assert edit.split_frames(100, [1, 1, 2]) == [25, 25, 50]
    assert sum(edit.split_frames(7, [1, 1, 100])) == 7 and min(edit.split_frames(7, [1, 1, 100])) >= 1
    assert edit.split_frames(9, [1, 1, 1]) == [3, 3, 3]


def test_beats_preview_and_thumbnail(tmp_path):
    p = tmp_path
    _mkproject(p, ["Beat section narration.", "Single image section."], [4, 2])
    for b, c in enumerate([(250, 0, 0), (0, 250, 0), (0, 0, 250)], 1):
        _solid(p / "visuals" / f"section_01_{b:02d}.png", c)
    _solid(p / "visuals" / "section_02.png", (250, 250, 0))
    (p / "storyboard.json").write_text(json.dumps({"beats": [
        {"section": 1, "beat": 1, "chars": 10}, {"section": 1, "beat": 2, "chars": 10}, {"section": 1, "beat": 3, "chars": 20}]}))
    t0 = time.time()
    final = edit.assemble(p)
    print(f"beat assemble seconds: {time.time() - t0:.1f}")
    s1, s2 = edit.span(4), edit.span(2)          # 4.4 and 2.4 s
    assert abs(_dur(final) - (s1 + s2)) < 0.1

    def dom(t):   # index of the dominant colour channel at time t
        m = _frame_mean(final, t, p / "f.png")
        return max(range(3), key=lambda i: m[i])
    # cuts at 25% / 50% of section 1 (1.1 s, 2.2 s)
    assert [dom(0.5), dom(1.6), dom(3.3)] == [0, 1, 2]
    assert dom(1.0) == 0 and dom(1.2) == 1 and dom(2.1) == 1 and dom(2.3) == 2
    m = _frame_mean(final, s1 + 1.0, p / "f.png")
    assert m[0] > 150 and m[1] > 150 and m[2] < 100          # section 2 single yellow image
    assert (p / "final.srt").read_text("utf-8").startswith("1\n00:00:00,000")

    prev = edit.make_preview(p)
    assert prev == p / "preview.mp4" and prev.stat().st_size < final.stat().st_size
    v = _probe(prev, "stream=codec_type,codec_name,width,height")
    vs = next(s for s in v["streams"] if s["codec_type"] == "video")
    assert (vs["width"], vs["height"], vs["codec_name"]) == (1280, 720, "h264")
    assert any(s["codec_type"] == "audio" and s["codec_name"] == "aac" for s in v["streams"])

    # no section_01.png: thumbnail background is the first beat (red)
    thumb = edit.make_thumbnail(p, "Beats")
    assert Image.open(thumb).size == (1280, 720)
    px = Image.open(thumb).convert("RGB").getpixel((5, 5))
    assert px[0] > px[1] and px[0] > px[2]


def test_equal_split_without_storyboard(tmp_path):
    p = tmp_path
    _mkproject(p, ["Two beats here."], [2])
    _solid(p / "visuals" / "section_01_01.png", (250, 0, 0))
    _solid(p / "visuals" / "section_01_02.png", (0, 0, 250))
    final = edit.assemble(p)
    assert abs(_dur(final) - edit.span(2)) < 0.1
    a = _frame_mean(final, 0.3, p / "f.png"); b = _frame_mean(final, 2.1, p / "f.png")
    assert a[0] > a[2] and b[2] > b[0]
