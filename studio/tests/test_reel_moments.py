from studio import reel_moments as r


def test_mmss():
    assert r.mmss("02:30") == 150 and r.mmss("1:02:03") == 3723 and r.mmss("bad") is None


def test_clean_moments_drops_bad_and_overlap():
    d = {"moments": [{"start": "00:10", "end": "00:25"}, {"start": "00:20", "end": "00:40"}, {"start": "01:00", "end": "01:02"}, {"start": "x", "end": "02:00"}, {"start": "05:00", "end": "05:20"}]}
    kept, dropped = r.clean_moments(d)
    assert [m["start"] for m in kept] == ["00:10", "05:00"] and dropped == 3
