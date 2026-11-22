# studio: stage contract (shared by all modules)

Python 3.12, package `studio` in `studio/studio/`. Tests in `studio/tests/test_<module>.py` (pytest, run from `studio/`).
No network in tests. No API keys in code: read from env, raise `NotConnected` (defined in `studio/errors.py`) with the env var name when missing.
Never print or log secrets. Never publish anything anywhere (publishing is out of scope).

## Project directory
`studio/work/<project_id>/` (gitignored):
```
script.json            output of studio.script.write_script (schema below)
voice/section_NN.wav   NN = 01.. (mono, 24000 Hz or higher, PCM)
voice/durations.json   {"01": 12.34, ...} seconds, measured with ffprobe
visuals/section_NN.png 1920x1080
final.mp4              1920x1080, 30fps, H.264 + AAC, loudness-normalized
final.srt              subtitles
shorts.mp4             1080x1920, <= 59 s
thumbnail.png          1280x720
qa.json                see qa module
```

## script.json
```
{"title_options": [str], "original_angle": str, "hook": str,
 "sections": [{"heading": str, "narration": str, "visual_prompt": str, "seconds": int}],
 "description": str, "tags": [str], "fact_claims_to_verify": [str], "ai_disclosure_needed": bool}
```
Plus the project's `lang` ("ja" or "en") is passed separately.

## Provider pattern
Each stage has a `Protocol` for its provider, one `Mock*` provider that works offline and deterministically (used in tests and CI),
and real adapters that raise `NotConnected` until configured. A real adapter is never reported as working unless it was run.

## Honesty rule
Every module exposes `describe()` -> dict(stage, status in {"done","mock","not_connected"}, note). Mock output must be visibly marked as mock
(e.g. "MOCK" watermark on images, a beep-free silent track for audio) so it can never be mistaken for a real asset.

## Costs
Any paid provider call returns/records usage so the caller can pass it to `studio.ledger.record_cost`. Add a price entry in `ledger.PRICES`-style
dict inside the module with a comment on the source and date; unknown prices must be None, never guessed.
