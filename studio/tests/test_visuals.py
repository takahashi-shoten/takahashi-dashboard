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
