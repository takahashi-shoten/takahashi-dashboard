import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import ledger, storyboard, visuals  # noqa: E402

JA = "今日は朝から雨が降っていた。窓の外を眺めながら、温かいお茶を淹れる！この時間が好きだ。\n" * 6
EN = "It was raining since morning. I made a cup of tea and watched the street. 3.5 million people live here! Why does it feel so quiet? " * 5


@pytest.mark.parametrize("text,lang,target", [(JA, "ja", None), (EN, "en", None), (JA, "ja", 30), (EN, "en", 60),
                                              ("短い。", "ja", None), ("No end", "en", None)])
def test_split_covers_text_exactly(text, lang, target):
    beats = storyboard.split_beats(text, lang, target)
    assert beats and "".join(beats) == text


def test_split_never_cuts_inside_sentence():
    ja = storyboard.split_beats(JA, "ja", 30)
    assert all(b.rstrip().endswith(("。", "！", "？")) for b in ja)
    en = storyboard.split_beats(EN, "en", 60)
    assert all(b.rstrip()[-1] in ".!?" for b in en)
    assert not any(b.rstrip().endswith("3.") for b in en)      # "3.5" is not a sentence end


def test_split_tail_merge_and_empty():
    s = "あいうえおかきくけこ。さしすせそたちつてと。な。"
    b = storyboard.split_beats(s, "ja", 11)
    assert "".join(b) == s and len(b) == 2 and b[-1].endswith("な。")
    assert storyboard.split_beats("  \n", "ja") == []


def test_default_targets():
    assert len(storyboard.split_beats(("あ" * 40 + "。") * 6, "ja")) == 3          # 41+41 <= 85 < 123


def setup(tmp_path, narrations=("今日は雨だった。" * 25, "短い。")):
    d = tmp_path / "p"
    d.mkdir()
    (d / "script.json").write_text(json.dumps({"sections": [{"heading": "h", "narration": n, "visual_prompt": "v", "seconds": 1}
                                                            for n in narrations]}), encoding="utf-8")
    con = ledger.connect(":memory:")
    con.execute("INSERT INTO projects(genre,lang) VALUES('g','ja')")
    return con, d


def reply_for(d, prompt="A rainy window with tea steaming on the sill"):
    script = json.loads((d / "script.json").read_text(encoding="utf-8"))
    plan = storyboard._plan_beats(script, "ja")
    beats = [dict(section=p["section"], beat=p["beat"], shot="object" if i % 2 else "wide", cast_ids=["anna"] if i % 2 == 0 else [],
                  visual_prompt=prompt) for i, p in enumerate(plan)]
    bible = dict(look="35mm photo, soft light", cast=[dict(id="anna", description="woman, 30s, short black hair, green sweater")],
                 locations=[dict(id="flat", description="small flat")])
    return dict(style_bible=bible, beats=beats)


class FakeClient:
    def __init__(self, *replies, stop="end_turn"):
        self.replies, self.calls, self.stop = list(replies), [], stop
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        r = self.replies.pop(0)
        return NS(stop_reason=self.stop, model="claude-sonnet-5-5", usage=NS(input_tokens=1000, output_tokens=2000),
                  content=[NS(type="text", text=json.dumps(r))])


def test_make_storyboard_valid_and_cost(tmp_path):
    con, d = setup(tmp_path)
    fc = FakeClient(reply_for(d))
    sb = storyboard.make_storyboard(con, fc, 1, d, "ja")
    k = fc.calls[0]
    assert k["model"] == "claude-sonnet-5-5" and k["fallbacks"] == "default" and "temperature" not in k
    assert json.loads((d / "storyboard.json").read_text(encoding="utf-8")) == sb
    b = sb["beats"]
    assert (b[-1]["section"], b[-1]["beat"]) == (2, 1)
    assert all(x["chars"] == len(x["narration"]) and not x["replaced"] for x in b)
    assert "".join(x["narration"] for x in b if x["section"] == 1) == "今日は雨だった。" * 25
    assert abs(ledger.profit(con, 1)["cost_usd"] - (1000 * 2 + 2000 * 10) / 1e6) < 1e-9


