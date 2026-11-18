import sys, pathlib, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
from app.services.content_analysis import signals as sig

def test_planner_always_valid():
    for dur in (16, 25, 26, 31, 44, 70, 119, 600, 1234.5):
        for cuts in ([], [10, 20, 30, 40, 50, 60], list(np.arange(3, dur, 7.3))):
            parts = sig.plan_equal_parts(dur, cuts)
            assert parts[0][0] == 0 and abs(parts[-1][1] - dur) < 0.02
            assert all(abs(a[1] - b[0]) < 0.02 for a, b in zip(parts, parts[1:]))          # contiguous, no gaps/overlaps
            if dur >= 30: assert all(15 - 0.02 <= b - a <= 25 + 0.02 for a, b in parts), (dur, parts)

def test_real_video():
    assert not sig.has_audio("/tmp/t/silent.mp4") and sig.has_audio("/tmp/t/long.mp4")
    ts, sc = sig.scene_series("/tmp/t/silent.mp4")
    cuts = ts[sc > 0.35]
    print("cuts found at:", [round(float(c), 1) for c in cuts])
    for expected in (10, 20, 30, 40, 50, 60): assert any(abs(c - expected) < 0.6 for c in cuts), expected
    parts = sig.plan_equal_parts(70, cuts); print("parts:", parts)
    assert all(15 <= b - a <= 25.01 for a, b in parts)
    rows = sig.score_parts(parts, ts, sc, cuts)
    assert all(0 < r["score"] < 100 and r["viral_pct"] < r["score"] for r in rows); print([(r["start"], r["score"]) for r in rows])

if __name__ == "__main__":
    test_planner_always_valid(); test_real_video(); print("SILENT TESTS PASSED")
