from studio import vu_eval as ev


def test_cer_ignores_punctuation_and_counts_errors():
    assert ev.cer("本能寺の変、信長は。", "本能寺の変信長は") == 0
    assert abs(ev.cer("abcd", "abxd") - 0.25) < 1e-9
    assert ev.cer("abc", "") == 1


def test_match_events_precision_recall_within_tolerance():
    r = ev.match_events([10, 20, 30, 40], [10.5, 19, 31.5, 55], tol=2.0)
    assert (r["tp"], r["fp"], r["fn"]) == (3, 1, 1) and r["precision"] == 0.75 and r["recall"] == 0.75
    assert ev.match_events([], [])["f1"] == 0


def test_defect_detection_counts_false_alarms():
    inj = [dict(type="audio_dropout", start=100, end=120), dict(type="video_blackout", start=300, end=308)]
    r = ev.defect_detection(inj, [105, 500, 600], tol=10)
    assert r["detection_rate"] == 0.5 and r["false_alarms"] == 2 and r["detected"][1]["detected"] is False


def test_mmss_and_srt_window():
    assert ev.mmss("01:15") == 75 and ev.mmss("1:02:03") == 3723 and ev.mmss(7) == 7
    srt = "1\n00:00:01,000 --> 00:00:03,000\nこんにちは\n\n2\n00:00:10,000 --> 00:00:12,000\n世界\n"
    assert ev.srt_window_text(srt, 0, 5) == "こんにちは" and ev.srt_window_text(srt, 9, 20) == "世界"
