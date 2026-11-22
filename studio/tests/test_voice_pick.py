import json
import subprocess

from studio import voice, voice_pick

FAKE = [
    {"name": "青山龍星", "styles": [{"name": "熱血", "id": 51}, {"name": "ノーマル", "id": 13}, {"name": "しっとり", "id": 86}]},
    {"name": "玄野武宏", "styles": [{"name": "喜び", "id": 39}, {"name": "ツンギレ", "id": 40}]},
    {"name": "ずんだもん", "styles": [{"name": "ノーマル", "id": 3}]},
]


def test_pick_normal_first_and_max_styles():
    c = voice_pick.pick_candidates(FAKE, names=["青山龍星", "玄野武宏"], max_styles=2)
    assert c == [{"speaker": "青山龍星", "style": "ノーマル", "id": 13},
                 {"speaker": "青山龍星", "style": "熱血", "id": 51},
                 {"speaker": "玄野武宏", "style": "喜び", "id": 39},
                 {"speaker": "玄野武宏", "style": "ツンギレ", "id": 40}]


def test_pick_tolerates_missing_and_limits():
    c = voice_pick.pick_candidates(FAKE, names=["いない人", "青山龍星"], max_styles=1)
    assert c == [{"speaker": "青山龍星", "style": "ノーマル", "id": 13}]


def test_default_names_do_not_include_female():
    assert "ずんだもん" not in voice_pick.CANDIDATE_NAMES


def test_slug_and_filename():
    assert voice_pick.sample_filename(3, "No.7", "アナウンス") == "03_No.7_アナウンス.mp3"
    assert "/" not in voice_pick.slug("a/b c")
    assert voice_pick.slug("///") == "x"


def test_build_samples_with_fake_voice(tmp_path, monkeypatch):
    class Fake:
        def __init__(self, speaker=None, **kw):
            self.speaker = speaker

        def synthesize(self, text, lang, out_path):
            if self.speaker == 99:
                raise RuntimeError("boom")
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                            "-t", "1", "-c:a", "pcm_s16le", str(out_path)], check=True)
            return 1.0

    monkeypatch.setattr(voice, "VoicevoxVoice", Fake)
    cands = [{"speaker": "青山龍星", "style": "ノーマル", "id": 13},
             {"speaker": "壊れ", "style": "ノーマル", "id": 99}]
    entries, failures = voice_pick.build_samples(cands, "テスト", tmp_path)
    assert len(entries) == 1 and len(failures) == 1
    e = entries[0]
    assert e["file"] == "01_青山龍星_ノーマル.mp3" and (tmp_path / e["file"]).exists()
    assert 0.5 < e["seconds"] < 2 and e["credit"] == "VOICEVOX:青山龍星"
    data = json.loads((tmp_path / "candidates.json").read_text(encoding="utf-8"))
    assert data["samples"][0]["id"] == 13 and data["failures"][0]["speaker"] == "壊れ"
    assert not list(tmp_path.glob("_tmp_*"))
