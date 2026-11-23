import pytest


@pytest.fixture(autouse=True)
def _isolated_tts_cache(tmp_path, monkeypatch):
    """Keep the Gemini TTS request cache out of the real work dir so tests never see (or leave) cached audio."""
    monkeypatch.setenv("STUDIO_TTS_CACHE", str(tmp_path / "tts_cache"))
