import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import visuals  # noqa: E402
from studio.errors import NotConnected  # noqa: E402


def project(tmp_path, prompts):
    secs = [dict(heading="h", narration="n", visual_prompt=p, seconds=5) for p in prompts]
    (tmp_path / "script.json").write_text(json.dumps(dict(sections=secs)), encoding="utf-8")
    return tmp_path


def test_mock_image_deterministic_and_sized(tmp_path):
    m = visuals.MockImage()
    m.generate("朝のカフェの水彩イラスト", tmp_path / "a.png")
    m.generate("朝のカフェの水彩イラスト", tmp_path / "b.png")
    m.generate("other", tmp_path / "c.png")
    assert Image.open(tmp_path / "a.png").size == (1920, 1080)
    assert (tmp_path / "a.png").read_bytes() == (tmp_path / "b.png").read_bytes() != (tmp_path / "c.png").read_bytes()
    assert m.describe()["status"] == "mock"


def test_render_visuals(tmp_path):
    p = project(tmp_path, ["a calm lake illustration", "paper city at dusk"])
    paths = visuals.render_visuals(p, visuals.MockImage())
    assert [x.name for x in paths] == ["section_01.png", "section_02.png"] and all(x.exists() for x in paths)


@pytest.mark.parametrize("prompt", [
    "photo of Taylor Swift on stage", "a man who looks like Tom Cruise", "ヌードの人物", "nsfw scene",
    "schoolgirl in lingerie", "Pikachu running", "ミッキーマウスの絵", "有名人の顔のアップ",
])
def test_check_prompt_rejects(prompt):
    assert visuals.check_prompt(prompt)


@pytest.mark.parametrize("prompt", [
    "watercolor illustration of a quiet cafe at dawn", "a photo of a mountain lake", "children's picture book style forest",
    "朝の静かな街並みのイラスト", "an elderly hiker walking a trail, flat vector art",
])
def test_check_prompt_accepts(prompt):
    assert visuals.check_prompt(prompt) == []


def test_render_visuals_rejects_and_lists_sections(tmp_path):
    p = project(tmp_path, ["fine landscape", "Mario in a castle"])
    with pytest.raises(ValueError, match="section 02"):
        visuals.render_visuals(p, visuals.MockImage())
    assert not (p / "visuals").exists()


def test_real_adapters_not_connected(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(NotConnected, match="GEMINI_API_KEY"):
        visuals.GeminiImage().generate("x", tmp_path / "x.png")
    with pytest.raises(NotConnected, match="OPENAI_API_KEY"):
        visuals.OpenAIImage().generate("x", tmp_path / "x.png")
    assert visuals.GeminiImage().describe()["status"] == "not_connected"


def test_hybrid_image_routes_opening_and_tail_to_premium(tmp_path):
    from pathlib import Path

    class Fake:
        def __init__(self, model):
            self.model, self.usage, self.last_usage, self.calls = model, [], None, []

        def generate(self, prompt, out_path, size=(1920, 1080)):
            self.calls.append(Path(out_path).name)
            self.last_usage = {"output_tokens": 1000}
            self.usage.append(self.last_usage)

        def describe(self):
            return dict(stage="visuals", status="done", note="fake")

    prem, std = Fake("P"), Fake("S")
    h = visuals.HybridImage(premium=prem, standard=std, opening_chars=100, tail_beats=2, max_share=0.5)
    items = [(tmp_path / f"b{i:02d}.png", {"section": 1, "beat": i, "chars": 40}) for i in range(10)]
    chosen = h.plan_premium(items)
    # opening: beats until >=100 chars (3 beats: 40+40+40), tail: last 2; cap = 50% of 10 = 5
    assert {p.name for p in chosen} == {"b00.png", "b01.png", "b02.png", "b08.png", "b09.png"}
    for p, _ in items:
        h.generate("x", p)
    assert sorted(prem.calls) == ["b00.png", "b01.png", "b02.png", "b08.png", "b09.png"] and len(std.calls) == 5
    assert len(h.usage) == 10 and [m for m, _ in h.parts] == ["P", "S"]


def test_image_cost_sums_each_model_price():
    from studio import produce

    class P:
        parts = [("gemini-3.1-flash-image", [{"output_tokens": 1000}]), ("gemini-3.1-flash-lite-image", [{"output_tokens": 2000}])]

    tok, usd = produce.image_cost(P())
    assert tok == 3000 and abs(usd - (1000 * 60 + 2000 * 30) / 1e6) < 1e-12
