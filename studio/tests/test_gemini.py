import base64
import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import gemini, qa, visuals  # noqa: E402
from studio.errors import NotConnected  # noqa: E402


def png_b64(size=(640, 360)):
    b = io.BytesIO(); Image.new("RGB", size, (30, 90, 160)).save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


class Resp:
    def __init__(self, code, body):
        self.status_code, self._b = code, body

    def json(self):
        return self._b


class Session:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append((url, json, headers))
        return self.replies.pop(0)


IMG = {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": png_b64()}}]}}],
       "usageMetadata": {"promptTokenCount": 30, "candidatesTokenCount": 1290}}


def test_no_key_raises_not_connected(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(NotConnected):
        visuals.GeminiImage(session=Session([])).generate("x", tmp_path / "a.png")
    assert visuals.GeminiImage().describe()["status"] == "not_connected"


def test_image_is_decoded_resized_and_usage_recorded(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    s = Session([Resp(200, IMG)])
    g = visuals.GeminiImage(session=s)
    g.generate("a calm cafe", tmp_path / "a.png")
    assert Image.open(tmp_path / "a.png").size == (1920, 1080)
    assert g.last_usage == {"input_tokens": 30, "output_tokens": 1290, "thought_tokens": 0}
    url, body, headers = s.calls[0]
    assert url.endswith("/gemini-3.1-flash-lite-image:generateContent") and headers["x-goog-api-key"] == "k"
    assert "key=" not in url                       # key only in the header, never in the URL


def test_image_retries_once_with_other_modalities_on_400(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    s = Session([Resp(400, {"error": {"message": "bad config"}}), Resp(200, IMG)])
    visuals.GeminiImage(session=s).generate("x", tmp_path / "a.png")
    assert s.calls[1][1]["generationConfig"]["responseModalities"] == ["TEXT", "IMAGE"]


def test_api_error_message_has_no_key(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET-KEY-123")
    s = Session([Resp(403, {"error": {"message": "permission denied"}})])
    with pytest.raises(gemini.GeminiError) as e:
        visuals.GeminiImage(session=s).generate("x", tmp_path / "a.png")
    assert "SECRET-KEY-123" not in str(e.value)


def test_gemini_reviewer_parses_json_with_search_tool(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    txt = 'ok\n{"verdict":"revise","issues":["Mt. Fuji is 3,776 m"],"unverified_claims":[]}'
    s = Session([Resp(200, {"candidates": [{"content": {"parts": [{"text": txt}]}}],
                            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "thoughtsTokenCount": 7}})])
    r = qa.GeminiReviewer(session=s).review({"sections": []}, "ja")
    assert s.calls[0][1]["tools"] == [{"google_search": {}}]
    assert r["reviewer"] == "gemini" and r["verdict"] == "revise" and r["usage"] == {"input_tokens": 10, "output_tokens": 12}
    # never a pass on garbage
    s2 = Session([Resp(200, {"candidates": [{"content": {"parts": [{"text": "fine"}]}}]})])
    assert qa.GeminiReviewer(session=s2).review({"sections": []}, "ja")["verdict"] == "revise"
