"""Minimal Gemini REST client (raw HTTP, `requests`). generateContent only. Never logs or echoes the key."""
import base64
import os

import requests

from .errors import NotConnected

BASE = "https://generativelanguage.googleapis.com/v1beta/models/"


class GeminiError(RuntimeError):
    pass


def api_key() -> str:
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if not k:
        raise NotConnected("set GEMINI_API_KEY (Google AI Studio key)")
    return k


def generate_content(model, body, session=None, timeout=180):
    r = (session or requests).post(f"{BASE}{model}:generateContent", json=body, timeout=timeout,
                                   headers={"x-goog-api-key": api_key(), "Content-Type": "application/json"})
    if r.status_code != 200:
        try:
            msg = r.json().get("error", {}).get("message", "")
        except ValueError:
            msg = ""
        raise GeminiError(f"HTTP {r.status_code}: {msg[:300]}")
    return r.json()


def usage(resp) -> dict:
    m = resp.get("usageMetadata", {}) or {}
    return {"input_tokens": int(m.get("promptTokenCount", 0)), "output_tokens": int(m.get("candidatesTokenCount", 0)),
            "thought_tokens": int(m.get("thoughtsTokenCount", 0))}


def _parts(resp):
    cands = resp.get("candidates") or []
    return ((cands[0].get("content") or {}).get("parts") or []) if cands else []


def text_of(resp) -> str:
    return "".join(p.get("text", "") for p in _parts(resp) if "text" in p and not p.get("thought"))


def first_image(resp):
    """(mime_type, bytes) of the first inline image, or None."""
    for p in _parts(resp):
        d = p.get("inlineData") or p.get("inline_data")
        if d and d.get("data"):
            return d.get("mimeType") or d.get("mime_type") or "image/png", base64.b64decode(d["data"])
    return None
