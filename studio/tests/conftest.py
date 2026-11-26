import pytest


@pytest.fixture(autouse=True)
def _isolated_tts_cache(tmp_path, monkeypatch):
    """Keep the Gemini TTS request cache out of the real work dir so tests never see (or leave) cached audio."""
    monkeypatch.setenv("STUDIO_TTS_CACHE", str(tmp_path / "tts_cache"))


@pytest.fixture(autouse=True)
def _no_real_knowledge_db(monkeypatch):
    """Tests must never consult or write the real knowledge DB in the repo (uses are logged); individual tests pass an explicit path / env."""
    monkeypatch.setenv("STUDIO_KNOWLEDGE_DB", "off")