def test_retry_then_success_and_double_mismatch(tmp_path):
    con, d = setup(tmp_path)
    bad = reply_for(d)
    bad["beats"].pop()
    fc = FakeClient(bad, reply_for(d))
    storyboard.make_storyboard(con, fc, 1, d, "ja")
    assert len(fc.calls) == 2
    fc2 = FakeClient(bad, bad)
    with pytest.raises(ValueError):
        storyboard.make_storyboard(con, fc2, 1, d, "ja")
    assert len(fc2.calls) == 2


def test_unsafe_prompt_replaced(tmp_path):
    con, d = setup(tmp_path)
    r = reply_for(d)
    r["beats"][0]["visual_prompt"] = "A nude woman by the window"
    sb = storyboard.make_storyboard(con, FakeClient(r), 1, d, "ja")
    assert sb["beats"][0]["replaced"] and not visuals.check_prompt(sb["beats"][0]["visual_prompt"])
    assert sb["beats"][0]["cast_ids"] == [] and not sb["beats"][1]["replaced"]


def test_refusal_raises(tmp_path):
    con, d = setup(tmp_path)
    with pytest.raises(RuntimeError, match="refused"):
        storyboard.make_storyboard(con, FakeClient(reply_for(d), stop="refusal"), 1, d, "ja")


def stored(tmp_path):
    con, d = setup(tmp_path)
    storyboard.make_storyboard(con, FakeClient(reply_for(d, "a cup of tea")), 1, d, "ja")
    return d


def test_render_beats_files_skip_and_order(tmp_path):
    d = stored(tmp_path)
    calls = []

    class P(visuals.MockImage):
        def generate(self, prompt, out_path, size=(1920, 1080)):
            calls.append(prompt)
            super().generate(prompt, out_path, size)

    paths = storyboard.render_beats(d, P())
    n = len(json.loads((d / "storyboard.json").read_text(encoding="utf-8"))["beats"])
    assert len(paths) == n == len(calls) and paths == sorted(paths)
    assert paths[0].name == "section_01_01.png" and paths[-1].name == "section_02_01.png" and all(p.exists() for p in paths)
    assert any("35mm photo" in c and "green sweater" in c for c in calls)
    paths[0].unlink()
    calls.clear()
    assert storyboard.render_beats(d, P()) == paths and len(calls) == 1


def test_render_beats_unsafe_blocks_everything(tmp_path):
    d = stored(tmp_path)
    sb = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
    sb["beats"][-1]["visual_prompt"] = "a naked person"
    (d / "storyboard.json").write_text(json.dumps(sb), encoding="utf-8")

    class P:
        def generate(self, *a, **k):
            raise AssertionError("must not generate")

    with pytest.raises(ValueError, match="section 2 beat 1"):
        storyboard.render_beats(d, P())


def test_usage_collected(tmp_path):
    d = stored(tmp_path)

    class P(visuals.MockImage):
        last_usage = None

        def generate(self, prompt, out_path, size=(1920, 1080)):
            super().generate(prompt, out_path, size)
            self.last_usage = {"tokens": 1}

    storyboard.render_beats(d, P(), max_workers=1)
    assert json.loads((d / "visuals" / "usage.json").read_text())[0]["usage"] == {"tokens": 1}


def test_extra_and_duplicate_beats_from_the_model_are_ignored(tmp_path):
    con, d = setup(tmp_path)
    good = reply_for(d)
    extra = json.loads(json.dumps(good))
    extra["beats"] = extra["beats"] + [dict(extra["beats"][0], beat=99), dict(extra["beats"][1])]   # an extra beat and a duplicate
    fc = FakeClient(extra)
    sb = storyboard.make_storyboard(con, fc, 1, d, "ja")
    assert len(fc.calls) == 1 and len(sb["beats"]) == len(good["beats"])
    assert [(b["section"], b["beat"]) for b in sb["beats"]] == [(b["section"], b["beat"]) for b in good["beats"]]
